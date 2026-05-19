"""6월 전지점 비즈니스·퍼널 목표 산정 (전 기간 데이터 기반)

산정 로직:
  - 지점별로 정상 운영 월(2~4월) 중 베스트 월의 지표를 6월 목표로 채택
  - 비즈니스 KPI (Primary): 전환수(최대) / CPA(최소)
  - 퍼널 KPI (수단): CPM(최소) / CTR(최대) / CVR(최대)
  - 베스트 월은 지표별로 독립 선택
  - 보조 통계 (평균·중앙값·최악) 함께 제공하여 목표 객관성 검증

5월은 운영 도중 중단된 부분 데이터로 어떤 시점 비교도 하지 않음.
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES

# 베스트 월 후보 (완전한 월만)
COMPLETE_MONTHS = ['2026-02', '2026-03', '2026-04']
CURRENT_MONTH = '2026-05'  # 갭 계산용


def _kpi_for_branch_month(df: pd.DataFrame, branch: str, month: str) -> dict | None:
    sub = df[(df['지점'] == branch) & (df['month'] == month)]
    if len(sub) == 0:
        return None
    cost = int(sub['cost'].sum())
    impr = int(sub['impressions'].sum())
    clk = int(sub['clicks'].sum())
    conv = int(sub['conversions'].sum())
    return {
        'cost': cost,
        'impressions': impr,
        'clicks': clk,
        'conversions': conv,
        'cpm': int(cost / impr * 1000) if impr > 0 else None,
        'ctr': round(clk / impr * 100, 2) if impr > 0 else None,
        'cvr': round(conv / clk * 100, 2) if clk > 0 else None,
        'cpa': int(cost / conv) if conv > 0 else None,
    }


def _pick_best(kpis_by_month: dict, metric: str, direction: str) -> tuple[str | None, float | None]:
    """direction: 'low' (낮을수록 좋음) | 'high' (높을수록 좋음)
    Returns: (best_month, best_value)
    """
    candidates = [(m, k[metric]) for m, k in kpis_by_month.items() if k and k.get(metric) is not None]
    if not candidates:
        return None, None
    if direction == 'low':
        return min(candidates, key=lambda x: x[1])
    return max(candidates, key=lambda x: x[1])


def _compute_aux_stats(kpis_by_month: dict, metric: str, direction: str) -> dict:
    """평균/중앙값/최악 - 베스트 월 목표가 낙관적이지 않은지 객관 비교용 보조 지표.

    direction='low' (CPM): worst = 가장 높은 값
    direction='high' (CTR/CVR): worst = 가장 낮은 값
    """
    import statistics
    vals = [(m, k[metric]) for m, k in kpis_by_month.items() if k and k.get(metric) is not None]
    if not vals:
        return {'mean': None, 'median': None, 'worst': None, 'worst_month': None}
    nums = [v for _, v in vals]
    if direction == 'low':
        worst_pair = max(vals, key=lambda x: x[1])
    else:
        worst_pair = min(vals, key=lambda x: x[1])
    return {
        'mean': round(statistics.mean(nums), 2),
        'median': round(statistics.median(nums), 2),
        'worst': round(worst_pair[1], 2),
        'worst_month': worst_pair[0],
    }


def _gap_pct(current: float | None, target: float | None, direction: str) -> float | None:
    """현재 → 목표까지의 갭 (%).
    direction='low' (CPM): 목표가 더 낮을수록 좋음. 현재가 목표보다 높으면 음수.
    direction='high' (CTR/CVR): 목표가 더 높을수록 좋음. 현재가 목표보다 낮으면 음수.

    Returns: 양수=이미 달성, 음수=개선 필요 (절댓값 = 필요 변동률 %)
    """
    if current is None or target is None or current == 0:
        return None
    if direction == 'low':
        # 현재가 목표보다 낮을수록 양수 (이미 달성). (target - current) / current
        # 양수 = 목표보다 좋음, 음수 = 개선 필요
        return round((target - current) / current * 100, 1)
    # high: (current - target) / target. 양수면 이미 달성, 음수면 개선 필요
    return round((current - target) / target * 100, 1)


def analyze(parsed_path: str) -> dict:
    df = pd.read_parquet(parsed_path)
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.strftime('%Y-%m')
    df = df[df['지점'].isin(VALID_BRANCHES)].copy()

    targets = {}

    for branch in VALID_BRANCHES:
        # 정상 운영 월들의 KPI (2~4월)
        kpis = {m: _kpi_for_branch_month(df, branch, m) for m in COMPLETE_MONTHS}

        # 비즈니스 KPI 베스트 (Primary)
        best_conv_month, best_conv = _pick_best(kpis, 'conversions', 'high')
        best_cpa_month, best_cpa = _pick_best(kpis, 'cpa', 'low')
        # 퍼널 KPI 베스트 (수단)
        best_cpm_month, best_cpm = _pick_best(kpis, 'cpm', 'low')
        best_ctr_month, best_ctr = _pick_best(kpis, 'ctr', 'high')
        best_cvr_month, best_cvr = _pick_best(kpis, 'cvr', 'high')

        # 신규 지점 fallback: 정상 운영 월 데이터가 전혀 없으면 5월 부분 데이터를 참고
        is_new_branch = all(k is None for k in kpis.values())
        partial_may = _kpi_for_branch_month(df, branch, CURRENT_MONTH) if is_new_branch else None
        if is_new_branch and partial_may is not None:
            tag = f'{CURRENT_MONTH} (신규·부분)'
            if partial_may.get('conversions') is not None:
                best_conv, best_conv_month = partial_may['conversions'], tag
            if partial_may.get('cpa') is not None:
                best_cpa, best_cpa_month = partial_may['cpa'], tag
            if partial_may.get('cpm') is not None:
                best_cpm, best_cpm_month = partial_may['cpm'], tag
            if partial_may.get('ctr') is not None:
                best_ctr, best_ctr_month = partial_may['ctr'], tag
            if partial_may.get('cvr') is not None:
                best_cvr, best_cvr_month = partial_may['cvr'], tag

        # 보조 통계 (평균·중앙값·최악) - 베스트 월 목표가 비현실적이지 않은지 검증용
        aux_conv = _compute_aux_stats(kpis, 'conversions', 'high')
        aux_cpa = _compute_aux_stats(kpis, 'cpa', 'low')
        aux_cpm = _compute_aux_stats(kpis, 'cpm', 'low')
        aux_ctr = _compute_aux_stats(kpis, 'ctr', 'high')
        aux_cvr = _compute_aux_stats(kpis, 'cvr', 'high')

        targets[branch] = {
            'is_new_branch': is_new_branch,
            'targets': {
                # Primary - 비즈니스 KPI
                'conversions': {
                    'value': None if best_conv is None else int(best_conv),
                    'source_month': best_conv_month,
                    'aux': aux_conv,
                },
                'cpa': {
                    'value': None if best_cpa is None else int(best_cpa),
                    'source_month': best_cpa_month,
                    'aux': aux_cpa,
                },
                # Funnel - 수단
                'cpm': {
                    'value': None if best_cpm is None else int(best_cpm),
                    'source_month': best_cpm_month,
                    'aux': aux_cpm,
                },
                'ctr': {
                    'value': None if best_ctr is None else float(best_ctr),
                    'source_month': best_ctr_month,
                    'aux': aux_ctr,
                },
                'cvr': {
                    'value': None if best_cvr is None else float(best_cvr),
                    'source_month': best_cvr_month,
                    'aux': aux_cvr,
                },
            },
            'monthly_history': kpis,
        }

    # 전체 합산 목표 — Primary(전환/CPA) + Funnel(CPM/CTR/CVR)
    month_totals = {}
    for m in COMPLETE_MONTHS:
        mdf = df[df['month'] == m]
        cost, impr, clk, conv = int(mdf['cost'].sum()), int(mdf['impressions'].sum()), int(mdf['clicks'].sum()), int(mdf['conversions'].sum())
        if impr > 0:
            month_totals[m] = {
                'conversions': conv,
                'cpa': int(cost / conv) if conv > 0 else None,
                'cpm': int(cost / impr * 1000),
                'ctr': round(clk / impr * 100, 2),
                'cvr': round(conv / clk * 100, 2) if clk > 0 else None,
            }
    total_targets = {}
    for metric, direction in [
        ('conversions', 'high'),
        ('cpa', 'low'),
        ('cpm', 'low'),
        ('ctr', 'high'),
        ('cvr', 'high'),
    ]:
        bm, bv = _pick_best(month_totals, metric, direction)
        total_targets[metric] = {'value': bv, 'source_month': bm}

    # 야심 목표 (지점별 베스트월 전환수 합산) - 모든 지점이 본인 베스트를 동시에 달성할 때
    branch_best_conv_sum = sum(
        (targets[b]['targets']['conversions']['value'] or 0)
        for b in VALID_BRANCHES
        if not targets[b]['is_new_branch']
    )
    total_targets['conversions_ambitious'] = {
        'value': branch_best_conv_sum,
        'source_month': '지점별 베스트월 합산',
    }

    return {
        'branches': VALID_BRANCHES,
        'complete_months': COMPLETE_MONTHS,
        'current_month': CURRENT_MONTH,
        'by_branch': targets,
        'overall_targets': total_targets,
        'note': '6월 목표는 정상 운영 월(2~4월) 베스트 기준. 5월은 운영 중단 부분 데이터로 베스트 후보·시점 비교 모두에서 제외.',
    }


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260518/parsed.parquet'
    r = analyze(path)
    print(f"베스트 월 후보: {r['complete_months']} (정상 운영 월)")
    print(f"\n[6월 전체 목표] (Primary)")
    for m in ('conversions', 'cpa'):
        t = r['overall_targets'][m]
        unit = '건' if m == 'conversions' else '원'
        print(f"  {m.upper()}: {t['value']}{unit} (베스트 월: {t['source_month']})")
    amb = r['overall_targets'].get('conversions_ambitious', {})
    print(f"  CONVERSIONS (야심): {amb.get('value')}건 ({amb.get('source_month')})")
    print(f"\n[6월 전체 목표] (Funnel)")
    for m in ('cpm', 'ctr', 'cvr'):
        t = r['overall_targets'][m]
        print(f"  {m.upper()}: {t['value']} (베스트 월: {t['source_month']})")

    print(f"\n[지점별 6월 목표]")
    for b in r['branches']:
        bd = r['by_branch'][b]
        t = bd['targets']
        print(f"\n  {b}")
        print(f"    전환={t['conversions']['value']}건 ({t['conversions']['source_month']})")
        print(f"    CPA 목표={t['cpa']['value']}원 ({t['cpa']['source_month']})")
        print(f"    CPM 목표={t['cpm']['value']}원 ({t['cpm']['source_month']})")
        print(f"    CTR 목표={t['ctr']['value']}% ({t['ctr']['source_month']})")
        print(f"    CVR 목표={t['cvr']['value']}% ({t['cvr']['source_month']})")
