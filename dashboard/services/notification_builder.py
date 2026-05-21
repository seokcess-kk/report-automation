"""텔레그램 일일 알림 메시지 빌더

매일 03:30 알림 메시지 조립:
  - 6월 운영 헤드라인 (정상/주의/긴급 지점 수, 페이스)
  - critical 이상 신호 (상위 5개)
  - high priority 추천 액션 (상위 5개)
  - 체크리스트 진행 요약

Telegram Markdown V1 (legacy) 형식 — 안전한 호환성.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from dashboard.services.data_loader import DataBundle
from dashboard.services.kpi_progress import compute as compute_kpi, summary_status
from dashboard.services.alert_engine import detect_alerts
from dashboard.services.action_recommender import generate as generate_actions
from dashboard.services.checklist_engine import evaluate as evaluate_checklist, summary as checklist_summary


def _escape(text: str) -> str:
    """텔레그램 Markdown V1 특수문자 이스케이프."""
    if text is None:
        return ''
    text = str(text)
    for ch in ('_', '*', '`', '['):
        text = text.replace(ch, '\\' + ch)
    return text


def _won(value) -> str:
    if value is None:
        return '-'
    try:
        return f'{int(value):,}원'
    except (ValueError, TypeError):
        return '-'


def build(bundle: DataBundle, today: Optional[date] = None) -> str:
    """일일 알림 메시지 (Markdown 형식)."""
    today = today or date.today()
    kpi = compute_kpi(bundle, today=today)
    kpi_st = summary_status(kpi)
    alerts = detect_alerts(bundle, today=today)
    recs = generate_actions(bundle)
    checklist = evaluate_checklist(bundle)
    ck_st = checklist_summary(checklist)

    parts = []

    # 헤드라인
    parts.append(f"*📊 6월 TikTok 운영 콘솔 · {today.strftime('%Y-%m-%d')}*")
    parts.append('')
    parts.append(f"_데이터: {_escape(bundle.data_dir.name)}_")
    parts.append('')

    # KPI 진행률
    parts.append(f"*🎯 KPI 진행률*")
    parts.append(f"전환: *{kpi.conversions_actual} / {kpi.target_base}건* (페이스 {kpi.pace_pct}%, D-{kpi.days_remaining})")
    parts.append(f"CPA 3일 MA: {_won(kpi.cpa_3day_avg)} (가드레일 {_won(kpi.target_cpa)} · {'✅' if kpi.cpa_within_guardrail else '⚠'})")
    parts.append(f"지점: 정상 {kpi_st['normal']} · 주의 {kpi_st['warn']} · 긴급 {kpi_st['critical']}")
    parts.append('')

    # Critical 신호 (최대 5개, 보류된 신호 제외)
    critical_alerts = [a for a in alerts if a.level == 'critical' and not a.suppressed]
    if critical_alerts:
        parts.append(f"*🔴 긴급 신호 ({len(critical_alerts)}건)*")
        for a in critical_alerts[:5]:
            parts.append(f"• {_escape(a.target_name)}: {_escape(a.message)}")
        if len(critical_alerts) > 5:
            parts.append(f"_… 외 {len(critical_alerts) - 5}건_")
        parts.append('')

    # Warning 신호 요약 (개수만)
    warning_alerts = [a for a in alerts if a.level == 'warning' and not a.suppressed]
    if warning_alerts:
        parts.append(f"*🟡 주의 신호: {len(warning_alerts)}건*")
        for a in warning_alerts[:3]:
            parts.append(f"• {_escape(a.target_name)}: {_escape(a.message)}")
        if len(warning_alerts) > 3:
            parts.append(f"_… 외 {len(warning_alerts) - 3}건 (상세는 콘솔)_")
        parts.append('')

    # 추천 액션 — high priority만
    high_recs = []
    for cat_key, label in [
        ('budget_increase', '💰 예산 증액'),
        ('budget_decrease', '💰 예산 감액'),
        ('ad_off', '🎬 광고 OFF'),
        ('setting', '⚙️ 세팅 확인'),
    ]:
        for r in recs.get(cat_key, []):
            if r.priority == 'high':
                high_recs.append((label, r))
    if high_recs:
        parts.append(f"*⚡ 오늘 우선 액션 ({len(high_recs)}건)*")
        for label, r in high_recs[:5]:
            parts.append(f"• {label} — {_escape(r.title)}")
            parts.append(f"  _{_escape(r.rationale[:120])}_")
        if len(high_recs) > 5:
            parts.append(f"_… 외 {len(high_recs) - 5}건_")
        parts.append('')

    # 체크리스트 진행
    total = sum(ck_st.values())
    parts.append(f"*✅ 6월 체크리스트*: 완료 {ck_st.get('completed', 0)} · 진행 {ck_st.get('in_progress', 0)} · 보류 {ck_st.get('not_started', 0)} / 총 {total}건")
    parts.append('')

    # 푸터
    parts.append(f"_콘솔: http://localhost:5050_")

    return '\n'.join(parts)


def build_concise(bundle: DataBundle, today: Optional[date] = None) -> str:
    """짧은 1줄 요약 (Slack/푸시 노티 등 짧은 채널용)."""
    today = today or date.today()
    kpi = compute_kpi(bundle, today=today)
    alerts = detect_alerts(bundle, today=today)
    critical = sum(1 for a in alerts if a.level == 'critical' and not a.suppressed)
    return (
        f"[6월 운영 {today.strftime('%m-%d')}] "
        f"전환 {kpi.conversions_actual}/{kpi.target_base} ({kpi.pace_pct}%) · "
        f"CPA {_won(kpi.cpa_3day_avg)} · "
        f"긴급 {critical}건"
    )


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    from dashboard.services.data_loader import load_bundle
    b = load_bundle()
    print('=== 풀 메시지 ===')
    print(build(b, today=date(2026, 5, 19)))
    print()
    print('=== 짧은 요약 ===')
    print(build_concise(b, today=date(2026, 5, 19)))
