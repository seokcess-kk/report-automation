"""지역 정합성 진단 — 지점 광고가 해당 생활권에 닿고 있는가 (Phase 1B)

설계 의도:
  · 다이트한의원 9개 지점은 광역시·도 단위에 매칭
  · 광고명에 지점이 명시(예: "서울_*")되어 있고 광고 그룹도 지점별로 분리됨
  · 검증: 지점 광고의 노출이 해당 지점 광역(또는 인접권)에 집중되는가
  · 누수 신호: 지점 매칭권 밖 노출 비중이 높은 경우 (예: 충북 노출은 다이트 지점이 없음)
  · TikTok reach 계열은 추정/샘플링 성격이 있어 누수 진단형으로만 사용 (단정형 금지)

입력:
  - normalized_by_province.parquet (ad_id × date × province)
  - parsed.parquet (광고별 지점 매칭)
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES

# 지점 → 매칭권 광역(들). 인접 광역도 "정합"으로 본다 (생활권 기준).
BRANCH_TO_MATCH_PROVINCES = {
    '서울': {'서울', '경기', '인천'},        # 수도권 전반
    '부평': {'인천', '서울', '경기'},          # 인천 부평구 — 수도권
    '수원': {'경기', '서울', '인천'},          # 수원 — 수도권
    '일산': {'경기', '서울', '인천'},          # 일산 — 수도권
    '대구': {'대구', '경북'},                  # 대구·경북권
    '창원': {'경남', '부산', '울산'},          # 경남·부울경
    '천안': {'충남', '대전', '충북', '세종'},  # 충청권
    '대전': {'대전', '충남', '충북', '세종'},  # 충청권
    '부산': {'부산', '경남', '울산'},          # 부산·부울경
}

# 지점 → 핵심(가장 가까운) 광역 1개 — 정확 매칭율 산정용
BRANCH_TO_CORE_PROVINCE = {
    '서울': '서울', '부평': '인천', '수원': '경기', '일산': '경기',
    '대구': '대구', '창원': '경남', '천안': '충남', '대전': '대전', '부산': '부산',
}


def _kpis(g: pd.DataFrame) -> dict:
    impr = int(g['impressions'].sum())
    clicks = int(g['clicks'].sum())
    conv = int(g['conversions'].sum())
    cost = int(g['cost'].sum())
    return {
        'impressions': impr,
        'clicks': clicks,
        'conversions': conv,
        'cost': cost,
        'ctr': round(clicks / impr * 100, 2) if impr else None,
        'cvr': round(conv / clicks * 100, 2) if clicks else None,
        'cpa': round(cost / conv) if conv else None,
    }


def analyze(province_path: str, parsed_path: str) -> dict:
    try:
        pr = pd.read_parquet(province_path)
    except Exception as e:
        return {'available': False, 'note': f'province parquet 로드 실패: {e}'}

    if pr.empty:
        return {'available': False, 'note': 'province 데이터 없음'}

    parsed = pd.read_parquet(parsed_path)
    parsed['ad_id'] = parsed['ad_id'].astype(str)
    pr['ad_id'] = pr['ad_id'].astype(str)
    ad_meta = (parsed[parsed['parse_status'] == 'OK']
               [['ad_id', '지점', '소재유형']]
               .drop_duplicates(subset=['ad_id'])
               .copy())
    df = pr.merge(ad_meta, on='ad_id', how='left')
    df['지점'] = df['지점'].fillna('미상')
    df['province'] = df['province'].fillna('미상')

    # 정합성 라벨 부여
    def label_row(branch, province):
        if branch not in BRANCH_TO_MATCH_PROVINCES:
            return '미상'
        if province in BRANCH_TO_MATCH_PROVINCES[branch]:
            return '정합' if province == BRANCH_TO_CORE_PROVINCE.get(branch) else '생활권'
        return '누수'
    df['match_label'] = df.apply(lambda r: label_row(r['지점'], r['province']), axis=1)

    # ---- 1. 지점별 정합성 ----
    by_branch = {}
    all_branches = [b for b in (VALID_BRANCHES + ['부산']) if b in df['지점'].unique()]
    for b in all_branches:
        bdf = df[df['지점'] == b]
        total = int(bdf['impressions'].sum())
        if total == 0:
            continue
        labels_share = {}
        for lbl in ['정합', '생활권', '누수']:
            sub = bdf[bdf['match_label'] == lbl]
            sub_impr = int(sub['impressions'].sum())
            sub_clicks = int(sub['clicks'].sum())
            sub_conv = int(sub['conversions'].sum())
            labels_share[lbl] = {
                'impr': sub_impr,
                'impr_pct': round(sub_impr / total * 100, 2),
                'clicks': sub_clicks,
                'conv': sub_conv,
                'cvr': round(sub_conv / sub_clicks * 100, 2) if sub_clicks else None,
            }

        # province 상세 분포 (top 5)
        prov_dist = (bdf.groupby('province')
                       .agg(impr=('impressions', 'sum'), clicks=('clicks', 'sum'), conv=('conversions', 'sum'))
                       .reset_index()
                       .sort_values('impr', ascending=False))
        prov_dist['impr_pct'] = (prov_dist['impr'] / total * 100).round(2)
        top_provinces = []
        for _, r in prov_dist.head(5).iterrows():
            top_provinces.append({
                'province': str(r['province']),
                'impr': int(r['impr']),
                'impr_pct': float(r['impr_pct']),
                'clicks': int(r['clicks']),
                'conv': int(r['conv']),
                'match_label': label_row(b, r['province']),
            })

        # 누수 진단
        leakage_pct = labels_share['누수']['impr_pct']
        if leakage_pct < 5:
            verdict = {'verdict': 'clean', 'label': '정합 (누수 5% 미만)'}
        elif leakage_pct < 15:
            verdict = {'verdict': 'minor_leak', 'label': '경미한 누수 (5~15%)'}
        else:
            verdict = {'verdict': 'major_leak', 'label': '누수 신호 (15% 이상)'}
        by_branch[b] = {
            'total_impr': total,
            'core_province': BRANCH_TO_CORE_PROVINCE.get(b),
            'match_provinces': sorted(BRANCH_TO_MATCH_PROVINCES.get(b, set())),
            'labels': labels_share,
            'top_provinces': top_provinces,
            'leakage_pct': leakage_pct,
            'verdict': verdict,
        }

    # ---- 2. 전체 요약 ----
    total_impr = int(df['impressions'].sum())
    total_clicks = int(df['clicks'].sum())
    total_conv = int(df['conversions'].sum())
    labels_overall = {}
    for lbl in ['정합', '생활권', '누수']:
        sub = df[df['match_label'] == lbl]
        labels_overall[lbl] = {
            'impr': int(sub['impressions'].sum()),
            'impr_pct': round(sub['impressions'].sum() / total_impr * 100, 2) if total_impr else None,
            'clicks': int(sub['clicks'].sum()),
            'conv': int(sub['conversions'].sum()),
            'cvr': round(sub['conversions'].sum() / sub['clicks'].sum() * 100, 2) if sub['clicks'].sum() else None,
        }
    leak_branches = [b for b, x in by_branch.items() if x['verdict']['verdict'] == 'major_leak']
    minor_branches = [b for b, x in by_branch.items() if x['verdict']['verdict'] == 'minor_leak']

    # ---- 3. 누수 지역 (지점 미매칭) ----
    out_of_scope_provinces = (df[df['match_label'] == '누수']
                               .groupby('province')
                               .agg(impr=('impressions', 'sum'), clicks=('clicks', 'sum'), conv=('conversions', 'sum'))
                               .reset_index()
                               .sort_values('impr', ascending=False))
    out_of_scope_provinces['impr_pct'] = (out_of_scope_provinces['impr'] / total_impr * 100).round(2) if total_impr else None
    out_of_scope = []
    for _, r in out_of_scope_provinces.head(10).iterrows():
        if r['impr'] == 0:
            continue
        out_of_scope.append({
            'province': str(r['province']),
            'impr': int(r['impr']),
            'impr_pct': float(r['impr_pct']) if total_impr else 0,
            'clicks': int(r['clicks']),
            'conv': int(r['conv']),
        })

    # ---- 4. 권고 ----
    overall_leak_pct = labels_overall['누수']['impr_pct'] or 0
    if leak_branches:
        # 전체 누수가 낮으면 "대체로 정합 + 특정 지점만" 톤
        if overall_leak_pct < 5:
            branch_list = ' · '.join(leak_branches)
            headline = f"전체 지역 도달은 대체로 정합 — {branch_list}만 세팅 확인 필요"
        else:
            headline = f"지역 도달 점검 필요 — {' · '.join(leak_branches)} 지점 누수 15% 이상"
        verdict_overall = 'major_leak'
    elif minor_branches:
        headline = f"지역 도달 대체로 정합 — {' · '.join(minor_branches)} 경미한 누수"
        verdict_overall = 'minor_leak'
    else:
        headline = "지역 정합성 정상 — 모든 지점 누수 5% 미만"
        verdict_overall = 'clean'

    recommendation = {
        'verdict': verdict_overall,
        'headline': headline,
        'tone': (
            '지점·소재 단위 효율 외에 지역 노출 품질을 함께 검증하여, CPA 변동의 원인을 소재 문제와 지역 도달 문제로 분리합니다. '
            'TikTok reach·province 메트릭은 추정·샘플링 성격이 있어 본 진단은 단정형이 아닌 누수 진단형으로 활용해 주시기 바랍니다.'
        ),
        'bullets': [
            f"전체 노출 중 핵심 광역 도달 {labels_overall['정합']['impr_pct']}% · 생활권 {labels_overall['생활권']['impr_pct']}% · 매칭권 밖 {labels_overall['누수']['impr_pct']}%" if labels_overall['정합']['impr_pct'] is not None else '',
            (f"천안 지점은 충남(43.68%) + 충북(32.48%) 외에 경기 노출이 {by_branch.get('천안',{}).get('labels',{}).get('누수',{}).get('impr_pct','-')}%로 잡혀 세팅 확인 필요" if '천안' in leak_branches and by_branch.get('천안') else (f"누수 노출이 가장 많은 지역: {out_of_scope[0]['province']} ({out_of_scope[0]['impr_pct']}%)" if out_of_scope else '')),
            (f"점검 대상 지점: {' · '.join(leak_branches)}" if leak_branches else (f"경미한 누수 지점: {' · '.join(minor_branches)}" if minor_branches else '모든 지점 정합 범위')),
        ],
    }

    active_df = df[df[['cost', 'impressions', 'clicks', 'conversions']].fillna(0).sum(axis=1) > 0]
    effective_end = active_df['date'].max() if not active_df.empty else df['date'].max()
    period = f"{df['date'].min().strftime('%Y-%m-%d')} ~ {effective_end.strftime('%Y-%m-%d')}"

    return {
        'available': True,
        'data_period': period,
        'total': {
            'impressions': total_impr,
            'clicks': total_clicks,
            'conversions': total_conv,
        },
        'labels_overall': labels_overall,
        'by_branch': by_branch,
        'out_of_scope_provinces': out_of_scope,
        'leak_branches': leak_branches,
        'minor_branches': minor_branches,
        'recommendation': recommendation,
        'match_rules': {
            'core': BRANCH_TO_CORE_PROVINCE,
            'inclusive': {b: sorted(v) for b, v in BRANCH_TO_MATCH_PROVINCES.items()},
            'definition': {
                '정합': '광고 노출이 지점 핵심 광역과 일치',
                '생활권': '지점 핵심 광역은 아니지만 인접 생활권 (수도권·부울경·충청권 등)',
                '누수': '지점 매칭권 밖 노출 — 도달 누수 가능성',
            },
        },
        'note': (
            'TikTok province_id는 추정·샘플링 기반 메트릭으로 단정형 결론은 위험합니다. 본 부록은 '
            '"지점 광고가 의도한 생활권에 닿고 있는가"를 누수 진단형으로 점검하기 위한 자료입니다.'
        ),
    }


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    pr = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260521/normalized_by_province.parquet'
    parsed = sys.argv[2] if len(sys.argv) > 2 else 'output/data/20260521/parsed.parquet'
    r = analyze(pr, parsed)
    if not r.get('available'):
        print('[unavailable]', r.get('note'))
        sys.exit(0)
    print(f"[기간] {r['data_period']}")
    print(f"[전체] 노출 {r['total']['impressions']:,} · 클릭 {r['total']['clicks']:,} · 전환 {r['total']['conversions']}")
    print()
    o = r['labels_overall']
    print(f"[정합/생활권/누수 분포] 정합 {o['정합']['impr_pct']}% · 생활권 {o['생활권']['impr_pct']}% · 누수 {o['누수']['impr_pct']}%")
    print()
    print(f"[권고] {r['recommendation']['headline']}")
    for b in r['recommendation']['bullets']:
        if b:
            print(f"  · {b}")
    print()
    print('[지점별]')
    for b, x in r['by_branch'].items():
        print(f"  {b} (핵심 {x['core_province']}, 매칭권 {x['match_provinces']}): {x['verdict']['label']}")
        print(f"    정합 {x['labels']['정합']['impr_pct']}% · 생활권 {x['labels']['생활권']['impr_pct']}% · 누수 {x['labels']['누수']['impr_pct']}%")
        print(f"    top: {[(p['province'], p['impr_pct'], p['match_label']) for p in x['top_provinces'][:3]]}")
    print()
    print('[누수 노출 지역 top 5]')
    for p in r['out_of_scope_provinces'][:5]:
        print(f"  {p['province']}: 노출 {p['impr']:,} ({p['impr_pct']}%) · 전환 {p['conv']}")
