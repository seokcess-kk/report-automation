"""6월 전지점 퍼널별 목표달성을 위한 타겟팅·콘텐츠 추천

출력 구조 (지점별):
- 우선 퍼널: 전 지점 평균 대비 가장 약한 퍼널 (원인 분석 모듈 활용)
- 유지: 본인 지점에서 이미 우수한 소재 (해당 퍼널 기준)
- 확대: 본인 지점에서도 운영중이지만 타 지점이 더 잘 활용 - 더 푸시
- 신규 도입: 본인 지점 미운영이지만 다른 지점에서 검증된 베스트 소재
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES

# 같은 디렉토리에서 import
sys.path.insert(0, str(Path(__file__).parent))
from analyze_top_creatives import _aggregate_creatives, MIN_CLICKS, MIN_COST
from analyze_root_cause import analyze as analyze_root


FUNNEL_DIRECTION = {'cpm': 'low', 'ctr': 'high', 'cvr': 'high'}


def _pick_focus_from_weaknesses(weaknesses: list) -> str | None:
    """원인 분석의 peer_weaknesses 에서 가장 큰 약점 퍼널 선택.
    CPM/CTR/CVR 중 약점이 있으면 그 중 severity 최대 선택. 없으면 None.
    """
    funnel_set = {'cpm', 'ctr', 'cvr'}
    candidates = [w for w in weaknesses if w['metric'] in funnel_set]
    if not candidates:
        return None
    # 강도 순 1위
    return candidates[0]['metric']


def _row_summary(row: pd.Series, focus: str) -> dict:
    return {
        'creative_name': row['매칭키'],
        'cost': int(row['cost']),
        'conversions': int(row['conversions']),
        'cpm': None if pd.isna(row['cpm']) else int(row['cpm']),
        'ctr': None if pd.isna(row['ctr']) else float(row['ctr']),
        'cvr': None if pd.isna(row['cvr']) else float(row['cvr']),
        'cpa': None if pd.isna(row['cpa']) else int(row['cpa']),
        'days_active': int(row['days_active']),
        'is_off': bool(row['is_off_all']),
        'focus_metric': focus,
        'focus_value': None if pd.isna(row[focus]) else float(row[focus]),
    }


def _pick_top(sub: pd.DataFrame, focus: str, n: int = 3) -> list[dict]:
    """focus 퍼널 기준 정렬."""
    if focus == 'cpm':
        ranked = sub.dropna(subset=['cpm']).nsmallest(n, 'cpm')
    else:
        ranked = sub.dropna(subset=[focus]).nlargest(n, focus)
    return [_row_summary(r, focus) for _, r in ranked.iterrows()]


def analyze(parsed_path: str) -> dict:
    root = analyze_root(parsed_path)

    df = pd.read_parquet(parsed_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['parse_status'] == 'OK'].copy()
    df = df[df['지점'].isin(VALID_BRANCHES)].dropna(subset=['매칭키'])

    grouped = _aggregate_creatives(df)
    eligible = grouped[(grouped['clicks'] >= MIN_CLICKS) & (grouped['cost'] >= MIN_COST)].copy()

    # 매칭키별 운영 지점 집합
    by_key_branches = eligible.groupby('매칭키')['지점'].apply(set).to_dict()

    result = {}
    for branch in VALID_BRANCHES:
        # 원인 분석의 peer_weaknesses 에서 가장 큰 약점 퍼널을 우선순위로
        bd_root = root['by_branch'][branch]
        weaknesses = bd_root.get('peer_weaknesses', []) if bd_root.get('is_diagnosable') else []
        focus_funnel = _pick_focus_from_weaknesses(weaknesses) or 'cvr'  # 약점 없으면 CVR 기본
        # focus_funnel 과 일치하는 약점 라벨 찾기
        focus_weakness = next((w for w in weaknesses if w['metric'] == focus_funnel), None)
        weakness_label = focus_weakness['label'] if focus_weakness else '특이 약점 없음 - 기본 CVR 강화'

        own = eligible[eligible['지점'] == branch].copy()
        other = eligible[eligible['지점'] != branch].copy()

        # 유지: 본인 지점 focus 퍼널 TOP3
        keep = _pick_top(own, focus_funnel, n=3)

        # 신규 도입: 다른 지점에서 focus 퍼널 우수 / 본인 지점 미운영
        own_keys = set(own['매칭키'])
        other_new = other[~other['매칭키'].isin(own_keys)].copy()
        # 매칭키별로 다른 지점들의 합산이 아니라 best 지점 1건만 선택
        if focus_funnel == 'cpm':
            other_new_best = other_new.sort_values('cpm').drop_duplicates(subset=['매칭키'], keep='first')
        else:
            other_new_best = other_new.sort_values(focus_funnel, ascending=False).drop_duplicates(subset=['매칭키'], keep='first')
        new_intro = _pick_top(other_new_best, focus_funnel, n=3)
        # 어느 지점 출신인지 부가 표시
        new_intro_keys = [c['creative_name'] for c in new_intro]
        key_to_src = dict(zip(other_new_best['매칭키'], other_new_best['지점']))
        for c in new_intro:
            c['source_branch'] = key_to_src.get(c['creative_name'])

        # 확대: 본인 지점에서 운영중이지만 본인 지점에서 focus 퍼널 성과가 평균 이하
        # & 다른 지점에서 같은 매칭키가 우수
        own_keys_list = list(own_keys)
        cross_strong_keys = set()
        for k in own_keys_list:
            others_for_k = other[other['매칭키'] == k]
            if len(others_for_k) == 0:
                continue
            # 다른 지점 평균이 본인 지점값보다 더 좋으면 cross_strong
            own_val = own[own['매칭키'] == k][focus_funnel].iloc[0]
            others_val = others_for_k[focus_funnel].mean()
            if pd.isna(own_val) or pd.isna(others_val):
                continue
            if focus_funnel == 'cpm':
                if others_val < own_val * 0.9:
                    cross_strong_keys.add(k)
            else:
                if others_val > own_val * 1.1:
                    cross_strong_keys.add(k)
        expand_pool = own[own['매칭키'].isin(cross_strong_keys)]
        expand = _pick_top(expand_pool, focus_funnel, n=3)
        # 출처 지점들 부가 표시
        for c in expand:
            sources = other[other['매칭키'] == c['creative_name']].sort_values(
                focus_funnel, ascending=(focus_funnel == 'cpm')
            )['지점'].tolist()
            c['better_in_branches'] = sources[:3]

        result[branch] = {
            'focus_funnel': focus_funnel,
            'focus_reason': weakness_label,
            'keep': keep,
            'expand': expand,
            'new_intro': new_intro,
        }

    return {
        'branches': VALID_BRANCHES,
        'by_branch': result,
    }


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260506/parsed.parquet'
    r = analyze(path)
    for b in r['branches']:
        bd = r['by_branch'][b]
        print(f"\n[{b}] 우선순위 퍼널: {bd['focus_funnel'].upper()} (갭: {bd['gap']})")
        print(f"  ▶ 유지 ({len(bd['keep'])}건):")
        for c in bd['keep']:
            print(f"     - {c['creative_name'][:50]} ({bd['focus_funnel']}={c['focus_value']}, 전환={c['conversions']})")
        print(f"  ▶ 확대 ({len(bd['expand'])}건):")
        for c in bd['expand']:
            print(f"     - {c['creative_name'][:50]} (현재 {bd['focus_funnel']}={c['focus_value']}, 타지점 더 우수)")
        print(f"  ▶ 신규 도입 ({len(bd['new_intro'])}건):")
        for c in bd['new_intro']:
            print(f"     - {c['creative_name'][:50]} (출처: {c.get('source_branch')}, {bd['focus_funnel']}={c['focus_value']})")
