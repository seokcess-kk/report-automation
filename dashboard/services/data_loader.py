"""데이터 로더 — 최신 분석 결과 + 설정 + 트래커 통합 로드 + 캐시

대시보드의 모든 services가 본 모듈을 통해 데이터 접근.
1시간 TTL 메모리 캐시로 빈번한 parquet 재로드 방지.
"""
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / '.claude' / 'skills'))

CACHE_TTL_SEC = 3600


@dataclass
class DataBundle:
    """대시보드 1회 렌더링에 필요한 데이터 묶음."""
    data_dir: Path
    parsed: pd.DataFrame
    creative_tier: pd.DataFrame
    daily_snapshot: dict
    proposal: dict
    audience: Optional[pd.DataFrame] = None
    province: Optional[pd.DataFrame] = None
    operation_rules: dict = field(default_factory=dict)
    checklist: dict = field(default_factory=dict)
    alert_rules: dict = field(default_factory=dict)
    actions: list = field(default_factory=list)
    checklist_state: dict = field(default_factory=dict)
    loaded_at: float = 0.0


_cache: Optional[DataBundle] = None


def _find_latest_data_dir() -> Path:
    data_root = PROJECT_ROOT / 'output' / 'data'
    if not data_root.exists():
        raise FileNotFoundError(f"output/data 없음: {data_root}")
    candidates = sorted(
        [d for d in data_root.iterdir() if d.is_dir() and (d / 'parsed.parquet').exists()],
        key=lambda d: d.name,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"parsed.parquet 있는 디렉토리 없음: {data_root}")
    return candidates[0]


def _find_latest_creative_tier(latest_dir: Path) -> pd.DataFrame:
    """현재 dir 우선, 비어 있으면 비어있지 않은 가장 최신 dir로 fallback."""
    same = latest_dir / 'creative_tier.parquet'
    if same.exists():
        df = pd.read_parquet(same)
        if not df.empty:
            return df
    # fallback
    data_root = latest_dir.parent
    for d in sorted(data_root.iterdir(), reverse=True):
        if not d.is_dir() or d == latest_dir:
            continue
        p = d / 'creative_tier.parquet'
        if p.exists():
            try:
                df = pd.read_parquet(p)
                if not df.empty:
                    return df
            except Exception:
                continue
    return pd.DataFrame()


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def _load_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    items = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items


def _load_proposal() -> dict:
    """현 시점(2026-06) 운영 제안서. 추후 멀티 월 지원 시 라우터에서 인자화."""
    p = PROJECT_ROOT / 'output' / 'proposal' / '202606' / 'proposal_daeat_202606.json'
    if not p.exists():
        return {}
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


def _load_optional_parquet(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    try:
        return pd.read_parquet(path)
    except Exception:
        return None


def load_bundle(force_reload: bool = False) -> DataBundle:
    """전체 데이터 묶음 로드 (캐시 적용)."""
    global _cache
    now = time.time()
    if (not force_reload) and _cache is not None and (now - _cache.loaded_at) < CACHE_TTL_SEC:
        return _cache

    latest_dir = _find_latest_data_dir()
    parsed = pd.read_parquet(latest_dir / 'parsed.parquet')
    creative_tier = _find_latest_creative_tier(latest_dir)

    snapshot_path = PROJECT_ROOT / 'output' / 'daily' / 'daily_snapshot.json'
    daily_snapshot = {}
    if snapshot_path.exists():
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            daily_snapshot = json.load(f)

    config_root = PROJECT_ROOT / 'config'
    operation_rules = _load_yaml(config_root / 'operation_rules.yaml')
    checklist = _load_yaml(config_root / 'june_checklist.yaml')
    alert_rules = _load_yaml(config_root / 'alert_rules.yaml')

    tracker_root = PROJECT_ROOT / 'output' / 'tracker'
    tracker_root.mkdir(parents=True, exist_ok=True)
    actions = _load_jsonl(tracker_root / 'actions.jsonl')

    state_path = tracker_root / 'checklist_state.json'
    checklist_state = {}
    if state_path.exists():
        with open(state_path, 'r', encoding='utf-8') as f:
            checklist_state = json.load(f)

    bundle = DataBundle(
        data_dir=latest_dir,
        parsed=parsed,
        creative_tier=creative_tier,
        daily_snapshot=daily_snapshot,
        proposal=_load_proposal(),
        audience=_load_optional_parquet(latest_dir / 'normalized_by_audience.parquet'),
        province=_load_optional_parquet(latest_dir / 'normalized_by_province.parquet'),
        operation_rules=operation_rules,
        checklist=checklist,
        alert_rules=alert_rules,
        actions=actions,
        checklist_state=checklist_state,
        loaded_at=now,
    )
    _cache = bundle
    return bundle


def invalidate_cache():
    """수동 새로고침 또는 액션 로깅 후 캐시 무효화."""
    global _cache
    _cache = None


def append_action(action: dict):
    """actions.jsonl에 액션 1건 추가."""
    tracker_root = PROJECT_ROOT / 'output' / 'tracker'
    tracker_root.mkdir(parents=True, exist_ok=True)
    path = tracker_root / 'actions.jsonl'
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(action, ensure_ascii=False) + '\n')
    invalidate_cache()


def save_checklist_state(state: dict):
    """체크리스트 수동 토글 상태 저장."""
    tracker_root = PROJECT_ROOT / 'output' / 'tracker'
    tracker_root.mkdir(parents=True, exist_ok=True)
    path = tracker_root / 'checklist_state.json'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    invalidate_cache()


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    b = load_bundle()
    print(f'[data_dir] {b.data_dir.name}')
    print(f'[parsed] {b.parsed.shape}')
    print(f'[creative_tier] {b.creative_tier.shape}')
    print(f'[daily_snapshot] {len(b.daily_snapshot)} keys')
    print(f'[proposal] {len(b.proposal)} keys: {list(b.proposal.keys())[:5]}...')
    print(f'[audience] {b.audience.shape if b.audience is not None else "None"}')
    print(f'[province] {b.province.shape if b.province is not None else "None"}')
    print(f'[operation_rules] {len(b.operation_rules)} sections')
    print(f'[checklist] {len(b.checklist.get("checklist", []))} items')
    print(f'[alert_rules] {len(b.alert_rules)} sections')
    print(f'[actions] {len(b.actions)} logged')
    print(f'[checklist_state] {len(b.checklist_state)} states')
