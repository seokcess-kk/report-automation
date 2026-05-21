"""액션 효과 추적 워커 — D+1/D+3/D+7 시점 도래한 액션의 효과 자동 측정

크론 또는 매일 1회 수동 실행:
  python -m dashboard.workers.effect_tracker

actions.jsonl을 rewrite 방식으로 업데이트 (append-only가 아님 — 효과 측정이 필요).
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / '.claude' / 'skills'))


def _kpi_for_date(parsed: pd.DataFrame, target_date: date, branch: Optional[str] = None,
                  ad_id: Optional[str] = None) -> dict:
    """해당 일자·지점·광고의 KPI 산출."""
    df = parsed.copy()
    df['date'] = pd.to_datetime(df['date']).dt.date
    df = df[df['date'] == target_date]
    if branch:
        df = df[df['지점'] == branch]
    if ad_id:
        df['ad_id'] = df['ad_id'].astype(str)
        df = df[df['ad_id'] == str(ad_id)]
    if df.empty:
        return {}
    cost = int(df['cost'].sum())
    clicks = int(df['clicks'].sum())
    conv = int(df['conversions'].sum())
    impr = int(df['impressions'].sum())
    return {
        'cost': cost, 'clicks': clicks, 'conversions': conv, 'impressions': impr,
        'cpa': round(cost / conv) if conv else None,
        'cvr': round(conv / clicks * 100, 2) if clicks else None,
        'ctr': round(clicks / impr * 100, 2) if impr else None,
    }


def measure_effects(today: Optional[date] = None):
    """D+1/D+3/D+7 미측정 효과를 채우고 actions.jsonl rewrite."""
    today = today or date.today()
    tracker_path = PROJECT_ROOT / 'output' / 'tracker' / 'actions.jsonl'
    if not tracker_path.exists():
        print('[skip] actions.jsonl 없음')
        return 0

    # 최신 parsed 로드
    data_root = PROJECT_ROOT / 'output' / 'data'
    candidates = sorted([d for d in data_root.iterdir() if d.is_dir() and (d / 'parsed.parquet').exists()], reverse=True)
    if not candidates:
        print('[skip] parsed.parquet 없음')
        return 0
    parsed = pd.read_parquet(candidates[0] / 'parsed.parquet')

    updated_count = 0
    actions = []
    with open(tracker_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                a = json.loads(line)
            except json.JSONDecodeError:
                continue
            actions.append(a)

    for a in actions:
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
            if today < target_day:
                continue
            kpi = _kpi_for_date(parsed, target_day, branch=a.get('branch'), ad_id=a.get('ad_id'))
            if not kpi:
                continue
            effects[key] = {
                'measured_at': datetime.now().isoformat(timespec='seconds'),
                'target_day': target_day.strftime('%Y-%m-%d'),
                **kpi,
            }
            updated_count += 1
        a['effects'] = effects

    # rewrite
    with open(tracker_path, 'w', encoding='utf-8') as f:
        for a in actions:
            f.write(json.dumps(a, ensure_ascii=False) + '\n')

    print(f'[updated] {updated_count}개 effect 측정')
    return updated_count


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    measure_effects()
