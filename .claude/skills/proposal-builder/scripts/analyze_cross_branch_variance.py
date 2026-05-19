"""동일 소재의 지점간 성과 차이 분석

같은 매칭키(소재유형_소재명)가 여러 지점에서 운영된 경우,
지점별 CPA·CVR이 얼마나 다른지 측정하여 운영 인사이트 도출.

핵심 산식:
  - 매칭키별 지점간 CPA 차이 = (max CPA - min CPA) / min CPA × 100
  - 변동 큰 소재 = '지점 적합성 차이 큼' → 잘 안 되는 지점에서 변주/교체
  - 변동 작은 소재 = '안정적' → 다른 지점 확대 가능

베이스라인: 정상 운영 월(2~4월)
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES

NORMAL_MONTHS = ['2026-02', '2026-03', '2026-04']
MIN_BRANCHES = 2          # 최소 2개 지점에서 운영
MIN_CONV_PER_BRANCH = 3   # 지점별 최소 전환 (신뢰성)
MIN_TOTAL_CONV = 10       # 매칭키 전체 최소 전환
GAP_THRESHOLD_HIGH = 100  # max/min CPA 차이 ≥100% = 큰 차이
GAP_THRESHOLD_MID = 50    # 50~100% = 중간 차이


def _kpi(df: pd.DataFrame) -> dict | None:
    if len(df) == 0:
        return None
    cost = float(df['cost'].sum())
    impr = float(df['impressions'].sum())
    clk = float(df['clicks'].sum())
    conv = float(df['conversions'].sum())
    return {
        'cost': int(cost),
        'impressions': int(impr),
        'clicks': int(clk),
        'conversions': int(conv),
        'cpa': int(cost / conv) if conv > 0 else None,
        'cvr': round(conv / clk * 100, 2) if clk > 0 else None,
        'ctr': round(clk / impr * 100, 2) if impr > 0 else None,
    }


def analyze(parsed_path: str) -> dict:
    df = pd.read_parquet(parsed_path)
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.strftime('%Y-%m')
    df = df[df['parse_status'] == 'OK'].copy()
    df = df[df['지점'].isin(VALID_BRANCHES)]
    df = df[df['month'].isin(NORMAL_MONTHS)]
    df = df.dropna(subset=['매칭키'])

    items = []
    for key, sub in df.groupby('매칭키'):
        total = _kpi(sub)
        if total is None or total['conversions'] < MIN_TOTAL_CONV:
            continue
        # 지점별 KPI
        by_branch = {}
        for b, bsub in sub.groupby('지점'):
            k = _kpi(bsub)
            if k and k['conversions'] >= MIN_CONV_PER_BRANCH and k['cpa']:
                by_branch[b] = k
        if len(by_branch) < MIN_BRANCHES:
            continue

        # CPA 통계
        cpas = [(b, k['cpa']) for b, k in by_branch.items()]
        cpas.sort(key=lambda x: x[1])
        best_branch, best_cpa = cpas[0]
        worst_branch, worst_cpa = cpas[-1]
        gap_pct = round((worst_cpa - best_cpa) / best_cpa * 100, 1) if best_cpa else 0
        # 변동 등급
        if gap_pct >= GAP_THRESHOLD_HIGH:
            variance_grade = 'high'
            variance_label = '지점 적합성 차이 큼'
        elif gap_pct >= GAP_THRESHOLD_MID:
            variance_grade = 'mid'
            variance_label = '지점간 차이 중간'
        else:
            variance_grade = 'low'
            variance_label = '안정적 (전 지점 일관)'

        # 운영 권장
        if variance_grade == 'high':
            recommendation = f'{best_branch} 우수 + {worst_branch} 부진. {worst_branch}에서는 변주/축소, {best_branch} 패턴 분석 후 다른 지점 확대'
        elif variance_grade == 'mid':
            recommendation = f'{best_branch} 베스트, {worst_branch} 점검 필요. 동일 소재의 지점별 운영 톤·예산 차이 확인'
        else:
            recommendation = f'전 지점에서 비교적 안정적. 미운영 지점 확대 후보'

        items.append({
            'creative_name': key,
            'n_branches': len(by_branch),
            'total_conversions': total['conversions'],
            'total_cpa': total['cpa'],
            'by_branch': by_branch,
            'best_branch': best_branch,
            'best_cpa': best_cpa,
            'worst_branch': worst_branch,
            'worst_cpa': worst_cpa,
            'gap_pct': gap_pct,
            'variance_grade': variance_grade,
            'variance_label': variance_label,
            'recommendation': recommendation,
        })

    # 변동 큰 순 정렬
    items.sort(key=lambda x: -x['gap_pct'])

    by_grade = {'high': [], 'mid': [], 'low': []}
    for it in items:
        by_grade[it['variance_grade']].append(it)

    # 자동 인사이트
    insights = []
    if by_grade['high']:
        top = by_grade['high'][0]
        insights.append({
            'label': '지점 적합성 차이 큰 소재',
            'detail': f"{len(by_grade['high'])}건 - 같은 소재가 지점별로 CPA 100%+ 차이. 1순위: '{top['creative_name'][:40]}' ({top['best_branch']} {top['best_cpa']:,}원 vs {top['worst_branch']} {top['worst_cpa']:,}원, {top['gap_pct']}% 차이)",
            'action': '6월: 부진 지점에서는 변주/축소, 우수 지점 패턴 분석 후 미운영 지점 확대',
        })
    if by_grade['low']:
        stable_cnt = len(by_grade['low'])
        insights.append({
            'label': '안정적 소재 (지점 영향 작음)',
            'detail': f"{stable_cnt}건 - 전 지점에서 비교적 일관된 성과. 미운영 지점 확대 시 예측 가능성 높음",
            'action': '6월: 미운영 지점에 적극 확대 후보',
        })
    if by_grade['mid']:
        insights.append({
            'label': '지점간 중간 차이 소재',
            'detail': f"{len(by_grade['mid'])}건 - CPA 50~100% 차이. 운영 톤·예산 배분 점검 가치 있음",
            'action': '베스트·워스트 지점간 운영 차이(시간대·예산·세팅) 비교 후 베스트 패턴 차용',
        })

    return {
        'baseline_period': NORMAL_MONTHS,
        'criteria': {
            'min_branches': MIN_BRANCHES,
            'min_conv_per_branch': MIN_CONV_PER_BRANCH,
            'min_total_conv': MIN_TOTAL_CONV,
            'gap_threshold_high': GAP_THRESHOLD_HIGH,
            'gap_threshold_mid': GAP_THRESHOLD_MID,
        },
        'items_count': len(items),
        'by_grade': by_grade,
        'items': items,
        'insights': insights,
    }


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260518/parsed.parquet'
    r = analyze(path)
    print(f'분석 대상 (다지점 운영 매칭키): {r["items_count"]}개\n')
    print(f"[변동 등급 분포]")
    print(f"  지점 적합성 차이 큼 (≥100%): {len(r['by_grade']['high'])}건")
    print(f"  중간 차이 (50~100%):        {len(r['by_grade']['mid'])}건")
    print(f"  안정적 (<50%):              {len(r['by_grade']['low'])}건")
    print()
    print(f"[차이 큰 소재 TOP10]")
    for it in r['items'][:10]:
        print(f"  • {it['creative_name'][:50]} ({it['n_branches']}개 지점)")
        print(f"      베스트 {it['best_branch']} {it['best_cpa']:,}원 vs 워스트 {it['worst_branch']} {it['worst_cpa']:,}원 (차이 {it['gap_pct']}%)")
    print()
    print('[자동 인사이트]')
    for ins in r['insights']:
        print(f"  • [{ins['label']}] {ins['detail']}")
        print(f"    → {ins['action']}")
