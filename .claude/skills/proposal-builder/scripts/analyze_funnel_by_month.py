"""전기간 월별 × 지점별 퍼널 지표 (CPM, CTR, CVR)

입력: output/data/<latest>/parsed.parquet (또는 인자 path)
출력: 함수 호출 시 dict 반환 / CLI 실행 시 stdout 요약

OFF 소재 포함 (KPI 집계 규칙). _calc 컬럼은 행 단위라 평균 내면 안되므로
원시 합계(cost, impressions, clicks, conversions)로 재계산.
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES


def _active_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Rows with any measurable delivery. Zero-only API rows should not extend the effective period."""
    metric_cols = [c for c in ['cost', 'impressions', 'clicks', 'conversions'] if c in df.columns]
    if not metric_cols:
        return df
    return df[df[metric_cols].fillna(0).sum(axis=1) > 0]


def analyze(parsed_path: str) -> dict:
    df = pd.read_parquet(parsed_path)
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.strftime('%Y-%m')

    # 지점 컬럼: parsed_df 의 '지점' 사용 (parse_status=OK만 지점이 채워짐)
    df = df[df['지점'].isin(VALID_BRANCHES)].copy()

    # 월×지점 집계
    agg = df.groupby(['month', '지점']).agg(
        cost=('cost', 'sum'),
        impressions=('impressions', 'sum'),
        clicks=('clicks', 'sum'),
        conversions=('conversions', 'sum'),
        landing_views=('landing_views', 'sum'),
    ).reset_index()

    def kpi(row):
        cost, impr, clk, conv = row['cost'], row['impressions'], row['clicks'], row['conversions']
        return pd.Series({
            'cpm': round(cost / impr * 1000, 0) if impr > 0 else None,
            'ctr': round(clk / impr * 100, 2) if impr > 0 else None,
            'cvr': round(conv / clk * 100, 2) if clk > 0 else None,
            'cpa': round(cost / conv, 0) if conv > 0 else None,
            'lpv_rate': round(row['landing_views'] / clk * 100, 2) if clk > 0 else None,
        })

    metrics = agg.apply(kpi, axis=1)
    agg = pd.concat([agg, metrics], axis=1)

    months = sorted(agg['month'].unique())

    # 결과 구조화: by_month_branch[month][branch] = {kpis}
    by_month_branch = {}
    for m in months:
        by_month_branch[m] = {}
        for b in VALID_BRANCHES:
            row = agg[(agg['month'] == m) & (agg['지점'] == b)]
            if len(row) == 0:
                by_month_branch[m][b] = None
                continue
            r = row.iloc[0]
            by_month_branch[m][b] = {
                'cost': int(r['cost']),
                'impressions': int(r['impressions']),
                'clicks': int(r['clicks']),
                'conversions': int(r['conversions']),
                'cpm': None if pd.isna(r['cpm']) else int(r['cpm']),
                'ctr': None if pd.isna(r['ctr']) else float(r['ctr']),
                'cvr': None if pd.isna(r['cvr']) else float(r['cvr']),
                'cpa': None if pd.isna(r['cpa']) else int(r['cpa']),
                'lpv_rate': None if pd.isna(r['lpv_rate']) else float(r['lpv_rate']),
            }

    # 월별 전체 합계 (지점 무관)
    by_month_total = {}
    for m in months:
        mdf = df[df['month'] == m]
        cost = int(mdf['cost'].sum())
        impr = int(mdf['impressions'].sum())
        clk = int(mdf['clicks'].sum())
        conv = int(mdf['conversions'].sum())
        by_month_total[m] = {
            'cost': cost, 'impressions': impr, 'clicks': clk, 'conversions': conv,
            'cpm': int(cost / impr * 1000) if impr > 0 else None,
            'ctr': round(clk / impr * 100, 2) if impr > 0 else None,
            'cvr': round(conv / clk * 100, 2) if clk > 0 else None,
            'cpa': int(cost / conv) if conv > 0 else None,
        }

    # 5월 데이터 완전성 표시.
    # API 수집상 광고 행은 남아 있지만 비용/노출/클릭/전환이 모두 0인 날짜가 생길 수 있다.
    # 제안서의 "마지막"은 유효 성과가 발생한 마지막 일자를 사용한다.
    active_df = _active_rows(df)
    last_date = active_df['date'].max().strftime('%Y-%m-%d') if not active_df.empty else df['date'].max().strftime('%Y-%m-%d')
    raw_last_date = df['date'].max().strftime('%Y-%m-%d')

    return {
        'months': months,
        'branches': VALID_BRANCHES,
        'by_month_branch': by_month_branch,
        'by_month_total': by_month_total,
        'last_date': last_date,
        'raw_last_date': raw_last_date,
    }


if __name__ == '__main__':
    import json
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260506/parsed.parquet'
    result = analyze(path)
    print(f"기간: {result['months'][0]} ~ {result['months'][-1]} (마지막 데이터: {result['last_date']})")
    print(f"\n[월별 전체 퍼널]")
    for m in result['months']:
        t = result['by_month_total'][m]
        print(f"  {m}: CPM={t['cpm']}원 / CTR={t['ctr']}% / CVR={t['cvr']}% / CPA={t['cpa']}원")
    print(f"\n[5월 지점별]")
    last_m = result['months'][-1]
    for b in result['branches']:
        x = result['by_month_branch'][last_m].get(b)
        if x is None:
            print(f"  {b}: 데이터 없음")
            continue
        print(f"  {b}: CPM={x['cpm']}원 / CTR={x['ctr']}% / CVR={x['cvr']}%")
