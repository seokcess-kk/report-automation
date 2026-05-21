"""애드온 소재 적용 전후 성과 비교 (R11 보수적 압축)

설계:
  · 본문용: overall + by_creative_type (인사이트 핵심)
  · 부록용: by_branch + creative_pairs + monthly_trend (디테일)
  · 통계 유의성(z-test for CVR proportions) 모두 포함
  · 표본 부족(클릭 <100) 경고 별도 메타필드

입력:
  - parsed.parquet
  - input/tiktok_ad_meta.csv (ad_id × is_addon)
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES

SAMPLE_MIN_CLICKS = 100   # 본문 추천 대상 최소 표본
PAIR_MIN_CLICKS = 100     # 매칭키 페어 비교 최소 표본
TYPE_MIN_CLICKS = 50      # 소재유형 분해 최소 표본


def _kpis(g: pd.DataFrame) -> dict:
    cost = int(g['cost'].sum())
    impr = int(g['impressions'].sum())
    clicks = int(g['clicks'].sum())
    conv = int(g['conversions'].sum())
    return {
        'ad_count': int(g['ad_id'].nunique()) if len(g) else 0,
        'cost': cost,
        'impressions': impr,
        'clicks': clicks,
        'conversions': conv,
        'cpm': round(cost / impr * 1000) if impr else None,
        'ctr': round(clicks / impr * 100, 2) if impr else None,
        'cvr': round(conv / clicks * 100, 2) if clicks else None,
        'cpa': round(cost / conv) if conv else None,
    }


def _delta(addon_v, non_v, direction: str):
    """direction='low' (CPM/CPA): 음수면 애드온 우수. 'high' (CTR/CVR): 양수면 우수."""
    if addon_v is None or non_v is None or non_v == 0:
        return None
    return round((addon_v - non_v) / non_v * 100, 1)


def _cvr_ztest(conv_a, click_a, conv_b, click_b):
    """두 비율(CVR) Z-test. p<0.05면 통계적으로 유의.
    표본이 0이거나 극단적이면 None 반환."""
    if not click_a or not click_b:
        return None, None
    p_a = conv_a / click_a
    p_b = conv_b / click_b
    p_pool = (conv_a + conv_b) / (click_a + click_b)
    if p_pool <= 0 or p_pool >= 1:
        return None, None
    se = (p_pool * (1 - p_pool) * (1/click_a + 1/click_b)) ** 0.5
    if se == 0:
        return None, None
    z = (p_a - p_b) / se
    # 표준정규 누적분포 근사 (scipy 의존 회피)
    # erf 근사 (Abramowitz & Stegun 7.1.26)
    import math
    def _norm_cdf(x):
        # Phi(x) using erf
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))
    p_value = 2 * (1 - _norm_cdf(abs(z)))
    return round(z, 2), round(p_value, 4)


def _delta_block(addon: dict, non: dict) -> dict:
    z, p = _cvr_ztest(addon['conversions'], addon['clicks'], non['conversions'], non['clicks'])
    return {
        'cpm': _delta(addon['cpm'], non['cpm'], 'low'),
        'ctr': _delta(addon['ctr'], non['ctr'], 'high'),
        'cvr': _delta(addon['cvr'], non['cvr'], 'high'),
        'cpa': _delta(addon['cpa'], non['cpa'], 'low'),
        'cvr_z': z,
        'cvr_p': p,
        'cvr_significant': bool(p is not None and p < 0.05),
    }


def _classify_action(by_type_row: dict, min_clicks: int = SAMPLE_MIN_CLICKS) -> dict:
    """소재유형별 운영 판단 — 단순 규칙.
    - 표본 부족(양쪽 클릭 < min): 판단 보류
    - CVR Δ > 0 AND p<0.05: 확대
    - CVR Δ < 0 OR CPA 악화 > 10%: 보류
    - 기타: 직관 운영 (유의성 부족)
    """
    a = by_type_row['addon']
    n = by_type_row['non_addon']
    d = by_type_row['delta_pct']
    if a['clicks'] < min_clicks or n['clicks'] < min_clicks:
        return {'verdict': 'low_sample', 'label': '표본 부족 — 판단 보류', 'rationale': f"애드온 클릭 {a['clicks']:,} / 비애드온 클릭 {n['clicks']:,} (기준 {min_clicks:,})"}
    cvr_d = d.get('cvr')
    cpa_d = d.get('cpa')
    sig = d.get('cvr_significant')
    if cvr_d is not None and cvr_d > 0 and sig:
        return {'verdict': 'expand', 'label': '6월 확대 권고', 'rationale': f"CVR +{cvr_d}% · CPA {cpa_d}% (p={d.get('cvr_p')}, 통계적 유의)"}
    if (cvr_d is not None and cvr_d < 0) or (cpa_d is not None and cpa_d > 10):
        return {'verdict': 'hold', 'label': '6월 보류', 'rationale': f"CVR {cvr_d}% · CPA {cpa_d}% (애드온 부정적 신호)"}
    return {'verdict': 'noop', 'label': '직관 운영 (유의성 부족)', 'rationale': f"CVR {cvr_d}% · CPA {cpa_d}% (p={d.get('cvr_p')}, 통계적 유의성 없음)"}


def analyze(parsed_path: str, meta_path: str = 'input/tiktok_ad_meta.csv') -> dict:
    df = pd.read_parquet(parsed_path)
    df['date'] = pd.to_datetime(df['date'])
    df['ad_id'] = df['ad_id'].astype(str)
    df = df[df['parse_status'] == 'OK'].copy()
    df = df[df['지점'].isin(VALID_BRANCHES)].dropna(subset=['매칭키'])
    df['month'] = df['date'].dt.strftime('%Y-%m')

    meta = pd.read_csv(meta_path, dtype={'ad_id': str}, encoding='utf-8-sig')
    meta = meta[['ad_id', 'is_addon']].copy()
    meta['is_addon'] = meta['is_addon'].astype(str).str.lower().isin(['true', '1', '1.0'])

    merged = df.merge(meta, on='ad_id', how='left')
    merged['is_addon'] = merged['is_addon'].fillna(False).astype(bool)

    # ---- 1. 전체 (본문 5.2 합산) ----
    addon_total = _kpis(merged[merged['is_addon'] == True])
    non_total = _kpis(merged[merged['is_addon'] == False])
    overall = {
        'addon': addon_total,
        'non_addon': non_total,
        'delta_pct': _delta_block(addon_total, non_total),
    }

    # ---- 2. 소재유형별 분해 (본문 5.2 inline) ----
    by_creative_type = {}
    creative_type_verdicts = []
    for ct in sorted(merged['소재유형'].fillna('미상').unique()):
        sub = merged[merged['소재유형'].fillna('미상') == ct]
        a = _kpis(sub[sub['is_addon'] == True])
        n = _kpis(sub[sub['is_addon'] == False])
        block = {
            'addon': a,
            'non_addon': n,
            'delta_pct': _delta_block(a, n),
        }
        verdict = _classify_action(block, min_clicks=TYPE_MIN_CLICKS)
        block['verdict'] = verdict
        by_creative_type[str(ct)] = block
        creative_type_verdicts.append({'creative_type': str(ct), **verdict})

    # ---- 3. 운영 판단 요약 (본문 5.1) ----
    expand_types = [v['creative_type'] for v in creative_type_verdicts if v['verdict'] == 'expand']
    hold_types = [v['creative_type'] for v in creative_type_verdicts if v['verdict'] == 'hold']
    noop_types = [v['creative_type'] for v in creative_type_verdicts if v['verdict'] == 'noop']
    low_sample_types = [v['creative_type'] for v in creative_type_verdicts if v['verdict'] == 'low_sample']
    judgement = {
        'expand': expand_types,
        'hold': hold_types,
        'noop': noop_types,
        'low_sample': low_sample_types,
        'headline': (
            f"6월 운영: 확대 {expand_types or '—'} · 보류 {hold_types or '—'} · 직관 운영 {noop_types or '—'}"
            + (f" · 표본 부족 {low_sample_types}" if low_sample_types else "")
        ),
    }

    # ---- 4. 지점별 (부록) ----
    by_branch = {}
    for b in VALID_BRANCHES:
        bdf = merged[merged['지점'] == b]
        a = _kpis(bdf[bdf['is_addon'] == True])
        n = _kpis(bdf[bdf['is_addon'] == False])
        sample_warning = a['clicks'] < SAMPLE_MIN_CLICKS or n['clicks'] < SAMPLE_MIN_CLICKS
        by_branch[b] = {
            'addon': a,
            'non_addon': n,
            'delta_pct': _delta_block(a, n),
            'sample_warning': sample_warning,
        }

    # ---- 5. 매칭키별 페어 비교 (부록) ----
    pairs = []
    for key, sub in merged.groupby('매칭키'):
        if sub['is_addon'].nunique() < 2:
            continue
        a = _kpis(sub[sub['is_addon'] == True])
        n = _kpis(sub[sub['is_addon'] == False])
        if a['clicks'] < PAIR_MIN_CLICKS or n['clicks'] < PAIR_MIN_CLICKS:
            continue
        d = _delta_block(a, n)
        pairs.append({
            'creative_name': str(key),
            'addon': a,
            'non_addon': n,
            'delta_pct': d,
        })
    # CVR Δ 큰 순
    pairs.sort(key=lambda p: (p['delta_pct'].get('cvr') or -1e9), reverse=True)

    # ---- 6. 월별 추세 (부록 — 시점별 효과 변화) ----
    monthly_trend = []
    for mn in sorted(merged['month'].unique()):
        sub = merged[merged['month'] == mn]
        a = _kpis(sub[sub['is_addon'] == True])
        n = _kpis(sub[sub['is_addon'] == False])
        sample_warning = a['clicks'] < SAMPLE_MIN_CLICKS or n['clicks'] < SAMPLE_MIN_CLICKS
        monthly_trend.append({
            'month': mn,
            'addon': a,
            'non_addon': n,
            'delta_pct': _delta_block(a, n),
            'sample_warning': sample_warning,
        })

    # ---- 7. 메타 요약 ----
    addon_ads = merged[merged['is_addon'] == True]['ad_id'].nunique()
    total_ads = merged['ad_id'].nunique()

    return {
        'meta_summary': {
            'addon_ads_in_data': int(addon_ads),
            'total_ads_in_data': int(total_ads),
            'addon_ratio': round(addon_ads / total_ads * 100, 1) if total_ads > 0 else 0,
            'thresholds': {
                'sample_min_clicks': SAMPLE_MIN_CLICKS,
                'pair_min_clicks': PAIR_MIN_CLICKS,
                'type_min_clicks': TYPE_MIN_CLICKS,
            },
        },
        'overall': overall,
        'by_creative_type': by_creative_type,
        'creative_type_verdicts': creative_type_verdicts,
        'judgement': judgement,
        'by_branch': by_branch,
        'creative_pairs': pairs,
        'monthly_trend': monthly_trend,
    }


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260518/parsed.parquet'
    meta = sys.argv[2] if len(sys.argv) > 2 else 'input/tiktok_ad_meta.csv'
    r = analyze(path, meta)

    print('[judgement]', r['judgement']['headline'])
    print()
    print('[overall]')
    o = r['overall']
    d = o['delta_pct']
    print(f"  CVR {o['addon']['cvr']}% vs {o['non_addon']['cvr']}% (Δ {d['cvr']}%, p={d['cvr_p']})")
    print(f"  CPA {o['addon']['cpa']:,}원 vs {o['non_addon']['cpa']:,}원 (Δ {d['cpa']}%)")
    print()
    print('[by_creative_type]')
    for ct, b in r['by_creative_type'].items():
        v = b['verdict']
        d = b['delta_pct']
        print(f"  {ct}: {v['label']} (CVR Δ {d['cvr']}%, p={d['cvr_p']}) — {v['rationale']}")
    print()
    print('[monthly_trend]')
    for m in r['monthly_trend']:
        d = m['delta_pct']
        warn = ' ⚠ 표본 적음' if m['sample_warning'] else ''
        print(f"  {m['month']}: CVR Δ {d['cvr']}% (p={d['cvr_p']}){warn}")
