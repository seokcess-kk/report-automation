"""애드온 소재 적용 전후 성과 비교

입력:
  - output/data/<date>/parsed.parquet (일별 × 광고 단위 성과)
  - input/tiktok_ad_meta.csv (ad_id 별 애드온 적용 여부)

산출:
  - 전체 합산: 애드온 vs 비애드온 KPI
  - 지점별: 애드온 vs 비애드온 KPI
  - 같은 매칭키(소재유형_소재명) 안에서 애드온 vs 비애드온 짝 비교
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES


def _kpis(g: pd.DataFrame) -> dict:
    cost = int(g['cost'].sum())
    impr = int(g['impressions'].sum())
    clk = int(g['clicks'].sum())
    conv = int(g['conversions'].sum())
    ad_count = int(g['ad_id'].nunique()) if 'ad_id' in g.columns else 0
    return {
        'ad_count': ad_count,
        'cost': cost,
        'impressions': impr,
        'clicks': clk,
        'conversions': conv,
        'cpm': int(cost / impr * 1000) if impr > 0 else None,
        'ctr': round(clk / impr * 100, 2) if impr > 0 else None,
        'cvr': round(conv / clk * 100, 2) if clk > 0 else None,
        'cpa': int(cost / conv) if conv > 0 else None,
    }


def _delta(addon_v, non_v, direction: str) -> float | None:
    """직접 비교 가능한 퍼센트 차이.
    direction='low' (CPM/CPA): 음수면 애드온이 더 낮음(=좋음)
    direction='high' (CTR/CVR): 양수면 애드온이 더 높음(=좋음)
    """
    if addon_v is None or non_v is None or non_v == 0:
        return None
    return round((addon_v - non_v) / non_v * 100, 1)


def analyze(parsed_path: str, meta_path: str = 'input/tiktok_ad_meta.csv') -> dict:
    df = pd.read_parquet(parsed_path)
    df['date'] = pd.to_datetime(df['date'])
    df['ad_id'] = df['ad_id'].astype(str)
    df = df[df['parse_status'] == 'OK'].copy()
    df = df[df['지점'].isin(VALID_BRANCHES)].dropna(subset=['매칭키'])

    meta = pd.read_csv(meta_path, dtype={'ad_id': str}, encoding='utf-8-sig')
    meta = meta[['ad_id', 'is_addon', 'addon_kind']].copy()
    # CSV는 boolean을 'True'/'False' 문자열로 저장
    meta['is_addon'] = meta['is_addon'].astype(str).str.lower().isin(['true', '1', '1.0'])

    merged = df.merge(meta, on='ad_id', how='left')
    # 메타에 없는 광고는 비애드온으로 간주
    merged['is_addon'] = merged['is_addon'].fillna(False).astype(bool)
    merged['addon_kind'] = merged['addon_kind'].fillna('').astype(str)

    # ---- 1. 전체 ----
    addon_total = _kpis(merged[merged['is_addon'] == True])
    non_total = _kpis(merged[merged['is_addon'] == False])
    overall = {
        'addon': addon_total,
        'non_addon': non_total,
        'delta_pct': {
            'cpm': _delta(addon_total['cpm'], non_total['cpm'], 'low'),
            'ctr': _delta(addon_total['ctr'], non_total['ctr'], 'high'),
            'cvr': _delta(addon_total['cvr'], non_total['cvr'], 'high'),
            'cpa': _delta(addon_total['cpa'], non_total['cpa'], 'low'),
        },
    }

    # ---- 2. 지점별 ----
    by_branch = {}
    for b in VALID_BRANCHES:
        bdf = merged[merged['지점'] == b]
        a = _kpis(bdf[bdf['is_addon'] == True])
        n = _kpis(bdf[bdf['is_addon'] == False])
        by_branch[b] = {
            'addon': a,
            'non_addon': n,
            'delta_pct': {
                'cpm': _delta(a['cpm'], n['cpm'], 'low'),
                'ctr': _delta(a['ctr'], n['ctr'], 'high'),
                'cvr': _delta(a['cvr'], n['cvr'], 'high'),
                'cpa': _delta(a['cpa'], n['cpa'], 'low'),
            },
        }

    # ---- 3. 매칭키별 페어 (애드온/비애드온 모두 존재하는 매칭키만) ----
    pairs = []
    for key, sub in merged.groupby('매칭키'):
        if sub['is_addon'].nunique() < 2:
            continue
        a = _kpis(sub[sub['is_addon'] == True])
        n = _kpis(sub[sub['is_addon'] == False])
        # 표본 크기 필터 - 양쪽 모두 클릭 100 이상
        if a['clicks'] < 100 or n['clicks'] < 100:
            continue
        pairs.append({
            'creative_name': key,
            'addon': a,
            'non_addon': n,
            'delta_pct': {
                'cpm': _delta(a['cpm'], n['cpm'], 'low'),
                'ctr': _delta(a['ctr'], n['ctr'], 'high'),
                'cvr': _delta(a['cvr'], n['cvr'], 'high'),
                'cpa': _delta(a['cpa'], n['cpa'], 'low'),
            },
        })
    # delta CTR 큰 순으로
    pairs.sort(key=lambda p: (p['delta_pct'].get('ctr') or -1e9), reverse=True)

    # ---- 4. 메타 요약 ----
    addon_ads_in_data = merged[merged['is_addon'] == True]['ad_id'].nunique()
    total_ads_in_data = merged['ad_id'].nunique()

    return {
        'meta_summary': {
            'addon_ads_in_data': int(addon_ads_in_data),
            'total_ads_in_data': int(total_ads_in_data),
            'addon_ratio': round(addon_ads_in_data / total_ads_in_data * 100, 1) if total_ads_in_data > 0 else 0,
        },
        'overall': overall,
        'by_branch': by_branch,
        'creative_pairs': pairs,
    }


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260506/parsed.parquet'
    meta = sys.argv[2] if len(sys.argv) > 2 else 'input/tiktok_ad_meta.csv'
    r = analyze(path, meta)

    ms = r['meta_summary']
    print(f"애드온 적용 광고: {ms['addon_ads_in_data']}/{ms['total_ads_in_data']} ({ms['addon_ratio']}%)")

    o = r['overall']
    print(f"\n[전체 합산]")
    print(f"  애드온:   CPM={o['addon']['cpm']}원 CTR={o['addon']['ctr']}% CVR={o['addon']['cvr']}% CPA={o['addon']['cpa']}원 (광고{o['addon']['ad_count']}개)")
    print(f"  비애드온: CPM={o['non_addon']['cpm']}원 CTR={o['non_addon']['ctr']}% CVR={o['non_addon']['cvr']}% CPA={o['non_addon']['cpa']}원 (광고{o['non_addon']['ad_count']}개)")
    print(f"  Δ:        CPM={o['delta_pct']['cpm']}% CTR={o['delta_pct']['ctr']}% CVR={o['delta_pct']['cvr']}% CPA={o['delta_pct']['cpa']}%")

    print(f"\n[지점별 Δ (애드온 vs 비애드온)]")
    for b in VALID_BRANCHES:
        d = r['by_branch'][b]['delta_pct']
        a_n = r['by_branch'][b]['addon']['ad_count']
        n_n = r['by_branch'][b]['non_addon']['ad_count']
        print(f"  {b} (애드온 {a_n}개 / 비애드온 {n_n}개): CPM={d['cpm']}% CTR={d['ctr']}% CVR={d['cvr']}% CPA={d['cpa']}%")

    print(f"\n[페어 비교 가능 매칭키: {len(r['creative_pairs'])}건]")
    for p in r['creative_pairs'][:10]:
        d = p['delta_pct']
        print(f"  {p['creative_name'][:50]}: CTR Δ={d['ctr']}% / CVR Δ={d['cvr']}% / CPA Δ={d['cpa']}%")
