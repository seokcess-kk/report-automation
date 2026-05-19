"""전환 수 관점 분석 — 캠페인 핵심 목적(전환수)을 절대량·효율 양쪽에서 평가

목표값 의존 제거 (사전 정의된 월 목표 사용 안 함).
대신 전 기간(2~5월) 데이터를 종합해 다음을 제공:

  · 전 지점/지점별 전 기간 누적 KPI (전환수, 비용, CPA, 일평균 전환)
  · 지점별 전환 비중 (전 지점 합산 대비 %)
  · CPA 효율 등급 (전 지점 평균 ±15% 기준)
  · 월별 전체 전환수 추이 (5월은 부분 데이터로 별도 표시)

누적 KPI 베이스라인: 2026-02~05 (전 기간, 5월은 부분 데이터 포함)
베스트월 비교에서는 5월 부분 데이터 제외 (NORMAL_MONTHS 별도 유지).
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES

NORMAL_MONTHS = ['2026-02', '2026-03', '2026-04']
PARTIAL_MONTH = '2026-05'

# CPA 효율 등급 임계값 (전 지점 평균 대비)
CPA_EFFICIENT = 0.85   # -15% 이하 → 효율 우수
CPA_INEFFICIENT = 1.15  # +15% 이상 → 효율 부진


def _kpi(df: pd.DataFrame, month: str = None, branch: str = None) -> dict | None:
    sub = df
    if month is not None:
        sub = sub[sub['month'] == month]
    if branch is not None:
        sub = sub[sub['지점'] == branch]
    if len(sub) == 0:
        return None
    cost = float(sub['cost'].sum())
    impr = float(sub['impressions'].sum())
    clk = float(sub['clicks'].sum())
    conv = float(sub['conversions'].sum())
    days = int(sub['date'].dt.date.nunique()) if 'date' in sub.columns else 0
    return {
        'cost': int(cost),
        'impressions': int(impr),
        'clicks': int(clk),
        'conversions': int(conv),
        'cpm': int(cost / impr * 1000) if impr > 0 else None,
        'ctr': round(clk / impr * 100, 2) if impr > 0 else None,
        'cvr': round(conv / clk * 100, 2) if clk > 0 else None,
        'cpa': int(cost / conv) if conv > 0 else None,
        'cpc': round(cost / clk, 0) if clk > 0 else None,
        'days_active': days,
        'daily_conversions': round(conv / days, 2) if days > 0 else 0,
    }


def _cpa_grade(branch_cpa: int | None, peer_cpa: int | None) -> dict:
    """CPA 효율 등급."""
    if branch_cpa is None or peer_cpa is None or peer_cpa == 0:
        return {'grade': 'unknown', 'label': '평가 불가', 'ratio_pct': None}
    ratio = branch_cpa / peer_cpa
    delta_pct = round((ratio - 1) * 100, 1)
    if ratio <= CPA_EFFICIENT:
        return {'grade': 'efficient', 'label': '효율 우수', 'ratio_pct': delta_pct}
    if ratio >= CPA_INEFFICIENT:
        return {'grade': 'inefficient', 'label': '효율 부진', 'ratio_pct': delta_pct}
    return {'grade': 'average', 'label': '평균 수준', 'ratio_pct': delta_pct}


def analyze(parsed_path: str) -> dict:
    df = pd.read_parquet(parsed_path)
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.strftime('%Y-%m')
    df = df[df['지점'].isin(VALID_BRANCHES)].copy()

    months = sorted(df['month'].unique())

    # 전 지점 합산 (전 기간 2~5월 누적, 5월 부분 데이터 포함)
    overall_full = _kpi(df)
    peer_cpa = overall_full['cpa'] if overall_full else None
    total_conv = overall_full['conversions'] if overall_full else 0

    # 월별 전체 전환수 추이 (5월 포함, 부분 표시)
    monthly_total = {}
    for m in months:
        k = _kpi(df, month=m)
        if k:
            monthly_total[m] = k

    # 지점별 분석
    by_branch = {}
    for branch in VALID_BRANCHES:
        bdf = df[df['지점'] == branch]

        # 전 기간 누적 (2~5월, 5월 부분 포함)
        period_total = _kpi(bdf)
        # 월별 KPI (정상월만 - 추세/베스트월 비교용)
        monthly = {m: _kpi(bdf, month=m) for m in NORMAL_MONTHS}
        # 5월 부분 운영 (참고)
        partial_may = _kpi(bdf, month=PARTIAL_MONTH)
        # 신규 지점 여부 (정상월 데이터 전혀 없음)
        has_normal = any(monthly[m] is not None for m in NORMAL_MONTHS)
        is_new = not has_normal
        is_partial_source = is_new and partial_may is not None

        if period_total is None:
            by_branch[branch] = {
                'is_new_branch': is_new,
                'is_partial_source': False,
                'period_total': None,
                'monthly_history': monthly,
                'partial_may': partial_may,
                'conv_share_pct': None,
                'cpa_grade': {'grade': 'new', 'label': '신규 지점 - 데이터 없음', 'ratio_pct': None},
            }
            continue

        share = round(period_total['conversions'] / total_conv * 100, 1) if total_conv > 0 else 0
        grade = _cpa_grade(period_total['cpa'], peer_cpa)
        # 신규(5월 부분만 운영) 지점은 별도 등급 라벨
        if is_partial_source:
            grade = {**grade, 'label': f"신규 (5월 부분) · {grade['label']}", 'grade': 'new'}

        by_branch[branch] = {
            'is_new_branch': is_new,
            'is_partial_source': is_partial_source,
            'period_total': period_total,
            'monthly_history': monthly,
            'partial_may': partial_may,
            'conv_share_pct': share,
            'cpa_grade': grade,
        }

    return {
        'baseline_period': months,  # 전 기간 (2~5월)
        'normal_months': NORMAL_MONTHS,  # 베스트월 비교에 사용
        'partial_month': PARTIAL_MONTH,
        'partial_note': '2026-05는 운영 도중 중단된 부분 데이터(15일까지). 누적 KPI에는 포함되며, 베스트월 산정에서만 제외.',
        'months': months,
        'monthly_total': monthly_total,
        'overall': overall_full,
        'branches': VALID_BRANCHES,
        'by_branch': by_branch,
        'methodology': '누적 KPI는 전 기간(2~5월) 데이터 사용. 5월은 부분 데이터로 비율 지표(CPM/CTR/CVR/CPA)에 미치는 영향은 제한적이나, 절대량(전환수·비용)에는 포함.',
    }


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260518/parsed.parquet'
    r = analyze(path)
    o = r['overall']
    print(f"[전 지점 합산 - 전 기간 정상 운영 누적]")
    print(f"  전환수 {o['conversions']:,}건 / 비용 {o['cost']:,}원 / CPA {o['cpa']:,}원 / 일평균 전환 {o['daily_conversions']}건\n")
    print(f"[지점별]")
    print(f"{'지점':<6} {'전환수':>6} {'비중':>6} {'CPA':>9} {'등급':<12} {'일평균':>7}")
    for b in r['branches']:
        d = r['by_branch'][b]
        if not d['period_total']:
            print(f"{b:<6} {'-':>6} {'-':>6} {'-':>9} {d['cpa_grade']['label']:<12}")
            continue
        pt = d['period_total']
        ratio = d['cpa_grade']['ratio_pct']
        ratio_str = f"({ratio:+.0f}%)" if ratio is not None else ''
        print(f"{b:<6} {pt['conversions']:>6} {d['conv_share_pct']:>5}% {pt['cpa']:>9,} {d['cpa_grade']['label']:<12} {pt['daily_conversions']:>7} {ratio_str}")
