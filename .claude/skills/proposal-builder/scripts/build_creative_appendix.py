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
    same_dir = Path(parsed_path).parent / 'creative_tier.parquet'
    if same_dir.exists():
        return same_dir
    data_root = Path(parsed_path).parent.parent
    if not data_root.exists():
        return None
    candidates = sorted(
        [d for d in data_root.iterdir() if d.is_dir() and (d / 'creative_tier.parquet').exists()],
        key=lambda d: d.name,
        reverse=True,
    )
    return (candidates[0] / 'creative_tier.parquet') if candidates else None


def build(parsed_path: str) -> dict:
    """creative_tier.parquet에서 부록 표 데이터 생성. 같은 dir에 없으면 최신 dir 검색."""
    tier_path = _find_latest_creative_tier(parsed_path)
    if tier_path is None:
        return {'branches': {}, 'tier_rationale': TIER_RATIONALE, 'note': 'creative_tier.parquet 없음 - 부록 생략'}
    try:
        df = pd.read_parquet(tier_path)
    except Exception as e:
        return {'branches': {}, 'tier_rationale': TIER_RATIONALE, 'note': f'creative_tier 로드 실패: {e}'}
    if df.empty:
        return {'branches': {}, 'tier_rationale': TIER_RATIONALE, 'note': '데이터 없음'}

    name_col = '매칭키' if '매칭키' in df.columns else ('creative_name' if 'creative_name' in df.columns else None)
    tier_col = 'TIER' if 'TIER' in df.columns else ('tier' if 'tier' in df.columns else None)
    cpa_col = 'CPA' if 'CPA' in df.columns else ('cpa' if 'cpa' in df.columns else None)
    cvr_col = 'CVR' if 'CVR' in df.columns else ('cvr' if 'cvr' in df.columns else None)
    ctr_col = 'CTR' if 'CTR' in df.columns else ('ctr' if 'ctr' in df.columns else None)
    cost_col = '총비용' if '총비용' in df.columns else ('cost' if 'cost' in df.columns else None)
    conv_col = '총전환' if '총전환' in df.columns else ('conversions' if 'conversions' in df.columns else None)
    days_col = '집행일수' if '집행일수' in df.columns else ('days_active' if 'days_active' in df.columns else None)
    branches_col = '집행지점목록' if '집행지점목록' in df.columns else None
    if not name_col or not tier_col or not branches_col:
        return {'branches': {}, 'tier_rationale': TIER_RATIONALE, 'note': '컬럼 누락'}

    TIER_ORDER = {'TIER1': 0, 'TIER2': 1, 'TIER3': 2, 'TIER4': 3, 'LOW_VOLUME': 4, 'UNCLASSIFIED': 5}

    def _to_int(v):
        return None if v is None or pd.isna(v) else int(v)

    def _to_float(v):
        return None if v is None or pd.isna(v) else float(v)

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
            cpa = r.get(cpa_col) if cpa_col else None
            cvr = r.get(cvr_col) if cvr_col else None
            ctr = r.get(ctr_col) if ctr_col else None
            cost = r.get(cost_col) if cost_col else None
            conv = r.get(conv_col) if conv_col else None
            days = r.get(days_col) if days_col else None
            evidence_parts = []
            if cpa is not None and not pd.isna(cpa):
                evidence_parts.append(f"CPA {int(cpa):,}원")
            if cvr is not None and not pd.isna(cvr):
                evidence_parts.append(f"CVR {float(cvr):.2f}%")
            if ctr is not None and not pd.isna(ctr):
                evidence_parts.append(f"CTR {float(ctr):.2f}%")
            items.append({
                'name': str(r[name_col]),
                'tier': tier,
                'cpa': _to_int(cpa),
                'cvr': _to_float(cvr),
                'ctr': _to_float(ctr),
                'cost': _to_int(cost),
                'conversions': _to_int(conv),
                'days_active': _to_int(days),
                'evidence': ' / '.join(evidence_parts),
                'recommended_action': TIER_ACTION.get(tier, ''),
            })
        items.sort(key=lambda x: (TIER_ORDER.get(x['tier'], 99), x['cpa'] if x['cpa'] is not None else 10**9))
        branches_out[branch] = items

    return {
        'branches': branches_out,
        'tier_rationale': TIER_RATIONALE,
        'tier_action_default': TIER_ACTION,
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
