"""전기간 퍼널별 × 지점별 우수 콘텐츠 TOP3

각 지점마다 CPM(낮은 순), CTR(높은 순), CVR(높은 순) TOP3 소재 추출.
- 그룹 단위: (지점, 매칭키)
- 저볼륨 제외: 클릭 < 100 OR 비용 < 100,000원
- CVR TOP3 추가 조건: 전환 ≥ 3건
- creative_name = 소재유형_소재명 (절대 규칙 #6: ad_name 아님)
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES


MIN_CLICKS = 100
MIN_COST = 100_000
MIN_CONVERSIONS_FOR_CVR = 3
MIN_CONVERSIONS_FOR_CPA = 5  # CPA TOP은 표본 신뢰성 위해 더 엄격
TOP_N = 3


def _aggregate_creatives(df: pd.DataFrame) -> pd.DataFrame:
    """지점 × 매칭키 기준 집계 → 퍼널 지표 계산."""
    active_mask = df[['cost', 'impressions', 'clicks', 'conversions']].fillna(0).sum(axis=1) > 0
    df = df.copy()
    df['_active_date'] = df['date'].where(active_mask)
    grp = df.groupby(['지점', '매칭키'], dropna=False).agg(
        cost=('cost', 'sum'),
        impressions=('impressions', 'sum'),
        clicks=('clicks', 'sum'),
        conversions=('conversions', 'sum'),
        landing_views=('landing_views', 'sum'),
        days_active=('_active_date', lambda x: x.dropna().dt.date.nunique()),
        is_off_any=('is_off', 'any'),
        is_off_all=('is_off', 'all'),
        ad_count=('ad_id', 'nunique'),
    ).reset_index()

    grp['cpm'] = (grp['cost'] / grp['impressions'] * 1000).where(grp['impressions'] > 0).round(0)
    grp['ctr'] = (grp['clicks'] / grp['impressions'] * 100).where(grp['impressions'] > 0).round(2)
    grp['cvr'] = (grp['conversions'] / grp['clicks'] * 100).where(grp['clicks'] > 0).round(2)
    grp['cpa'] = (grp['cost'] / grp['conversions']).where(grp['conversions'] > 0).round(0)
    grp['lpv_rate'] = (grp['landing_views'] / grp['clicks'] * 100).where(grp['clicks'] > 0).round(2)
    return grp


def _row_to_card(row: pd.Series, focus_metric: str) -> dict:
    return {
        'creative_name': row['매칭키'],
        'branch': row['지점'],
        'metric_focus': focus_metric,
        'metric_value': None if pd.isna(row[focus_metric]) else float(row[focus_metric]),
        'cost': int(row['cost']),
        'impressions': int(row['impressions']),
        'clicks': int(row['clicks']),
        'conversions': int(row['conversions']),
        'cpm': None if pd.isna(row['cpm']) else int(row['cpm']),
        'ctr': None if pd.isna(row['ctr']) else float(row['ctr']),
        'cvr': None if pd.isna(row['cvr']) else float(row['cvr']),
        'cpa': None if pd.isna(row['cpa']) else int(row['cpa']),
        'days_active': int(row['days_active']),
        'is_off': bool(row['is_off_all']),
    }


def _row_to_volume_card(row: pd.Series, focus_metric: str, branch_total_conv: int) -> dict:
    """전환수 관점 카드 (전환 점유율·일평균 전환 추가)."""
    share = (row['conversions'] / branch_total_conv * 100) if branch_total_conv > 0 else 0
    daily_conv = (row['conversions'] / row['days_active']) if row['days_active'] > 0 else 0
    return {
        'creative_name': row['매칭키'],
        'branch': row['지점'],
        'metric_focus': focus_metric,
        'metric_value': None if pd.isna(row[focus_metric]) else float(row[focus_metric]),
        'cost': int(row['cost']),
        'impressions': int(row['impressions']),
        'clicks': int(row['clicks']),
        'conversions': int(row['conversions']),
        'cpm': None if pd.isna(row['cpm']) else int(row['cpm']),
        'ctr': None if pd.isna(row['ctr']) else float(row['ctr']),
        'cvr': None if pd.isna(row['cvr']) else float(row['cvr']),
        'cpa': None if pd.isna(row['cpa']) else int(row['cpa']),
        'days_active': int(row['days_active']),
        'is_off': bool(row['is_off_all']),
        'conv_share_pct': round(share, 1),
        'daily_conversions': round(daily_conv, 2),
    }


def analyze(parsed_path: str) -> dict:
    df = pd.read_parquet(parsed_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['parse_status'] == 'OK'].copy()
    df = df[df['지점'].isin(VALID_BRANCHES)]
    df = df.dropna(subset=['매칭키'])

    grouped = _aggregate_creatives(df)

    # 저볼륨 필터
    eligible = grouped[(grouped['clicks'] >= MIN_CLICKS) & (grouped['cost'] >= MIN_COST)].copy()

    # 지점별 전체 전환수 (점유율 계산용 — 모든 소재 포함)
    branch_total_conv = grouped.groupby('지점')['conversions'].sum().to_dict()

    # 지점별 × 카테고리별 TOP3 추출 (효율 + 양 양쪽)
    result = {b: {'cpm': [], 'ctr': [], 'cvr': [], 'volume': [], 'cpa': []} for b in VALID_BRANCHES}

    for b in VALID_BRANCHES:
        sub = eligible[eligible['지점'] == b].copy()
        if len(sub) == 0:
            continue

        btc = branch_total_conv.get(b, 0)

        # === 효율 관점 ===
        # CPM: 낮은 순
        cpm_top = sub.dropna(subset=['cpm']).nsmallest(TOP_N, 'cpm')
        result[b]['cpm'] = [_row_to_card(r, 'cpm') for _, r in cpm_top.iterrows()]

        # CTR: 높은 순
        ctr_top = sub.dropna(subset=['ctr']).nlargest(TOP_N, 'ctr')
        result[b]['ctr'] = [_row_to_card(r, 'ctr') for _, r in ctr_top.iterrows()]

        # CVR: 높은 순 (전환 ≥ 3건 조건)
        cvr_pool = sub[(sub['conversions'] >= MIN_CONVERSIONS_FOR_CVR)].dropna(subset=['cvr'])
        cvr_top = cvr_pool.nlargest(TOP_N, 'cvr')
        result[b]['cvr'] = [_row_to_card(r, 'cvr') for _, r in cvr_top.iterrows()]

        # === 양 관점 (전환수 증대 목적 직결) ===
        # 전환수 절대량 TOP3
        vol_top = sub.nlargest(TOP_N, 'conversions')
        result[b]['volume'] = [_row_to_volume_card(r, 'conversions', btc) for _, r in vol_top.iterrows()]

        # CPA 우수 TOP3 (전환 ≥ 5건 신뢰 표본)
        cpa_pool = sub[sub['conversions'] >= MIN_CONVERSIONS_FOR_CPA].dropna(subset=['cpa'])
        cpa_top = cpa_pool.nsmallest(TOP_N, 'cpa')
        result[b]['cpa'] = [_row_to_volume_card(r, 'cpa', btc) for _, r in cpa_top.iterrows()]

    return {
        'branches': VALID_BRANCHES,
        'criteria': {
            'min_clicks': MIN_CLICKS,
            'min_cost': MIN_COST,
            'min_conversions_for_cvr': MIN_CONVERSIONS_FOR_CVR,
            'min_conversions_for_cpa': MIN_CONVERSIONS_FOR_CPA,
            'top_n': TOP_N,
        },
        'by_branch': result,
        'eligible_count': len(eligible),
        'total_creatives': len(grouped),
    }


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260506/parsed.parquet'
    r = analyze(path)
    print(f"분석 대상: {r['eligible_count']}개 (전체 {r['total_creatives']}개 중)")
    for b in r['branches']:
        bd = r['by_branch'][b]
        print(f"\n[{b}]")
        for funnel in ('cpm', 'ctr', 'cvr'):
            print(f"  {funnel.upper()} TOP3:")
            for c in bd[funnel]:
                val = c['metric_value']
                tag = ' (OFF)' if c['is_off'] else ''
                print(f"    - {c['creative_name'][:60]}{tag} → {funnel}={val} (전환={c['conversions']}, 비용={c['cost']:,})")
