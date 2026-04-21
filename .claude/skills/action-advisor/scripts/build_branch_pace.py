"""지점별 월간 페이스 JSON 생성.

입력:
    output/data/YYYYMMDD/parsed.parquet  (현재 월 데이터만 필터)

출력:
    output/data/YYYYMMDD/branch_pace.json

사용법:
    python .claude/skills/action-advisor/scripts/build_branch_pace.py output/data/20260421
"""
import calendar
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import VALID_BRANCHES, MONTHLY_BUDGET, MONTHLY_TARGET_CONV, MONTHLY_TARGET_CONV_BY_BRANCH


def _status_branch(budget_pct: float, conv_pct: float, date_progress: float,
                   cpa: float, target_cpa: float) -> str:
    conv_gap = conv_pct - date_progress
    budget_gap = budget_pct - date_progress
    cpa_ratio = (cpa / target_cpa) if target_cpa and not np.isnan(cpa) else 1.0

    if conv_gap <= -20 or cpa_ratio > 1.5 or budget_gap > 20:
        return 'danger'
    if conv_gap <= -10 or cpa_ratio > 1.1 or budget_gap > 10:
        return 'warn'
    return 'ok'


def _status_overall(budget_pct: float, conv_pct: float, date_progress: float) -> str:
    conv_gap = conv_pct - date_progress
    budget_gap = budget_pct - date_progress
    if conv_gap <= -15 or budget_gap > 20:
        return 'danger'
    if conv_gap <= -5 or budget_gap > 10:
        return 'warn'
    return 'ok'


def build_pace(data_dir: str) -> dict:
    parsed_path = os.path.join(data_dir, 'parsed.parquet')
    if not os.path.exists(parsed_path):
        raise FileNotFoundError(parsed_path)

    df = pd.read_parquet(parsed_path)
    df['date'] = pd.to_datetime(df['date'])

    # 데이터 최신일 기준으로 "이번 달" 결정
    last_date = df['date'].max().date()
    month_start = date(last_date.year, last_date.month, 1)
    days_total = calendar.monthrange(last_date.year, last_date.month)[1]
    days_elapsed = (last_date - month_start).days + 1
    date_progress = round(days_elapsed / days_total * 100, 1)

    df_month = df[df['date'].dt.date >= month_start].copy()

    # 전체 합계 (OFF 포함 — 실제 집행된 비용/전환은 모두 반영)
    total_cost = float(df_month['cost'].sum())
    total_conv = float(df_month['conversions'].sum())
    total_budget = sum(MONTHLY_BUDGET.get(b, 0) for b in VALID_BRANCHES)

    budget_pct = round(total_cost / total_budget * 100, 1) if total_budget else 0
    conv_pct = round(total_conv / MONTHLY_TARGET_CONV * 100, 1) if MONTHLY_TARGET_CONV else 0
    proj_conv = round(total_conv / days_elapsed * days_total) if days_elapsed else 0
    proj_pct = round(proj_conv / MONTHLY_TARGET_CONV * 100, 1) if MONTHLY_TARGET_CONV else 0

    # TARGET_CPA (전역): target_cpa.csv 우선, 없으면 중앙값
    target_cpa_global = _load_target_cpa(df_month)

    # 지점별
    branches = []
    for b in VALID_BRANCHES:
        df_b = df_month[df_month.get('지점') == b] if '지점' in df_month.columns else pd.DataFrame()
        budget = MONTHLY_BUDGET.get(b, 0)
        conv_target = MONTHLY_TARGET_CONV_BY_BRANCH.get(b, 0)

        cost = float(df_b['cost'].sum()) if len(df_b) else 0.0
        conv = float(df_b['conversions'].sum()) if len(df_b) else 0.0
        clicks = float(df_b['clicks'].sum()) if len(df_b) else 0.0
        impressions = float(df_b['impressions'].sum()) if len(df_b) else 0.0

        b_budget_pct = round(cost / budget * 100, 1) if budget else 0.0
        b_conv_pct = round(conv / conv_target * 100, 1) if conv_target else 0.0
        b_proj_conv = round(conv / days_elapsed * days_total) if days_elapsed else 0
        b_proj_pct = round(b_proj_conv / conv_target * 100, 1) if conv_target else 0.0
        cpa = round(cost / conv) if conv else float('nan')
        cpa_vs_target = round(cpa / target_cpa_global * 100) if (target_cpa_global and not np.isnan(cpa)) else None

        # Sparkline — 월초부터 일별 cost/conv
        sparkline = []
        if len(df_b):
            daily = (
                df_b.groupby(df_b['date'].dt.date)
                .agg(cost=('cost', 'sum'), conv=('conversions', 'sum'))
                .reset_index()
                .sort_values('date')
            )
            for _, r in daily.iterrows():
                sparkline.append({
                    'date': r['date'].isoformat(),
                    'cost': float(r['cost']),
                    'conv': float(r['conv']),
                })

        status = _status_branch(b_budget_pct, b_conv_pct, date_progress,
                                cpa if not np.isnan(cpa) else target_cpa_global,
                                target_cpa_global)

        branches.append({
            'branch': b,
            'budget': budget,
            'cost_so_far': round(cost),
            'budget_pct': b_budget_pct,
            'conv_target': conv_target,
            'conv_so_far': round(conv),
            'conv_pct': b_conv_pct,
            'proj_conv': b_proj_conv,
            'proj_pct': b_proj_pct,
            'clicks': round(clicks),
            'impressions': round(impressions),
            'cpa': None if np.isnan(cpa) else int(cpa),
            'target_cpa': target_cpa_global,
            'cpa_vs_target_pct': cpa_vs_target,
            'status': status,
            'sparkline': sparkline,
        })

    return {
        'updated': last_date.isoformat(),
        'month': f"{last_date.year}-{last_date.month:02d}",
        'days_total': days_total,
        'days_elapsed': days_elapsed,
        'date_progress': date_progress,
        'overall': {
            'budget_total': total_budget,
            'cost_so_far': round(total_cost),
            'budget_pct': budget_pct,
            'conv_target': MONTHLY_TARGET_CONV,
            'conv_so_far': round(total_conv),
            'conv_pct': conv_pct,
            'proj_conv': proj_conv,
            'proj_pct': proj_pct,
            'target_cpa': target_cpa_global,
            'status': _status_overall(budget_pct, conv_pct, date_progress),
        },
        'branches': branches,
    }


def _load_target_cpa(df_month: pd.DataFrame) -> int:
    """target_cpa.csv 우선, 없으면 중앙값 CPA."""
    tcpa_path = os.path.join('input', 'target_cpa.csv')
    if os.path.exists(tcpa_path):
        try:
            t = pd.read_csv(tcpa_path)
            if 'target_cpa' in t.columns and len(t) > 0:
                return int(t['target_cpa'].iloc[0])
        except Exception:
            pass
    # fallback: ON 소재 CPA 중앙값
    if 'is_off' in df_month.columns:
        df_on = df_month[~df_month['is_off']]
    else:
        df_on = df_month
    conv = df_on['conversions'].sum()
    cost = df_on['cost'].sum()
    return int(cost / conv) if conv else 25000


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else None
    if not data_dir:
        # output/data/YYYYMMDD 중 최신
        base = Path('output/data')
        if not base.exists():
            print(f"[ERROR] {base} 없음")
            sys.exit(1)
        data_dir = str(max(base.iterdir()))
        print(f"[INFO] 최신 data_dir 자동 감지: {data_dir}")

    pace = build_pace(data_dir)
    out_path = os.path.join(data_dir, 'branch_pace.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(pace, f, ensure_ascii=False, indent=2)
    print(f"[OK] {out_path} ({len(pace['branches'])}지점)")


if __name__ == '__main__':
    main()
