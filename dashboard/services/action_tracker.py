"""액션 트래커 — 운영자가 수행한 액션 기록 + D+1/D+3/D+7 효과 조회

저장: output/tracker/actions.jsonl (append-only)
스키마는 docs/dashboard-plan.md 10장 참조.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Optional

from dashboard.services.data_loader import DataBundle, append_action, load_bundle


@dataclass
class ActionLog:
    id: str
    date: str
    timestamp: str
    action_type: str
    branch: Optional[str] = None
    ad_id: Optional[str] = None
    creative_name: Optional[str] = None
    before: Optional[str] = None
    after: Optional[str] = None
    reason: str = ''
    expected_metric: Optional[str] = None
    review_after_days: list = None    # [1, 3, 7]
    operator: str = 'agency'
    linked_alert_id: Optional[str] = None
    linked_checklist_id: Optional[str] = None
    effects: dict = None              # {d1: {...}, d3: {...}, d7: {...}}


def log_action(
    action_type: str,
    reason: str,
    branch: Optional[str] = None,
    ad_id: Optional[str] = None,
    creative_name: Optional[str] = None,
    before: Optional[str] = None,
    after: Optional[str] = None,
    expected_metric: Optional[str] = None,
    review_after_days: list = None,
    operator: str = 'agency',
    linked_alert_id: Optional[str] = None,
    linked_checklist_id: Optional[str] = None,
) -> dict:
    """액션 1건 기록 + actions.jsonl에 append."""
    now = datetime.now()
    action = {
        'id': str(uuid.uuid4()),
        'date': now.strftime('%Y-%m-%d'),
        'timestamp': now.isoformat(timespec='seconds'),
        'action_type': action_type,
        'branch': branch,
        'ad_id': ad_id,
        'creative_name': creative_name,
        'before': before,
        'after': after,
        'reason': reason,
        'expected_metric': expected_metric,
        'review_after_days': review_after_days or [1, 3, 7],
        'operator': operator,
        'linked_alert_id': linked_alert_id,
        'linked_checklist_id': linked_checklist_id,
        'effects': {'d1': None, 'd3': None, 'd7': None},
    }
    append_action(action)
    return action


def list_actions(bundle: DataBundle, limit: int = 50, since: Optional[date] = None) -> list[dict]:
    """저장된 액션 조회. since 이후만 필터링 가능."""
    actions = bundle.actions or []
    if since:
        actions = [a for a in actions if a.get('date', '') >= since.strftime('%Y-%m-%d')]
    return sorted(actions, key=lambda a: a.get('timestamp', ''), reverse=True)[:limit]


def pending_effect_measurements(bundle: DataBundle, today: Optional[date] = None) -> list[dict]:
    """D+1/D+3/D+7 측정이 필요한 액션 + 측정해야 할 날 반환."""
    today = today or date.today()
    pending = []
    for a in (bundle.actions or []):
        action_date_str = a.get('date')
        if not action_date_str:
            continue
        try:
            action_date = datetime.strptime(action_date_str, '%Y-%m-%d').date()
        except ValueError:
            continue
        effects = a.get('effects') or {}
        for n in (a.get('review_after_days') or [1, 3, 7]):
            key = f'd{n}'
            if effects.get(key) is not None:
                continue
            target_day = action_date + timedelta(days=n)
            if today >= target_day:
                pending.append({'action': a, 'days': n, 'target_day': target_day.strftime('%Y-%m-%d')})
    return pending


# Re-export for convenience
from datetime import timedelta


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    bundle = load_bundle()
    print(f'[기존 액션] {len(bundle.actions)}건')
    print(f'[측정 대기] {len(pending_effect_measurements(bundle))}건')
    print()
    # 테스트 액션 1건 (실제로 기록되니까 주의 — 검증 시에만 사용)
    # action = log_action(
    #     action_type='budget_decrease',
    #     branch='천안',
    #     before='daily_budget 70000',
    #     after='daily_budget 50000',
    #     reason='CPA 가드레일 초과 + 경기 누수 확인',
    #     expected_metric='CPA',
    #     linked_checklist_id='w1_cheonan_geo_setting_check',
    # )
    # print(f'[기록 완료] id={action["id"]}')
