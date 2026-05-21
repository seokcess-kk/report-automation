"""KPI 진행률 계산 — 6월 762/822건 목표 대비 누적·페이스·예상 도달

홈 화면 3.1 "오늘의 결론" 영역의 핵심 지표 제공.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Optional

import pandas as pd

from dashboard.services.data_loader import DataBundle


JUNE_START = date(2026, 6, 1)
JUNE_END = date(2026, 6, 30)
JUNE_DAYS_TOTAL = (JUNE_END - JUNE_START).days + 1  # 30


@dataclass
class KpiProgress:
    today: str
    days_elapsed: int          # 6월 시작 기준 경과일 (오늘 포함)
    days_remaining: int
    progress_pct: float        # 경과일 / 30일

    target_base: int           # 762
    target_stretch: int        # 822
    target_cpa: int            # 27,278

    conversions_actual: int    # 6월 누적 실적
    pace_pct: float            # 실적 / (target * progress_pct)
    projected_total: float     # 현재 페이스 유지 시 6월 말 예상 전환수

    cpa_today: Optional[int]
    cpa_3day_avg: Optional[int]
    cpa_within_guardrail: bool

    branches: dict             # 지점별 상태


def _safe_date_filter(parsed: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    if parsed.empty:
        return parsed
    p = parsed.copy()
    p['date'] = pd.to_datetime(p['date'])
    return p[(p['date'].dt.date >= start) & (p['date'].dt.date <= end)]


def _branch_kpi(df: pd.DataFrame, branch: str, target_conv: int, target_cpa: int) -> dict:
    bdf = df[df['지점'] == branch]
    cost = int(bdf['cost'].sum())
    conv = int(bdf['conversions'].sum())
    cpa = round(cost / conv) if conv else None
    return {
        'branch': branch,
        'conversions': conv,
        'cost': cost,
        'cpa': cpa,
        'target_conversions': target_conv,
        'conv_pct': round(conv / target_conv * 100, 1) if target_conv else None,
        'within_guardrail': (cpa is not None and cpa <= target_cpa * 1.10),
    }


def compute(bundle: DataBundle, today: Optional[date] = None) -> KpiProgress:
    today = today or date.today()
    # 6월 컨텍스트 — 6월 이전이면 6월 1일 기준으로 0 시작
    if today < JUNE_START:
        days_elapsed = 0
        days_remaining = JUNE_DAYS_TOTAL
    elif today > JUNE_END:
        days_elapsed = JUNE_DAYS_TOTAL
        days_remaining = 0
    else:
        days_elapsed = (today - JUNE_START).days + 1
        days_remaining = JUNE_DAYS_TOTAL - days_elapsed

    progress_pct = days_elapsed / JUNE_DAYS_TOTAL if JUNE_DAYS_TOTAL else 0

    meta = bundle.operation_rules.get('meta', {})
    target_base = int(meta.get('monthly_target_conv_base', 762))
    target_stretch = int(meta.get('monthly_target_conv_stretch', 822))
    target_cpa = int(meta.get('proposal_target_cpa', 27278))

    # 6월 실적 — parsed.parquet 기준 (분석 디렉토리가 5월 부분월이면 0일 가능)
    june_df = _safe_date_filter(bundle.parsed, JUNE_START, JUNE_END)
    conv_actual = int(june_df['conversions'].sum()) if not june_df.empty else 0

    # 페이스 — 균등 페이스 가정
    expected_so_far = target_base * progress_pct
    pace_pct = round(conv_actual / expected_so_far * 100, 1) if expected_so_far else 0.0
    projected_total = round(conv_actual / progress_pct, 1) if progress_pct else 0.0

    # CPA 추적
    cpa_today, cpa_3day_avg, cpa_within_guardrail = None, None, True
    if not june_df.empty:
        june_df['_d'] = june_df['date'].dt.date
        by_day = june_df.groupby('_d').agg(cost=('cost', 'sum'), conv=('conversions', 'sum'))
        by_day['cpa'] = by_day.apply(lambda r: round(r['cost'] / r['conv']) if r['conv'] else None, axis=1)
        days_with_data = by_day.dropna(subset=['cpa']).sort_index()
        if not days_with_data.empty:
            cpa_today = int(days_with_data.iloc[-1]['cpa'])
            tail = days_with_data.tail(3)
            if not tail.empty:
                cpa_3day_avg = round(tail['cpa'].mean())
            cpa_within_guardrail = (cpa_3day_avg or 0) <= target_cpa * 1.10

    # 지점별
    common_mod = __import__('common', fromlist=['MONTHLY_TARGET_CONV_BY_BRANCH', 'VALID_BRANCHES'])
    target_by_branch = common_mod.MONTHLY_TARGET_CONV_BY_BRANCH
    valid_branches = common_mod.VALID_BRANCHES

    branches = {}
    for b in valid_branches:
        branches[b] = _branch_kpi(june_df, b, target_by_branch.get(b, 0), target_cpa)

    return KpiProgress(
        today=today.strftime('%Y-%m-%d'),
        days_elapsed=days_elapsed,
        days_remaining=days_remaining,
        progress_pct=round(progress_pct * 100, 1),
        target_base=target_base,
        target_stretch=target_stretch,
        target_cpa=target_cpa,
        conversions_actual=conv_actual,
        pace_pct=pace_pct,
        projected_total=projected_total,
        cpa_today=cpa_today,
        cpa_3day_avg=cpa_3day_avg,
        cpa_within_guardrail=cpa_within_guardrail,
        branches=branches,
    )


def summary_status(kpi: KpiProgress) -> dict:
    """홈 3.1 '오늘의 결론' 헤드용 요약 — 정상/주의/긴급 지점 수."""
    normal, warn, critical = 0, 0, 0
    for b, info in kpi.branches.items():
        cpa = info.get('cpa')
        conv_pct = info.get('conv_pct') or 0
        if cpa is None:
            normal += 1
            continue
        if not info.get('within_guardrail') or conv_pct < 80:
            critical += 1
        elif conv_pct < 95:
            warn += 1
        else:
            normal += 1
    return {
        'normal': normal,
        'warn': warn,
        'critical': critical,
        'pace_label': _pace_label(kpi.pace_pct),
    }


def _pace_label(pace_pct: float) -> str:
    if pace_pct >= 95:
        return 'on_track'
    if pace_pct >= 85:
        return 'warn'
    return 'critical'


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    from dashboard.services.data_loader import load_bundle
    bundle = load_bundle()
    kpi = compute(bundle, today=date(2026, 6, 15))   # 가상 6/15 — 부분월 검증용
    print(f'[today] {kpi.today}')
    print(f'[6월 경과] {kpi.days_elapsed}/{JUNE_DAYS_TOTAL}일 (남은 {kpi.days_remaining}일)')
    print(f'[목표] {kpi.target_base} (상향 {kpi.target_stretch}) · 가드레일 CPA {kpi.target_cpa:,}원')
    print(f'[누적] 전환 {kpi.conversions_actual} · 페이스 {kpi.pace_pct}% · 예상 {kpi.projected_total}건')
    print(f'[CPA] 오늘 {kpi.cpa_today} · 3일 MA {kpi.cpa_3day_avg} · 가드레일 통과 {kpi.cpa_within_guardrail}')
    print()
    print('[지점별]')
    for b, info in kpi.branches.items():
        print(f'  {b}: 전환 {info["conversions"]}/{info["target_conversions"]} ({info["conv_pct"]}%) · CPA {info["cpa"]} · 가드 {info["within_guardrail"]}')
    print()
    print(f'[summary] {summary_status(kpi)}')
