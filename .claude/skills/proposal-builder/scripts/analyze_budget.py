"""비용·예산 분석 — 실집행 대비 성과 + 6월 목표 달성 예산 역산

설계 (codex Round 4 합의):
  · MONTHLY_BUDGET(계획 예산) 사용 안 함 — 실집행 데이터 중심
  · 정상월 2~4월을 베이스라인으로 평균 월간 집행 산정
  · 5월은 운영 중단 부분 데이터로 평균 산정에서 제외, 추이 차트에서만 표시

산출:
  · monthly_total: 월별 총비용·전환·100만원당 전환 (2~5월)
  · by_branch:
      - 정상월 평균 월간 집행
      - 100만원당 전환수
      - 비용 비중 vs 전환 비중
      - 효율 점수 (전환 비중 / 비용 비중)
      - 효율 등급 (good/avg/bad)
  · june_scenarios: 6월 예산 시나리오 3종 (낙관/권장/보수)
  · june_recommended_by_branch: 지점별 6월 권장 예산
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES

NORMAL_MONTHS = ['2026-02', '2026-03', '2026-04']
PARTIAL_MONTH = '2026-05'

# 효율 점수 임계값 (전환 비중 / 비용 비중)
EFF_GOOD = 1.15   # ≥ +15% → 우수
EFF_BAD = 0.85    # ≤ -15% → 부진

# 6월 권장 예산 효율 가중 (codex 권장)
EFF_WEIGHT = {
    'good': 1.10,    # 우수 → +10%
    'average': 1.00, # 평균 → 유지
    'bad': 0.90,     # 부진 → -10% (CVR 회복 전)
    'new': 1.00,     # 신규 → 계획 유지
}


def analyze(parsed_path: str) -> dict:
    df = pd.read_parquet(parsed_path)
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.strftime('%Y-%m')
    df = df[df['지점'].isin(VALID_BRANCHES)].copy()

    months_all = sorted(df['month'].unique())
    df_normal = df[df['month'].isin(NORMAL_MONTHS)]
    n_normal = len(NORMAL_MONTHS)

    # ===== 월별 총비용 (전 기간) =====
    monthly_total = {}
    for m in months_all:
        sub = df[df['month'] == m]
        cost = int(sub['cost'].sum())
        conv = int(sub['conversions'].sum())
        days = int(sub['date'].dt.date.nunique())
        monthly_total[m] = {
            'cost': cost,
            'conversions': conv,
            'days_active': days,
            'is_partial': m == PARTIAL_MONTH,
            'cost_per_day': round(cost / days) if days > 0 else None,
            'conv_per_million': round(conv / (cost / 1_000_000), 1) if cost > 0 else None,
            'cpa': int(cost / conv) if conv > 0 else None,
        }

    # ===== 전 지점 정상월 평균 =====
    normal_total_cost = int(df_normal['cost'].sum())
    normal_total_conv = int(df_normal['conversions'].sum())
    avg_monthly_cost = round(normal_total_cost / n_normal)
    avg_monthly_conv = round(normal_total_conv / n_normal)
    avg_cpa = int(normal_total_cost / normal_total_conv) if normal_total_conv > 0 else None
    avg_conv_per_million = round(normal_total_conv / (normal_total_cost / 1_000_000), 1) if normal_total_cost > 0 else None

    # ===== 지점별 분석 =====
    by_branch = {}
    for branch in VALID_BRANCHES:
        bdf_normal = df_normal[df_normal['지점'] == branch]
        bdf_partial = df[(df['month'] == PARTIAL_MONTH) & (df['지점'] == branch)]

        normal_cost = int(bdf_normal['cost'].sum())
        normal_conv = int(bdf_normal['conversions'].sum())
        has_normal = len(bdf_normal) > 0
        # 평균 월간 집행 = 정상월 합계 / 3 (운영 안 한 월도 포함해 평균을 낮춤)
        avg_branch_cost = round(normal_cost / n_normal) if has_normal else 0
        avg_branch_conv = round(normal_conv / n_normal) if has_normal else 0
        branch_cpa = int(normal_cost / normal_conv) if normal_conv > 0 else None
        conv_per_million = round(normal_conv / (normal_cost / 1_000_000), 1) if normal_cost > 0 else None

        # 비용/전환 비중 (전 지점 정상월 누적 기준)
        cost_share = round(normal_cost / normal_total_cost * 100, 1) if normal_total_cost else 0
        conv_share = round(normal_conv / normal_total_conv * 100, 1) if normal_total_conv else 0
        # 효율 점수 = 전환 비중 / 비용 비중 (1.0 평균, >1 비용 대비 전환 잘 나옴)
        efficiency = round(conv_share / cost_share, 2) if cost_share > 0 else None

        # 5월 부분
        partial_cost = int(bdf_partial['cost'].sum()) if len(bdf_partial) else 0
        partial_conv = int(bdf_partial['conversions'].sum()) if len(bdf_partial) else 0
        is_new = not has_normal and partial_cost > 0
        no_data = not has_normal and partial_cost == 0

        # 효율 등급
        if is_new:
            grade = 'new'
            grade_label = '신규 지점 (5월 부분)'
        elif no_data:
            grade = 'na'
            grade_label = '데이터 없음'
        elif efficiency is None:
            grade = 'na'
            grade_label = '평가 불가'
        elif efficiency >= EFF_GOOD:
            grade = 'good'
            grade_label = f'우수 (전환 {conv_share}% > 비용 {cost_share}%)'
        elif efficiency <= EFF_BAD:
            grade = 'bad'
            grade_label = f'부진 (전환 {conv_share}% < 비용 {cost_share}%)'
        else:
            grade = 'average'
            grade_label = '평균 수준'

        by_branch[branch] = {
            'is_new_branch': is_new,
            'no_data': no_data,
            'normal_total_cost': normal_cost,
            'avg_monthly_cost': avg_branch_cost,
            'avg_monthly_conv': avg_branch_conv,
            'branch_cpa': branch_cpa,
            'conv_per_million': conv_per_million,
            'cost_share_pct': cost_share,
            'conv_share_pct': conv_share,
            'efficiency_ratio': efficiency,
            'efficiency_grade': grade,
            'efficiency_label': grade_label,
            'partial_may_cost': partial_cost,
            'partial_may_conv': partial_conv,
        }

    # ===== 6월 시나리오 — codex 권장 (B+D 조합) =====
    # june_targets에서 가져온 값을 사용해야 정확하지만, 이 모듈은 단독 분석이라
    # parsed로부터 직접 베스트월 값을 산정. 외부 의존 없이 자체완결.
    def _branch_best_value(branch: str, metric: str, direction: str):
        """direction='high'면 최대, 'low'면 최소."""
        vals = []
        for m in NORMAL_MONTHS:
            sub = df_normal[(df_normal['지점'] == branch) & (df_normal['month'] == m)]
            if len(sub) == 0:
                continue
            cost = int(sub['cost'].sum())
            impr = int(sub['impressions'].sum())
            conv = int(sub['conversions'].sum())
            if metric == 'cpa':
                if conv > 0:
                    vals.append(int(cost / conv))
            elif metric == 'conversions':
                vals.append(conv)
        if not vals:
            return None
        return min(vals) if direction == 'low' else max(vals)

    # 시나리오용 지점별 base/stretch + CPA 베스트
    branch_scenarios = {}
    for branch in VALID_BRANCHES:
        bd = by_branch[branch]
        # base 전환 = 정상월 평균 전환 (전 지점 762건 base에 정합)
        base_conv = bd['avg_monthly_conv']
        # stretch 전환 = 베스트월 전환
        stretch_conv = _branch_best_value(branch, 'conversions', 'high') or base_conv
        # CPA 베스트
        cpa_best = _branch_best_value(branch, 'cpa', 'low') or bd['branch_cpa']
        # CPA 평균 = 지점 누적 CPA
        cpa_avg = bd['branch_cpa']
        branch_scenarios[branch] = {
            'base_conv': base_conv,
            'stretch_conv': stretch_conv,
            'cpa_best': cpa_best,
            'cpa_avg': cpa_avg,
        }

    # 전 지점 합산 시나리오
    # 낙관 = Σ(stretch × CPA 베스트)
    optimistic = sum(
        (s['stretch_conv'] * s['cpa_best']) if (s['stretch_conv'] and s['cpa_best']) else 0
        for s in branch_scenarios.values()
    )
    # 보수 = Σ(base × CPA 평균)
    conservative = sum(
        (s['base_conv'] * s['cpa_avg']) if (s['base_conv'] and s['cpa_avg']) else 0
        for s in branch_scenarios.values()
    )

    # 권장 = 정상월 평균 집행 × 지점별 효율 가중 (codex 권장)
    recommended_by_branch = {}
    for branch in VALID_BRANCHES:
        bd = by_branch[branch]
        grade = bd['efficiency_grade']
        weight = EFF_WEIGHT.get(grade, 1.0)
        base = bd['avg_monthly_cost']
        if bd['is_new_branch']:
            # 신규 지점은 5월 부분 운영 그대로 (없으면 0)
            rec = bd['partial_may_cost'] if bd['partial_may_cost'] else 0
            reason = '신규 학습 안정화 - 5월 부분 운영 수준 유지'
        elif bd['no_data']:
            rec = 0
            reason = '데이터 없음 - 신규 진입 시 별도 계획 필요'
        else:
            rec = round(base * weight)
            sign = '+' if weight > 1 else ('-' if weight < 1 else '±')
            pct = int(abs(weight - 1) * 100)
            label = {'good': '효율 우수', 'average': '평균 수준', 'bad': '효율 부진'}[grade]
            reason = f'{label} → {sign}{pct}%'
        delta = rec - base if base else 0
        delta_pct = round(delta / base * 100, 1) if base else None
        recommended_by_branch[branch] = {
            'recommended_june_budget': rec,
            'delta_amount': delta,
            'delta_pct': delta_pct,
            'reason': reason,
            'base_avg_monthly_cost': base,
        }

    recommended_total = sum(r['recommended_june_budget'] for r in recommended_by_branch.values())

    # 시나리오 표시값
    scenarios = {
        'optimistic': {
            'label': '낙관 (Stretch 전환 × 베스트 CPA)',
            'total_budget': optimistic,
            'expected_conv': sum(s['stretch_conv'] or 0 for s in branch_scenarios.values()),
            'assumption': '모든 지점이 본인 베스트월 전환·CPA를 동시 달성',
            'risk': '베스트월은 서로 다른 월·서로 다른 운영 조건에서 달성된 값이라 동시 달성 가능성은 제한적',
        },
        'recommended': {
            'label': '권장 (정상월 평균 집행 × 효율 가중)',
            'total_budget': recommended_total,
            'expected_conv': '시나리오별 차등',
            'assumption': '실집행 베이스라인 유지하며 효율 우수 지점 증액·부진 지점 축소',
            'risk': 'CVR 회복이 더디면 부진 지점 축소 폭이 부족할 수 있음',
        },
        'conservative': {
            'label': '보수 (Base 전환 × CPA 평균)',
            'total_budget': conservative,
            'expected_conv': sum(s['base_conv'] or 0 for s in branch_scenarios.values()),
            'assumption': 'CPA가 정상월 평균 수준에 머무는 시나리오',
            'risk': '지점별 효율 격차 무시. 비효율 지점에 베이스 예산 그대로 투입',
        },
    }

    return {
        'baseline': {
            'normal_months': NORMAL_MONTHS,
            'partial_month': PARTIAL_MONTH,
            'avg_monthly_cost': avg_monthly_cost,
            'avg_monthly_conv': avg_monthly_conv,
            'avg_cpa': avg_cpa,
            'avg_conv_per_million': avg_conv_per_million,
            'normal_total_cost': normal_total_cost,
            'normal_total_conv': normal_total_conv,
        },
        'monthly_total': monthly_total,
        'by_branch': by_branch,
        'june_scenarios': scenarios,
        'june_recommended_by_branch': recommended_by_branch,
        'june_recommended_total': recommended_total,
        'efficiency_thresholds': {'good': EFF_GOOD, 'bad': EFF_BAD},
        'note': (
            '평균 월간 집행 = 정상월 2~4월 합계 ÷ 3. 5월은 부분 데이터로 평균 산정에서 제외. '
            '효율 점수 = 지점 전환 비중 ÷ 비용 비중. 비용 비중 대비 전환 비중이 클수록 예산 효율 우수. '
            '6월 권장 예산은 정상월 평균 × 효율 가중 (우수 +10% / 평균 유지 / 부진 -10%).'
        ),
    }


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260518/parsed.parquet'
    r = analyze(path)
    b = r['baseline']
    print(f"[전 지점 합산 - 정상월 평균]")
    print(f"  평균 월간 집행: {b['avg_monthly_cost']:,}원")
    print(f"  평균 월간 전환: {b['avg_monthly_conv']}건")
    print(f"  평균 CPA: {b['avg_cpa']:,}원")
    print(f"  100만원당 전환: {b['avg_conv_per_million']}건")

    print(f"\n[월별 총비용]")
    for m, d in r['monthly_total'].items():
        partial = ' (부분)' if d['is_partial'] else ''
        print(f"  {m}: {d['cost']:,}원 · 전환 {d['conversions']}건 · 100만원당 {d['conv_per_million']}건 · CPA {d['cpa']:,}원{partial}")

    print(f"\n[지점별 효율]")
    for branch in r['by_branch']:
        bd = r['by_branch'][branch]
        if bd['no_data']:
            print(f"  {branch}: 데이터 없음")
            continue
        if bd['is_new_branch']:
            print(f"  {branch}: 신규 (5월 부분 {bd['partial_may_cost']:,}원, {bd['partial_may_conv']}건)")
            continue
        print(f"  {branch}: 평균 {bd['avg_monthly_cost']:,}원/월 · 100만원당 {bd['conv_per_million']}건")
        print(f"    비용 {bd['cost_share_pct']}% vs 전환 {bd['conv_share_pct']}% · 효율 {bd['efficiency_ratio']} · {bd['efficiency_label']}")

    print(f"\n[6월 시나리오]")
    for k, s in r['june_scenarios'].items():
        print(f"  {s['label']}: {s['total_budget']:,}원 (전환 {s.get('expected_conv')})")

    print(f"\n[6월 지점별 권장 예산]")
    for branch in r['june_recommended_by_branch']:
        rec = r['june_recommended_by_branch'][branch]
        sign = '+' if rec['delta_pct'] and rec['delta_pct'] > 0 else ''
        print(f"  {branch}: {rec['recommended_june_budget']:,}원 ({sign}{rec['delta_pct']}% vs 정상월 평균) - {rec['reason']}")
    print(f"  ----")
    print(f"  합계: {r['june_recommended_total']:,}원")
