"""체크리스트 엔진 — june_checklist.yaml 항목 + 데이터 기반 status 자동 평가

status:
  completed     ✓  success_metric의 target 도달
  in_progress   🔄 운영 시작 흔적 감지, target 미도달
  partial       ⚠️  운영 시작했으나 일부 기준만 충족
  not_started   ☐  운영 흔적 없음

manual_override: true 항목은 운영자 수동 토글 → checklist_state.json
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

from dashboard.services.data_loader import DataBundle


@dataclass
class ChecklistItem:
    id: str
    title: str
    owner: str
    week: str
    related_section: str
    status: str               # completed | in_progress | partial | not_started
    status_icon: str
    note: Optional[str] = None
    manual_override: bool = False
    manually_checked: bool = False
    success_metric_value: Optional[float] = None


_STATUS_ICON = {
    'completed': '✓',
    'in_progress': '🔄',
    'partial': '⚠',
    'not_started': '☐',
}


def evaluate(bundle: DataBundle) -> list[ChecklistItem]:
    items_raw = (bundle.checklist.get('checklist') or [])
    state = bundle.checklist_state or {}
    out: list[ChecklistItem] = []
    for raw in items_raw:
        cid = raw['id']
        status, note, metric_val = _evaluate_rule(raw.get('status_rule'), bundle)
        manual = bool(raw.get('manual_override'))
        user_state = state.get(cid) or {}
        manually_checked = bool(user_state.get('checked'))
        # 수동 토글이 켜졌으면 completed로 override (manual_override 가능 항목만)
        final_status = status
        if manual and manually_checked:
            final_status = 'completed'
            if user_state.get('note'):
                note = user_state['note']
        out.append(ChecklistItem(
            id=cid,
            title=raw['title'],
            owner=raw.get('owner', ''),
            week=raw.get('week', ''),
            related_section=raw.get('related_section', ''),
            status=final_status,
            status_icon=_STATUS_ICON.get(final_status, '?'),
            note=note,
            manual_override=manual,
            manually_checked=manually_checked,
            success_metric_value=metric_val,
        ))
    return out


def _evaluate_rule(rule: Optional[str], bundle: DataBundle) -> tuple[str, Optional[str], Optional[float]]:
    """status_rule 명에 따라 상태 평가. (status, note, metric_value) 반환."""
    if not rule:
        return 'not_started', None, None

    if rule == 'geo_leakage_resolved':
        geo = (bundle.proposal or {}).get('geo_leakage') or {}
        ch = (geo.get('by_branch') or {}).get('천안') or {}
        leak = ch.get('leakage_pct')
        if leak is None:
            return 'not_started', '데이터 없음', None
        if leak < 15:
            return 'completed', f'천안 누수 {leak}% (< 15%)', leak
        return 'in_progress', f'천안 누수 {leak}% — 설정 점검 필요', leak

    if rule == 'age_25_34_excluded':
        th = (bundle.proposal or {}).get('targeting_health') or {}
        ah = th.get('age_history') or {}
        restart = ah.get('restart_branches') or []
        if restart and set(restart) == {'수원'}:
            return 'completed', '4월 이후 25-34는 수원 한정 운영 (다른 8개 지점 0)', None
        if restart:
            return 'partial', f'재운영 지점: {", ".join(restart)} (수원 외 포함)', None
        return 'not_started', '운영 이력 데이터 없음', None

    if rule == 'age_test_recovery':
        th = (bundle.proposal or {}).get('targeting_health') or {}
        ah = th.get('age_history') or {}
        post = (ah.get('post_exclusion_branches') or {}).get('수원') or {}
        cvr = post.get('cvr')
        if cvr is None:
            return 'not_started', '수원 25-34 데이터 없음', None
        # 다른 연령대 평균 CVR ~6%의 50% = 3% 도달 시 회복으로 판정
        if cvr >= 3.0:
            return 'completed', f'수원 25-34 CVR {cvr}% (회복 기준 3% 도달)', cvr
        return 'in_progress', f'수원 25-34 CVR {cvr}% (회복 기준 3% 미달)', cvr

    if rule == 'addon_v2_v1_groups_active':
        # parsed.parquet에서 v1 시기·v2 시기 모두 운영 흔적 확인
        # MVP: 분석 결과의 design_by_type에 v1·v2 양쪽 표본이 있으면 in_progress
        addon = (bundle.proposal or {}).get('addon_effect') or {}
        ver = addon.get('by_version') or {}
        v1 = (ver.get('v1_vs_period') or {}).get('addon') or {}
        v2v1 = ver.get('v2_vs_v1') or {}
        v2 = v2v1.get('v2') or {}
        if v1.get('clicks', 0) > 0 and v2.get('clicks', 0) > 0:
            return 'in_progress', 'v1·v2 광고 그룹 동시 운영 데이터 감지', None
        return 'not_started', '6월 시작 전 — 분리 운영 흔적 없음', None

    if rule == 'jinryo_v1_restore_action':
        addon = (bundle.proposal or {}).get('addon_effect') or {}
        verdicts = (addon.get('judgement') or {}).get('by_design_type') or {}
        if '진료셀프캠' in (verdicts.get('v1_better') or []):
            return 'in_progress', '진료셀프캠 v1 우세 — 복원 또는 v2 재검토 결정 필요', None
        return 'not_started', '데이터 없음 또는 6월 시작 전', None

    if rule == 'addon_design_test_concluded':
        # W2~W3 단계 — MVP에서는 시간 기준만 (6월 21일 도달 시 평가)
        return 'not_started', 'W2~W3 단계 도달 시 평가', None

    if rule == 'cpa_within_guardrail':
        from dashboard.services.kpi_progress import compute as compute_kpi
        kpi = compute_kpi(bundle)
        breaches = [b for b, info in kpi.branches.items()
                    if info.get('cpa') and not info.get('within_guardrail')]
        if not breaches:
            return 'completed', '9개 지점 모두 가드레일 이내', None
        return 'in_progress', f'가드레일 초과: {", ".join(breaches)}', None

    if rule == 'july_decision_logged':
        return 'not_started', 'W4 단계 — 7월 결정 기록 시 ✓', None

    if rule == 'kpi_achieved':
        from dashboard.services.kpi_progress import compute as compute_kpi
        kpi = compute_kpi(bundle)
        if kpi.conversions_actual >= kpi.target_base:
            return 'completed', f'6월 누적 {kpi.conversions_actual}건 (목표 {kpi.target_base})', kpi.conversions_actual
        if kpi.pace_pct >= 95:
            return 'in_progress', f'페이스 {kpi.pace_pct}% — 목표 달성 가시화', kpi.pace_pct
        if kpi.days_elapsed == 0:
            return 'not_started', '6월 시작 전', None
        return 'partial', f'페이스 {kpi.pace_pct}% — 페이스 부족', kpi.pace_pct

    if rule == 'busan_stabilized':
        # 부산 CPA가 전 지점 평균 ±15% 이내
        from dashboard.services.kpi_progress import compute as compute_kpi
        kpi = compute_kpi(bundle)
        busan = kpi.branches.get('부산', {})
        if busan.get('cpa') is None:
            return 'not_started', '부산 운영 데이터 부족', None
        other_cpas = [info['cpa'] for b, info in kpi.branches.items() if b != '부산' and info.get('cpa')]
        if not other_cpas:
            return 'not_started', '비교 가능한 지점 데이터 부족', None
        avg = sum(other_cpas) / len(other_cpas)
        ratio = busan['cpa'] / avg
        if 0.85 <= ratio <= 1.15:
            return 'completed', f'부산 CPA {busan["cpa"]:,}원 (전 지점 평균 {round(avg):,}원 ±15% 이내)', ratio
        return 'in_progress', f'부산 CPA {busan["cpa"]:,}원 / 평균 {round(avg):,}원 (격차 {round((ratio-1)*100, 1)}%)', ratio

    return 'not_started', f'룰 미구현: {rule}', None


def summary(items: list[ChecklistItem]) -> dict:
    counts = {'completed': 0, 'in_progress': 0, 'partial': 0, 'not_started': 0}
    for it in items:
        counts[it.status] = counts.get(it.status, 0) + 1
    return counts


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    from dashboard.services.data_loader import load_bundle
    bundle = load_bundle()
    items = evaluate(bundle)
    print(f'[총 항목] {len(items)}')
    for it in items:
        print(f'  {it.status_icon} [{it.status}] {it.week} {it.title}')
        if it.note:
            print(f'        → {it.note}')
    print()
    print(f'[summary] {summary(items)}')
