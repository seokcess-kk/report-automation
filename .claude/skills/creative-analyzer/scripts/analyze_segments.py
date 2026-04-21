"""세그먼트 분석: 요일/소재유형/(시간대)

입력:
    parsed.parquet             — 일별 x 광고
    normalized_by_hour.parquet — (선택) 시간대 breakdown

출력 (data_dir 아래):
    weekday_analysis.parquet/csv
    creative_type_analysis.parquet/csv
    hour_analysis.parquet/csv  (입력 있을 때만)

사용법:
    python .claude/skills/creative-analyzer/scripts/analyze_segments.py output/data/20260421
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import VALID_AD_TYPES

WEEKDAY_KOR = {
    'Monday': '월', 'Tuesday': '화', 'Wednesday': '수', 'Thursday': '목',
    'Friday': '금', 'Saturday': '토', 'Sunday': '일',
}
WEEKDAY_ORDER = ['월', '화', '수', '목', '금', '토', '일']


def _efficiency(summary: pd.DataFrame) -> pd.DataFrame:
    """공용 KPI 부여 (비중/효율점수)"""
    total_cost = summary['총비용'].sum()
    total_conv = summary['총전환'].sum()
    summary['비용비중'] = (summary['총비용'] / total_cost * 100).round(1) if total_cost > 0 else 0.0
    summary['전환비중'] = (summary['총전환'] / total_conv * 100).round(1) if total_conv > 0 else 0.0
    summary['CPA'] = (summary['총비용'] / summary['총전환'].replace(0, np.nan)).round(0)
    summary['CTR'] = (summary['총클릭'] / summary['총노출'].replace(0, np.nan) * 100).round(2)
    summary['CVR'] = (summary['총전환'] / summary['총클릭'].replace(0, np.nan) * 100).round(2)
    summary['예산효율점수'] = (summary['전환비중'] / summary['비용비중'].replace(0, np.nan)).round(2)
    return summary


def analyze_weekdays(df: pd.DataFrame) -> pd.DataFrame:
    """요일별 집계. parsed.parquet 전체(ON+OFF) 사용 — 최근 30일 기준."""
    if 'date' not in df.columns or len(df) == 0:
        return pd.DataFrame()

    d = df.copy()
    d['date'] = pd.to_datetime(d['date'])
    # 최근 30일만 (요일별 최소 4회 관측)
    cutoff = d['date'].max() - pd.Timedelta(days=30)
    d = d[d['date'] >= cutoff]
    d['weekday'] = d['date'].dt.day_name().map(WEEKDAY_KOR)

    summary = d.groupby('weekday').agg(
        총비용=('cost', 'sum'),
        총전환=('conversions', 'sum'),
        총클릭=('clicks', 'sum'),
        총노출=('impressions', 'sum'),
        일수=('date', 'nunique'),
    ).reset_index()

    summary['weekday'] = pd.Categorical(summary['weekday'], categories=WEEKDAY_ORDER, ordered=True)
    summary = summary.sort_values('weekday').reset_index(drop=True)
    summary = _efficiency(summary)
    return summary


def analyze_creative_types(df: pd.DataFrame) -> pd.DataFrame:
    """소재 유형별 집계. 최근 30일 + ON 소재만."""
    if '소재유형' not in df.columns or len(df) == 0:
        return pd.DataFrame()

    d = df.copy()
    d['date'] = pd.to_datetime(d['date'])
    cutoff = d['date'].max() - pd.Timedelta(days=30)
    d = d[d['date'] >= cutoff]

    # ON 소재만 (OFF 제외 — 현재 전략 평가용)
    if 'is_off' in d.columns:
        d = d[~d['is_off']]

    d = d[d['소재유형'].isin(VALID_AD_TYPES)]
    if len(d) == 0:
        return pd.DataFrame()

    summary = d.groupby('소재유형').agg(
        총비용=('cost', 'sum'),
        총전환=('conversions', 'sum'),
        총클릭=('clicks', 'sum'),
        총노출=('impressions', 'sum'),
        소재수=('매칭키', 'nunique') if '매칭키' in d.columns else ('ad_id', 'nunique'),
    ).reset_index()

    summary = _efficiency(summary)
    return summary.sort_values('예산효율점수', ascending=False).reset_index(drop=True)


def analyze_hours(df_hour: pd.DataFrame) -> pd.DataFrame:
    """시간대별 집계 (normalized_by_hour.parquet 기반)."""
    if df_hour is None or len(df_hour) == 0:
        return pd.DataFrame()
    if 'hour' not in df_hour.columns:
        # stat_time_hour 가 있을 수 있음
        if 'stat_time_hour' in df_hour.columns:
            df_hour = df_hour.rename(columns={'stat_time_hour': 'hour'})
        else:
            return pd.DataFrame()

    d = df_hour.copy()
    d['hour'] = d['hour'].astype(int)

    summary = d.groupby('hour').agg(
        총비용=('cost', 'sum'),
        총전환=('conversions', 'sum'),
        총클릭=('clicks', 'sum'),
        총노출=('impressions', 'sum'),
    ).reset_index().sort_values('hour')

    summary = _efficiency(summary)
    return summary.reset_index(drop=True)


def main(data_dir: str):
    parsed_path = os.path.join(data_dir, 'parsed.parquet')
    if not os.path.exists(parsed_path):
        print(f"[ERROR] {parsed_path} 없음")
        sys.exit(1)

    df = pd.read_parquet(parsed_path)
    if 'parse_status' in df.columns:
        df = df[df['parse_status'] == 'OK']

    # 요일
    wk = analyze_weekdays(df)
    if len(wk) > 0:
        wk.to_parquet(os.path.join(data_dir, 'weekday_analysis.parquet'), index=False)
        wk.to_csv(os.path.join(data_dir, 'weekday_analysis.csv'), index=False, encoding='utf-8-sig')
        print(f"[OK] weekday_analysis ({len(wk)}행)")

    # 소재 유형
    ct = analyze_creative_types(df)
    if len(ct) > 0:
        ct.to_parquet(os.path.join(data_dir, 'creative_type_analysis.parquet'), index=False)
        ct.to_csv(os.path.join(data_dir, 'creative_type_analysis.csv'), index=False, encoding='utf-8-sig')
        print(f"[OK] creative_type_analysis ({len(ct)}행)")

    # 시간대 (있을 때만)
    hour_path = os.path.join(data_dir, 'normalized_by_hour.parquet')
    hr = pd.DataFrame()
    if os.path.exists(hour_path):
        hr = analyze_hours(pd.read_parquet(hour_path))
        if len(hr) > 0:
            hr.to_parquet(os.path.join(data_dir, 'hour_analysis.parquet'), index=False)
            hr.to_csv(os.path.join(data_dir, 'hour_analysis.csv'), index=False, encoding='utf-8-sig')
            print(f"[OK] hour_analysis ({len(hr)}행)")

    # 웹 대시보드용 통합 JSON
    def _to_records(df: pd.DataFrame) -> list:
        if len(df) == 0:
            return []
        d = df.copy()
        # NaN → None
        for c in d.columns:
            if d[c].dtype.kind in ('f', 'i'):
                d[c] = d[c].where(d[c].notna(), None)
        return d.to_dict(orient='records')

    payload = {
        'weekday': _to_records(wk),
        'creative_type': _to_records(ct),
        'hour': _to_records(hr),
    }
    json_path = os.path.join(data_dir, 'segment_analysis.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    print(f"[OK] segment_analysis.json (weekday {len(wk)} / type {len(ct)} / hour {len(hr)})")


if __name__ == '__main__':
    data_dir = sys.argv[1] if len(sys.argv) > 1 else None
    if not data_dir:
        base = Path('output/data')
        if base.exists():
            data_dir = str(max(base.iterdir()))
            print(f"[INFO] 최신 data_dir: {data_dir}")
        else:
            sys.exit(1)
    main(data_dir)
