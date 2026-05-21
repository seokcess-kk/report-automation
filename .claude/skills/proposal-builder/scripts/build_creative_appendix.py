"""부록 소재 표 생성 — 지점별 전체 TIER 분류 + 판단 근거 + 권장 액션

액션 카드는 핵심 TIER1/TIER4만 inline (codex R9 Q3 결정 — 별도 부록 표 + 카드 inline 최소).
부록은 전체 소재의 운영 의사결정 데이터를 표 한 장으로 통합.

출력 형식:
  {
    'branches': {
        '서울': [
            {name, tier, cpa, cvr, ctr, cost, conversions, days_active,
             evidence, recommended_action}, ...
        ]
    },
    'tier_rationale': {tier: 판단 근거 문구}
  }
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES


TIER_RATIONALE = {
    'TIER1': 'CPA ≤ 지점 목표 AND CVR ≥ 5.0% — 최우수, 광고 단위 유지·확대',
    'TIER2': 'CPA ≤ 지점 목표 AND CVR < 5.0% AND 랜딩도달률 ≥ 50% — CVR 개선 시 TIER1 후보',
    'TIER3': 'CPA > 지점 목표 AND CVR ≥ 5.0% — CPA 가드 후 유지',
    'TIER4': 'CPA > 지점 목표 AND CVR < 5.0% — 최우선 OFF 후보',
    'LOW_VOLUME': '클릭 < 100 AND 비용 < 100,000원 — 평가 보류',
    'UNCLASSIFIED': '집행일수 < 7일 — 평가 보류',
}

TIER_ACTION = {
    'TIER1': '광고 단위 ON 유지·확대',
    'TIER2': '랜딩 hero·CTA 점검 후 CVR 개선 시 확대',
    'TIER3': '광고 그룹 예산 가드 (증액 보류)',
    'TIER4': '광고 단위 OFF (우선)',
    'LOW_VOLUME': '추가 노출 누적 후 재평가',
    'UNCLASSIFIED': '집행일수 충족 후 재평가',
}


def _find_latest_creative_tier(parsed_path: str) -> Path | None:
    """현재 dir 우선, 비어 있으면 비어있지 않은 가장 최신 dir로 fallback.

    5월 부분월처럼 ON 광고가 적어 TIER 분류가 0행인 경우를 위한 안전장치.
    """
    candidates = []
    same_dir = Path(parsed_path).parent / 'creative_tier.parquet'
    if same_dir.exists():
        candidates.append(same_dir)
    data_root = Path(parsed_path).parent.parent
    if data_root.exists():
        other = sorted(
            [d for d in data_root.iterdir() if d.is_dir() and (d / 'creative_tier.parquet').exists()],
            key=lambda d: d.name,
            reverse=True,
        )
        for d in other:
            p = d / 'creative_tier.parquet'
            if p != same_dir:
                candidates.append(p)
    # 비어있지 않은 첫 후보 반환
    for c in candidates:
        try:
            df = pd.read_parquet(c)
            if not df.empty:
                return c
        except Exception:
            continue
    # 모두 비어 있으면 첫 후보(가장 최신) 반환 — caller가 empty 처리
    return candidates[0] if candidates else None


def _aggregate_branch_creative_kpi(parsed_for_kpi_path: Path) -> dict:
    """parsed.parquet → (지점, 소재구분, 소재유형, 소재명) 단위 KPI 집계.

    소재 단위 합산 효율이 아닌 지점별 효율을 별도 계산해 부록 C에 노출.
    TIER 부여는 creative_tier (소재 단위) 기준 그대로 유지하고, KPI 수치만 분리.
    """
    if not parsed_for_kpi_path.exists():
        return {}
    try:
        p = pd.read_parquet(parsed_for_kpi_path)
    except Exception:
        return {}
    if p.empty or 'is_off' not in p.columns:
        return {}

    p_on = p[(p['is_off'] == False) & (p.get('parse_status', 'OK') == 'OK')].copy()
    if p_on.empty:
        return {}
    p_on['_active_date'] = p_on['date'].where(
        p_on[['cost', 'impressions', 'clicks', 'conversions']].fillna(0).sum(axis=1) > 0
    )

    # 집계 컬럼 — 시청 깊이/인게이지먼트는 있을 때만
    agg_spec = {
        '총비용': ('cost', 'sum'),
        '총클릭': ('clicks', 'sum'),
        '총노출': ('impressions', 'sum'),
        '총전환': ('conversions', 'sum'),
        '총랜딩': ('landing_views', 'sum'),
        '집행일수': ('_active_date', 'nunique'),
    }
    optional_cols = {
        'video_watched_6s': '총6초시청',
        'video_p100': '총p100',
        'avg_video_play_sec': '평균재생초',
        'likes': '총좋아요',
        'shares': '총공유',
        'engaged_view_15s': '총15초시청',
    }
    for src, dst in optional_cols.items():
        if src in p_on.columns:
            agg_spec[dst] = (src, 'mean' if src == 'avg_video_play_sec' else 'sum')

    grouped = p_on.groupby(['지점', '소재구분', '소재유형', '소재명']).agg(**agg_spec).reset_index()
    # 비율 재계산
    grouped['CPA'] = grouped.apply(lambda r: round(r['총비용']/r['총전환']) if r['총전환'] else None, axis=1)
    grouped['CTR'] = grouped.apply(lambda r: round(r['총클릭']/r['총노출']*100, 2) if r['총노출'] else None, axis=1)
    grouped['CVR'] = grouped.apply(lambda r: round(r['총전환']/r['총클릭']*100, 2) if r['총클릭'] else None, axis=1)
    if '총6초시청' in grouped.columns:
        grouped['6s시청률'] = grouped.apply(lambda r: round(r['총6초시청']/r['총노출']*100, 2) if r['총노출'] else None, axis=1)
    if '총p100' in grouped.columns:
        grouped['p100완료율'] = grouped.apply(lambda r: round(r['총p100']/r['총노출']*100, 2) if r['총노출'] else None, axis=1)
    if '총좋아요' in grouped.columns:
        grouped['좋아요율'] = grouped.apply(lambda r: round(r['총좋아요']/r['총노출']*100, 3) if r['총노출'] else None, axis=1)
    if '총공유' in grouped.columns:
        grouped['공유율'] = grouped.apply(lambda r: round(r['총공유']/r['총노출']*100, 4) if r['총노출'] else None, axis=1)
    if '총15초시청' in grouped.columns:
        grouped['15s시청률'] = grouped.apply(lambda r: round(r['총15초시청']/r['총노출']*100, 2) if r['총노출'] else None, axis=1)
    if '평균재생초' in grouped.columns:
        grouped['평균재생초'] = grouped['평균재생초'].round(2)

    # (branch, 소재구분, 소재유형, 소재명) → KPI dict
    lookup = {}
    for _, r in grouped.iterrows():
        key = (r['지점'], r['소재구분'], r['소재유형'], r['소재명'])
        lookup[key] = r.to_dict()
    return lookup


def build(parsed_path: str) -> dict:
    """creative_tier.parquet (소재 단위 TIER) + parsed.parquet (지점×소재 KPI) 결합.

    TIER은 creative_tier 기준 (지점 무관 합산), KPI는 parsed에서 지점별로 재집계.
    fallback이 발생하면 fallback dir의 parsed.parquet으로 KPI 계산.
    """
    tier_path = _find_latest_creative_tier(parsed_path)
    if tier_path is None:
        return {'branches': {}, 'tier_rationale': TIER_RATIONALE, 'note': 'creative_tier.parquet 없음 - 부록 생략'}
    try:
        df = pd.read_parquet(tier_path)
    except Exception as e:
        return {'branches': {}, 'tier_rationale': TIER_RATIONALE, 'note': f'creative_tier 로드 실패: {e}'}
    if df.empty:
        return {'branches': {}, 'tier_rationale': TIER_RATIONALE, 'note': '데이터 없음'}

    # 지점×소재 단위 KPI 재집계 (tier_path와 같은 dir의 parsed.parquet 사용)
    parsed_for_kpi = tier_path.parent / 'parsed.parquet'
    branch_kpi_lookup = _aggregate_branch_creative_kpi(parsed_for_kpi)

    name_col = '매칭키' if '매칭키' in df.columns else ('creative_name' if 'creative_name' in df.columns else None)
    tier_col = 'TIER' if 'TIER' in df.columns else ('tier' if 'tier' in df.columns else None)
    cpa_col = 'CPA' if 'CPA' in df.columns else ('cpa' if 'cpa' in df.columns else None)
    cvr_col = 'CVR' if 'CVR' in df.columns else ('cvr' if 'cvr' in df.columns else None)
    ctr_col = 'CTR' if 'CTR' in df.columns else ('ctr' if 'ctr' in df.columns else None)
    cost_col = '총비용' if '총비용' in df.columns else ('cost' if 'cost' in df.columns else None)
    conv_col = '총전환' if '총전환' in df.columns else ('conversions' if 'conversions' in df.columns else None)
    days_col = '집행일수' if '집행일수' in df.columns else ('days_active' if 'days_active' in df.columns else None)
    branches_col = '집행지점목록' if '집행지점목록' in df.columns else None
    # 시청 깊이 컬럼 (있을 때만 활용)
    v6s_col = '6s시청률' if '6s시청률' in df.columns else None
    p100_col = 'p100완료율' if 'p100완료율' in df.columns else None
    avg_sec_col = '평균재생초' if '평균재생초' in df.columns else None
    # 인게이지먼트 컬럼 (Phase 1C)
    share_col = '공유율' if '공유율' in df.columns else None
    like_col = '좋아요율' if '좋아요율' in df.columns else None
    eng15s_col = '15s시청률' if '15s시청률' in df.columns else None
    if not name_col or not tier_col or not branches_col:
        return {'branches': {}, 'tier_rationale': TIER_RATIONALE, 'note': '컬럼 누락'}

    TIER_ORDER = {'TIER1': 0, 'TIER2': 1, 'TIER3': 2, 'TIER4': 3, 'LOW_VOLUME': 4, 'UNCLASSIFIED': 5}

    def _to_int(v):
        return None if v is None or pd.isna(v) else int(v)

    def _to_float(v):
        return None if v is None or pd.isna(v) else float(v)

    # 소재 단위 누적 KPI (fallback용) — branch_kpi_lookup이 비어 있거나 미스 발생 시
    def _fallback_kpi(r):
        return {
            'cpa': r.get(cpa_col) if cpa_col else None,
            'cvr': r.get(cvr_col) if cvr_col else None,
            'ctr': r.get(ctr_col) if ctr_col else None,
            'cost': r.get(cost_col) if cost_col else None,
            'conv': r.get(conv_col) if conv_col else None,
            'days': r.get(days_col) if days_col else None,
            'v6s': r.get(v6s_col) if v6s_col else None,
            'p100': r.get(p100_col) if p100_col else None,
            'avg_sec': r.get(avg_sec_col) if avg_sec_col else None,
            'share': r.get(share_col) if share_col else None,
            'like': r.get(like_col) if like_col else None,
            'eng15s': r.get(eng15s_col) if eng15s_col else None,
        }

    branches_out = {}
    for branch in VALID_BRANCHES:
        def has_branch(lst, b=branch):
            try:
                return b in list(lst) if lst is not None else False
            except Exception:
                return False
        bdf = df[df[branches_col].apply(has_branch)].copy()
        if bdf.empty:
            continue
        items = []
        for _, r in bdf.iterrows():
            tier = str(r.get(tier_col, '')).upper()
            # 지점별 KPI lookup 시도 — (branch, 소재구분, 소재유형, 소재명) 키
            key = (branch, r.get('소재구분'), r.get('소재유형'), r.get('소재명'))
            bk = branch_kpi_lookup.get(key)
            if bk is not None:
                # 지점별 효율 사용
                cpa = bk.get('CPA')
                cvr = bk.get('CVR')
                ctr = bk.get('CTR')
                cost = bk.get('총비용')
                conv = bk.get('총전환')
                days = bk.get('집행일수')
                v6s = bk.get('6s시청률')
                p100 = bk.get('p100완료율')
                avg_sec = bk.get('평균재생초')
                share = bk.get('공유율')
                like = bk.get('좋아요율')
                eng15s = bk.get('15s시청률')
                kpi_source = 'branch'
            else:
                # 지점별 데이터 부재 시 소재 단위 누적값 fallback
                fb = _fallback_kpi(r)
                cpa = fb['cpa']; cvr = fb['cvr']; ctr = fb['ctr']
                cost = fb['cost']; conv = fb['conv']; days = fb['days']
                v6s = fb['v6s']; p100 = fb['p100']; avg_sec = fb['avg_sec']
                share = fb['share']; like = fb['like']; eng15s = fb['eng15s']
                kpi_source = 'aggregate'
            evidence_parts = []
            if cpa is not None and not pd.isna(cpa):
                evidence_parts.append(f"CPA {int(cpa):,}원")
            if cvr is not None and not pd.isna(cvr):
                evidence_parts.append(f"CVR {float(cvr):.2f}%")
            if ctr is not None and not pd.isna(ctr):
                evidence_parts.append(f"CTR {float(ctr):.2f}%")
            if v6s is not None and not pd.isna(v6s):
                evidence_parts.append(f"6s시청 {float(v6s):.1f}%")
            items.append({
                'name': str(r[name_col]),
                'tier': tier,
                'cpa': _to_int(cpa),
                'cvr': _to_float(cvr),
                'ctr': _to_float(ctr),
                'cost': _to_int(cost),
                'conversions': _to_int(conv),
                'days_active': _to_int(days),
                'v6s_rate': _to_float(v6s),
                'p100_rate': _to_float(p100),
                'avg_video_sec': _to_float(avg_sec),
                'share_rate': _to_float(share),
                'like_rate': _to_float(like),
                'eng15s_rate': _to_float(eng15s),
                'evidence': ' / '.join(evidence_parts),
                'recommended_action': TIER_ACTION.get(tier, ''),
                'kpi_source': kpi_source,
            })
        items.sort(key=lambda x: (TIER_ORDER.get(x['tier'], 99), x['cpa'] if x['cpa'] is not None else 10**9))
        branches_out[branch] = items

    # 데이터 출처 안내 — 현재 dir이 비어 다른 dir에서 가져왔을 경우 사용자에게 표시
    same_dir = Path(parsed_path).parent / 'creative_tier.parquet'
    data_source = None
    if tier_path != same_dir:
        data_source = tier_path.parent.name  # 예: '20260519'

    return {
        'branches': branches_out,
        'tier_rationale': TIER_RATIONALE,
        'tier_action_default': TIER_ACTION,
        'data_source_dir': data_source,
        'note': '액션 카드 inline은 핵심 TIER1/TIER4 1~2개. 부록은 지점별 전체 소재 표.',
    }


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260519/parsed.parquet'
    r = build(path)
    print(f"[부록 소재 표] 지점 {len(r['branches'])}개")
    for branch, items in r['branches'].items():
        print(f"\n[{branch}] {len(items)}개")
        for it in items[:5]:
            print(f"  {it['tier']:12s} {it['name'][:30]:30s} {it['evidence']}")
