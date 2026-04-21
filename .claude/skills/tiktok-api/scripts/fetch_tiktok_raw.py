"""TikTok Marketing API → input/tiktok_raw.csv

최근 N일(기본 14)의 일별 × 광고별 metrics를 API로 수집하여
수동 export와 동일한 CSV 스키마로 저장.

사용법:
    python .claude/skills/tiktok-api/scripts/fetch_tiktok_raw.py
    python .claude/skills/tiktok-api/scripts/fetch_tiktok_raw.py --days 30
    python .claude/skills/tiktok-api/scripts/fetch_tiktok_raw.py --output input/tiktok_raw.csv

필수 환경변수:
    TIKTOK_ACCESS_TOKEN, TIKTOK_ADVERTISER_ID
"""
import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    HOST,
    TIKTOK_ACCESS_TOKEN,
    TIKTOK_ADVERTISER_ID,
    TIKTOK_APP_ID,
    TIKTOK_APP_SECRET,
    require,
)

# 수동 export CSV 컬럼 순서 (절대 변경 금지 — 하류 파이프라인이 이 스키마 기대)
CSV_COLUMNS = [
    '캠페인 이름', '광고 이름', '광고 ID', '일별',
    '비용', '노출수', 'CPM',
    '클릭수(목적지)', 'CPC(목적지)', 'CTR(목적지)',
    '전환수', '전환당 비용', '전환율(CVR)',
    '빈도', '동영상 조회수', '통화',
]

# API metric 이름 → CSV 컬럼
METRIC_TO_CSV = {
    'spend': '비용',
    'impressions': '노출수',
    'cpm': 'CPM',
    'clicks': '클릭수(목적지)',
    'cpc': 'CPC(목적지)',
    'ctr': 'CTR(목적지)',
    'conversion': '전환수',
    'cost_per_conversion': '전환당 비용',
    'conversion_rate': '전환율(CVR)',
    'frequency': '빈도',
    'video_play_actions': '동영상 조회수',
}

METRIC_FIELDS = list(METRIC_TO_CSV.keys())
# API가 metrics에 함께 반환하는 meta 필드 (dimension 역할이지만 metrics로 요청)
META_FIELDS = ['ad_name', 'campaign_name', 'currency']

# 재시도 정책
MAX_RETRIES = 3
RETRY_BACKOFF_SEC = 5


def fetch_report(
    start_date: str,
    end_date: str,
    advertiser_id: str,
    access_token: str,
    page_size: int = 1000,
) -> list:
    """
    /report/integrated/get/ 호출 — 페이지네이션 처리.
    returns: 모든 페이지의 list 항목 병합
    """
    url = f'{HOST}/report/integrated/get/'
    headers = {'Access-Token': access_token}

    all_rows = []
    page = 1

    while True:
        params = {
            'advertiser_id': advertiser_id,
            'report_type': 'BASIC',
            'data_level': 'AUCTION_AD',
            'dimensions': json.dumps(['ad_id', 'stat_time_day']),
            'metrics': json.dumps(METRIC_FIELDS + META_FIELDS),
            'start_date': start_date,
            'end_date': end_date,
            'page': page,
            'page_size': page_size,
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=60)
                resp.raise_for_status()
                payload = resp.json()
                if payload.get('code') != 0:
                    raise RuntimeError(
                        f"API error code={payload.get('code')} msg={payload.get('message')}"
                    )
                break
            except (requests.RequestException, RuntimeError) as e:
                if attempt == MAX_RETRIES:
                    raise
                wait = RETRY_BACKOFF_SEC * attempt
                print(f"[retry {attempt}/{MAX_RETRIES}] {e} — {wait}s 대기 후 재시도")
                time.sleep(wait)

        data = payload.get('data') or {}
        rows = data.get('list') or []
        all_rows.extend(rows)

        page_info = data.get('page_info') or {}
        total_page = page_info.get('total_page', 0)
        if page >= total_page or total_page == 0:
            break
        page += 1

    return all_rows


def api_row_to_csv_row(api_row: dict) -> dict:
    """API 응답 1 row → CSV 1 row"""
    dims = api_row.get('dimensions') or {}
    mets = api_row.get('metrics') or {}

    stat_day = dims.get('stat_time_day', '')
    # 'YYYY-MM-DD HH:MM:SS' 또는 'YYYY-MM-DD' 처리
    date_str = stat_day[:10] if stat_day else ''

    row = {
        '캠페인 이름': mets.get('campaign_name', ''),
        '광고 이름': mets.get('ad_name', ''),
        '광고 ID': str(dims.get('ad_id', '')),
        '일별': date_str,
        '통화': mets.get('currency', 'KRW'),
    }
    for api_key, csv_key in METRIC_TO_CSV.items():
        row[csv_key] = mets.get(api_key, 0)
    return row


def merge_with_existing(new_df: pd.DataFrame, existing_path: str) -> pd.DataFrame:
    """
    기존 CSV와 병합.
    - new_df 에 포함된 (일별) 값들은 기존에서 제거 후 새 값으로 대체
    - 그 외 이전 날짜는 그대로 유지
    """
    if not Path(existing_path).exists():
        return new_df

    existing = pd.read_csv(existing_path, encoding='utf-8-sig', dtype={'광고 ID': str})
    # 컬럼 누락 방지
    for col in CSV_COLUMNS:
        if col not in existing.columns:
            existing[col] = ''
    existing = existing[CSV_COLUMNS]

    new_dates = set(new_df['일별'].unique())
    kept = existing[~existing['일별'].isin(new_dates)]

    merged = pd.concat([kept, new_df], ignore_index=True)
    merged = merged.sort_values(['일별', '광고 이름']).reset_index(drop=True)
    return merged


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=14, help='최근 N일 (기본 14)')
    parser.add_argument('--output', default='input/tiktok_raw.csv')
    parser.add_argument('--end-date', default=None, help='YYYY-MM-DD (기본: 오늘)')
    args = parser.parse_args()

    access_token = require('TIKTOK_ACCESS_TOKEN', TIKTOK_ACCESS_TOKEN)
    advertiser_id = require('TIKTOK_ADVERTISER_ID', TIKTOK_ADVERTISER_ID)

    end_date = (
        datetime.strptime(args.end_date, '%Y-%m-%d').date()
        if args.end_date else date.today()
    )
    start_date = end_date - timedelta(days=args.days - 1)

    print(f"[fetch] advertiser={advertiser_id} 기간={start_date} ~ {end_date}")

    rows = fetch_report(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        advertiser_id,
        access_token,
    )
    print(f"[fetch] API 응답 {len(rows)}개 레코드")

    if not rows:
        print("[fetch] 수신 데이터 없음 — 기존 CSV 유지하고 종료")
        return

    new_df = pd.DataFrame([api_row_to_csv_row(r) for r in rows])
    new_df = new_df[CSV_COLUMNS]

    merged = merge_with_existing(new_df, args.output)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(args.output, index=False, encoding='utf-8-sig')
    print(f"[fetch] 저장 완료 → {args.output} ({len(merged)}행)")


if __name__ == '__main__':
    main()
