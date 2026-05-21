"""이상 신호 감지 — 3가지 기준 병행 (전일비 + 3일 MA + 6월 목표 페이스)

홈 3.3 영역. alert_rules.yaml의 룰을 데이터에 적용.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from dashboard.services.data_loader import DataBundle
from dashboard.services.kpi_progress import compute as compute_kpi, JUNE_START, JUNE_END


@dataclass
class Alert:
    level: str            # critical | warning | recovery
    icon: str
    color: str
    rule_id: str
    target_type: str      # global | branch | adgroup | creative
    target_name: str      # 지점명, 광고그룹명 등
    message: str
    metric_value: Optional[float] = None
    linked_action: Optional[str] = None
    linked_checklist: Optional[str] = None
    suppressed: bool = False   # 노이즈 필터에 의한 보류
    suppressed_reason: Optional[str] = None


def _branch_daily_series(parsed: pd.DataFrame, branch: str) -> pd.DataFrame:
    """지점별 일별 KPI 시계열 (cost, clicks, conversions, cpa, cvr, ctr)."""
    df = parsed[parsed['지점'] == branch].copy()
    df['date'] = pd.to_datetime(df['date']).dt.date
    daily = df.groupby('date').agg(
        cost=('cost', 'sum'),
        impressions=('impressions', 'sum'),
        clicks=('clicks', 'sum'),
        conversions=('conversions', 'sum'),
    ).reset_index().sort_values('date')
    daily['cpa'] = daily.apply(lambda r: r['cost'] / r['conversions'] if r['conversions'] else None, axis=1)
    daily['cvr'] = daily.apply(lambda r: r['conversions'] / r['clicks'] * 100 if r['clicks'] else None, axis=1)
    daily['ctr'] = daily.apply(lambda r: r['clicks'] / r['impressions'] * 100 if r['impressions'] else None, axis=1)
    return daily


def _moving_avg(daily: pd.DataFrame, metric: str, today: date, window: int) -> Optional[float]:
    """today를 포함한 직전 N일(있는 만큼) 이동평균."""
    if daily.empty:
        return None
    recent = daily[daily['date'] <= today].tail(window)
    values = recent[metric].dropna()
    if values.empty:
        return None
    return float(values.mean())


def _day_over_day(daily: pd.DataFrame, metric: str, today: date) -> tuple[Optional[float], Optional[float]]:
    """오늘·전일 값 반환. 전일 데이터 없으면 (None, None)."""
    if daily.empty:
        return None, None
    today_row = daily[daily['date'] == today]
    yesterday_row = daily[daily['date'] == today - timedelta(days=1)]
    if today_row.empty or yesterday_row.empty:
        return None, None
    return float(today_row.iloc[0][metric]) if pd.notna(today_row.iloc[0][metric]) else None, \
           float(yesterday_row.iloc[0][metric]) if pd.notna(yesterday_row.iloc[0][metric]) else None


def _noise_check(clicks_today: int, days_active: int, filt: dict) -> tuple[bool, str]:
    """노이즈 필터 통과 여부 + 사유."""
    if clicks_today < filt.get('min_clicks_for_signal', 30):
        return False, f'클릭 {clicks_today} < 30 (표본 부족)'
    if days_active < filt.get('min_days_active', 7):
        return False, f'집행 {days_active}일 < 7 (학습 기간)'
    return True, ''


def detect_alerts(bundle: DataBundle, today: Optional[date] = None) -> list[Alert]:
    """전체 이상 신호 탐지. 우선순위 정렬해서 반환."""
    today = today or date.today()
    rules = bundle.alert_rules or {}
    meta_noise = (rules.get('meta') or {}).get('noise_filter', {})

    alerts: list[Alert] = []
    alerts.extend(_check_target_pace(bundle, today, rules))
    alerts.extend(_check_branches(bundle, today, rules, meta_noise))
    alerts.extend(_check_operation_specific(bundle, today, rules))

    # 우선순위 정렬: critical > warning > recovery, 동일 level 내 target_type 우선순위
    level_order = {'critical': 0, 'warning': 1, 'recovery': 2}
    type_order = {'global': 0, 'branch': 1, 'adgroup': 2, 'creative': 3}
    alerts.sort(key=lambda a: (level_order.get(a.level, 9), type_order.get(a.target_type, 9)))
    return alerts


def _check_target_pace(bundle: DataBundle, today: date, rules: dict) -> list[Alert]:
    """7.3 페이스 신호 — 전역 1회만."""
    pace_rules = rules.get('target_pace', [])
    if not pace_rules:
        return []
    kpi = compute_kpi(bundle, today)
    out = []
    for rule in pace_rules:
        rid = rule.get('id', '')
        if 'pace_low' in rid and kpi.pace_pct < 85 and kpi.days_elapsed > 0:
            out.append(Alert(
                level='critical',
                icon='🔴', color='#ef4444',
                rule_id=rid, target_type='global', target_name='6월 전환 페이스',
                message=f'전환 페이스 목표 대비 {kpi.pace_pct}% — 액션 필요',
                metric_value=kpi.pace_pct,
                linked_action=rule.get('linked_action'),
            ))
        elif 'pace_warning' in rid and 85 <= kpi.pace_pct < 95 and kpi.days_elapsed > 0:
            out.append(Alert(
                level='warning',
                icon='🟡', color='#f59e0b',
                rule_id=rid, target_type='global', target_name='6월 전환 페이스',
                message=f'전환 페이스 {kpi.pace_pct}% — 주의',
                metric_value=kpi.pace_pct,
            ))
    return out


def _check_branches(bundle: DataBundle, today: date, rules: dict, noise_filter: dict) -> list[Alert]:
    """지점별 7.1(전일비) + 7.2(3일 MA) 신호."""
    if bundle.parsed.empty:
        return []
    out = []
    common_mod = __import__('common', fromlist=['VALID_BRANCHES'])
    branches = common_mod.VALID_BRANCHES

    meta_op = (bundle.operation_rules.get('meta') or {})
    target_cpa = meta_op.get('proposal_target_cpa', 27278)
    target_cvr = meta_op.get('proposal_target_cvr_pct', 5.0)

    dod_rules = {r['id']: r for r in rules.get('day_over_day', [])}
    ma_rules = {r['id']: r for r in rules.get('three_day_moving_average', [])}

    for b in branches:
        daily = _branch_daily_series(bundle.parsed, b)
        if daily.empty:
            continue
        clicks_today = int(daily[daily['date'] == today]['clicks'].sum()) if not daily[daily['date'] == today].empty else 0
        days_active = int(daily[daily['conversions'] > 0]['date'].nunique())
        passed, suppress_reason = _noise_check(clicks_today, days_active, noise_filter)

        # 7.2 3일 MA — critical 가능
        cpa_3 = _moving_avg(daily, 'cpa', today, 3)
        if cpa_3 and cpa_3 > target_cpa * 1.20:
            out.append(Alert(
                level='critical',
                icon='🔴', color='#ef4444',
                rule_id='cpa_guardrail_breach',
                target_type='branch', target_name=b,
                message=f'{b}: CPA 3일 MA {int(cpa_3):,}원 (가드레일 +20% 초과)',
                metric_value=round((cpa_3 / target_cpa - 1) * 100, 1),
                linked_action=ma_rules.get('cpa_guardrail_breach', {}).get('linked_action'),
                suppressed=not passed, suppressed_reason=suppress_reason if not passed else None,
            ))

        cvr_3 = _moving_avg(daily, 'cvr', today, 3)
        if cvr_3 is not None and cvr_3 < target_cvr * 0.70:
            out.append(Alert(
                level='critical',
                icon='🔴', color='#ef4444',
                rule_id='cvr_persistent_low',
                target_type='branch', target_name=b,
                message=f'{b}: CVR 3일 MA {cvr_3:.2f}% (목표 {target_cvr}% 대비 70% 미달)',
                metric_value=round(cvr_3, 2),
                linked_action=ma_rules.get('cvr_persistent_low', {}).get('linked_action'),
                suppressed=not passed, suppressed_reason=suppress_reason if not passed else None,
            ))

        # 7.1 전일비 — warning
        cpa_today_v, cpa_yest = _day_over_day(daily, 'cpa', today)
        if cpa_today_v and cpa_yest and cpa_today_v > cpa_yest * 1.30:
            delta = round((cpa_today_v / cpa_yest - 1) * 100, 1)
            out.append(Alert(
                level='warning',
                icon='🟡', color='#f59e0b',
                rule_id='cpa_spike',
                target_type='branch', target_name=b,
                message=f'{b}: CPA 전일 대비 +{delta}% 상승',
                metric_value=delta,
                suppressed=not passed, suppressed_reason=suppress_reason if not passed else None,
            ))

        cvr_today_v, cvr_yest = _day_over_day(daily, 'cvr', today)
        if cvr_today_v and cvr_yest and cvr_today_v < cvr_yest * 0.70:
            delta = round((cvr_today_v / cvr_yest - 1) * 100, 1)
            out.append(Alert(
                level='warning',
                icon='🟡', color='#f59e0b',
                rule_id='cvr_drop',
                target_type='branch', target_name=b,
                message=f'{b}: CVR 전일 대비 {delta}% 하락',
                metric_value=delta,
                suppressed=not passed, suppressed_reason=suppress_reason if not passed else None,
            ))

    return out


def _check_operation_specific(bundle: DataBundle, today: date, rules: dict) -> list[Alert]:
    """7.5 — 천안 지역 누수·25-34 수원 등 제안서 연계 신호."""
    out = []
    op_rules = {r['id']: r for r in rules.get('operation_specific', [])}

    # 천안 지역 누수
    geo = (bundle.proposal or {}).get('geo_leakage') or {}
    if geo.get('available'):
        cheonan = (geo.get('by_branch') or {}).get('천안')
        if cheonan:
            leak = cheonan.get('leakage_pct', 0)
            if leak >= 15:
                rule = op_rules.get('cheonan_geo_leakage_active', {})
                out.append(Alert(
                    level='warning',
                    icon='🟡', color='#f59e0b',
                    rule_id='cheonan_geo_leakage_active',
                    target_type='branch', target_name='천안',
                    message=f'천안 지역 누수 {leak}% (15% 초과) — 광고 그룹 지역 설정 확인',
                    metric_value=leak,
                    linked_checklist=rule.get('linked_checklist'),
                ))

    # 성별 누수 (남성 노출)
    th = (bundle.proposal or {}).get('targeting_health') or {}
    if th.get('available'):
        gs = th.get('gender_summary', {})
        male_pct = gs.get('male_impr_pct') or 0
        if male_pct > 0.5:
            rule = op_rules.get('age_25_34_male_leak', {})
            out.append(Alert(
                level='critical',
                icon='🔴', color='#ef4444',
                rule_id='age_25_34_male_leak',
                target_type='global', target_name='성별 타겟팅',
                message=f'남성 노출 {male_pct}% 감지 — 성별 타겟팅 점검 필요',
                metric_value=male_pct,
                linked_checklist=rule.get('linked_checklist'),
            ))

    return out


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    from dashboard.services.data_loader import load_bundle
    bundle = load_bundle()
    alerts = detect_alerts(bundle, today=date(2026, 5, 19))  # 5월 마지막 운영일 기준
    print(f'[총 신호] {len(alerts)}개')
    for a in alerts:
        suffix = f' [SUPPRESSED: {a.suppressed_reason}]' if a.suppressed else ''
        print(f'  {a.icon} [{a.level}] {a.target_name}: {a.message}{suffix}')
