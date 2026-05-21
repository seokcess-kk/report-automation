"""TikTok Marketing API → input/tiktok_raw.csv (+ 선택적 tiktok_raw_by_age.csv)

최근 N일(기본 14)의 일별 × 광고별 metrics 를 API로 수집하여
수동 export와 동일한 CSV 스키마로 저장.

사용법:
    python .claude/skills/tiktok-api/scripts/fetch_tiktok_raw.py
    python .claude/skills/tiktok-api/scripts/fetch_tiktok_raw.py --days 30
    python .claude/skills/tiktok-api/scripts/fetch_tiktok_raw.py --include-age
    python .claude/skills/tiktok-api/scripts/fetch_tiktok_raw.py --start 2026-04-01 --end 2026-04-20

필수 환경변수:
    TIKTOK_ACCESS_TOKEN, TIKTOK_ADVERTISER_ID

선택 환경변수 (API 메트릭명이 계정별로 다를 때 오버라이드):
    TIKTOK_METRIC_LANDING   기본: real_time_landing_page_view
    TIKTOK_METRIC_REACH     기본: reach
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
    require,
)

# 메트릭명 오버라이드 (계정별 차이 흡수)
# TikTok pixel PAGE_VIEW 이벤트 기반 "랜딩 페이지 조회(웹사이트)"의 API 메트릭명.
# 표준: total_pageview. 계정이 Events API v2를 쓰거나 이벤트 매핑이 다르면 아래 후보 참고:
#   - total_pageview (pixel PAGE_VIEW)
#   - onsite_shopping_page_views (TikTok onsite destination)
#   - complete_payment / total_complete_payment (픽셀 이벤트가 결제인 경우)
METRIC_LANDING = os.getenv('TIKTOK_METRIC_LANDING', 'total_pageview')
METRIC_REACH = os.getenv('TIKTOK_METRIC_REACH', 'reach')

# 수동 export CSV 컬럼 순서 (하류 파이프라인이 이 스키마 기대 — 끝에 추가만 허용)
CSV_COLUMNS = [
    '캠페인 이름', '광고 이름', '광고 ID', '일별',
    '비용', '노출수', 'CPM',
    '클릭수(목적지)', 'CPC(목적지)', 'CTR(목적지)',
    '전환수', '전환당 비용', '전환율(CVR)',
    '빈도', '동영상 조회수', '통화',
    '랜딩 페이지 조회(웹사이트)', '도달',
    # 시청 깊이 메트릭 (R12 — 인플방문후기 가설 검증)
    '2초 시청', '6초 시청',
    '25% 시청 완료', '50% 시청 완료', '75% 시청 완료', '100% 시청 완료',
    '평균 재생 시간',
    # 인게이지먼트 메트릭 (Phase 1C — 바이럴 지수, 5.4 가설 정밀화)
    '좋아요', '댓글', '공유', '팔로우', '프로필 방문',
    '15초 시청',
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
    METRIC_LANDING: '랜딩 페이지 조회(웹사이트)',
    METRIC_REACH: '도달',
    # 시청 깊이 메트릭
    'video_watched_2s': '2초 시청',
    'video_watched_6s': '6초 시청',
    'video_views_p25': '25% 시청 완료',
    'video_views_p50': '50% 시청 완료',
    'video_views_p75': '75% 시청 완료',
    'video_views_p100': '100% 시청 완료',
    'average_video_play': '평균 재생 시간',
    # 인게이지먼트 메트릭 (Phase 1C)
    'likes': '좋아요',
    'comments': '댓글',
    'shares': '공유',
    'follows': '팔로우',
    'profile_visits': '프로필 방문',
    'engaged_view_15s': '15초 시청',
}

# 나이대 CSV (별도 파일)
CSV_COLUMNS_BY_AGE = [
    '캠페인 이름', '광고 이름', '광고 ID', '일별', '나이',
    '비용', '노출수',
    '클릭수(목적지)', 'CTR(목적지)',
    '전환수', '전환당 비용', '전환율(CVR)',
    '랜딩 페이지 조회(웹사이트)', '도달', '통화',
]

# 오디언스(나이+성별) CSV — Phase 1A
CSV_COLUMNS_BY_AUDIENCE = [
    '캠페인 이름', '광고 이름', '광고 ID', '일별', '나이', '성별',
    '비용', '노출수',
    '클릭수(목적지)', 'CTR(목적지)',
    '전환수', '전환당 비용', '전환율(CVR)',
    '랜딩 페이지 조회(웹사이트)', '도달', '통화',
]

# 지역(province_id) CSV — Phase 1B
CSV_COLUMNS_BY_PROVINCE = [
    '캠페인 이름', '광고 이름', '광고 ID', '일별', 'province_id',
    '비용', '노출수',
    '클릭수(목적지)', 'CTR(목적지)',
    '전환수', '전환당 비용', '전환율(CVR)',
    '랜딩 페이지 조회(웹사이트)', '도달', '통화',
]

# 시간대 CSV (별도 파일) — 일별 × 광고 × 시간
CSV_COLUMNS_BY_HOUR = [
    '캠페인 이름', '광고 이름', '광고 ID', '일별', '시간',
    '비용', '노출수',
    '클릭수(목적지)', 'CTR(목적지)',
    '전환수', '전환당 비용', '전환율(CVR)',
    '랜딩 페이지 조회(웹사이트)', '도달', '통화',
]

METRIC_FIELDS = list(METRIC_TO_CSV.keys())
META_FIELDS = ['ad_name', 'campaign_name', 'currency']

MAX_RETRIES = 3
RETRY_BACKOFF_SEC = 5


def fetch_report(
    start_date: str,
    end_date: str,
    advertiser_id: str,
    access_token: str,
    dimensions: list,
    report_type: str = 'BASIC',
    metrics: list = None,
    page_size: int = 1000,
) -> list:
    """/report/integrated/get/ 호출 — 페이지네이션 처리.

    report_type:
        BASIC    — 표준 지표 + ad_id/stat_time_day 디멘션
        AUDIENCE — age/gender 등 오디언스 breakdown 디멘션
    """
    url = f'{HOST}/report/integrated/get/'
    headers = {'Access-Token': access_token}

    if metrics is None:
        metrics = METRIC_FIELDS + META_FIELDS

    all_rows = []
    page = 1

    while True:
        params = {
            'advertiser_id': advertiser_id,
            'report_type': report_type,
            'data_level': 'AUCTION_AD',
            'dimensions': json.dumps(dimensions),
            'metrics': json.dumps(metrics),
            'start_date': start_date,
            'end_date': end_date,
            'page': page,
            'page_size': page_size,
        }

        # 토큰 만료 코드 — 재시도 불필요 (즉시 실패)
        TOKEN_ERROR_CODES = {40100, 40104, 40105, 40107, 40109, 40113, 40114}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=60)
                if resp.status_code in (401, 403):
                    raise SystemExit(
                        f"[FATAL] HTTP {resp.status_code} — TIKTOK_ACCESS_TOKEN 만료 또는 권한 없음. "
                        f"oauth_bootstrap.py 로 재발급 필요."
                    )
                resp.raise_for_status()
                payload = resp.json()
                code = payload.get('code')
                if code != 0:
                    msg = payload.get('message', '')
                    if code in TOKEN_ERROR_CODES:
                        raise SystemExit(
                            f"[FATAL] TikTok 토큰 만료/무효 (code={code} msg={msg}). "
                            f"TIKTOK_ACCESS_TOKEN 갱신 필요."
                        )
                    if 'metric' in msg.lower() or code == 40002:
                        raise RuntimeError(
                            f"API error code={code} msg={msg}\n"
                            f"  -> 메트릭/디멘션 확인 필요. TIKTOK_METRIC_LANDING / TIKTOK_METRIC_REACH "
                            f"환경변수로 오버라이드 가능. 현재값: landing={METRIC_LANDING}, reach={METRIC_REACH}"
                        )
                    raise RuntimeError(f"API error code={code} msg={msg}")
                break
            except SystemExit:
                raise
            except (requests.RequestException, RuntimeError) as e:
                if attempt == MAX_RETRIES:
                    raise
                wait = RETRY_BACKOFF_SEC * attempt
                print(f"[retry {attempt}/{MAX_RETRIES}] {e} - {wait}s wait")
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


def api_row_to_csv_row(api_row: dict, include_age: bool = False,
                       include_hour: bool = False, include_audience: bool = False,
                       include_province: bool = False) -> dict:
    """API 응답 1 row → CSV 1 row"""
    dims = api_row.get('dimensions') or {}
    mets = api_row.get('metrics') or {}

    stat_day = dims.get('stat_time_day', '')
    date_str = stat_day[:10] if stat_day else ''
    hour_str = ''
    if include_hour:
        stat_hour = dims.get('stat_time_hour', '')
        if stat_hour:
            date_str = stat_hour[:10]
            hour_str = stat_hour[11:13] if len(stat_hour) >= 13 else ''

    row = {
        '캠페인 이름': mets.get('campaign_name', ''),
        '광고 이름': mets.get('ad_name', ''),
        '광고 ID': str(dims.get('ad_id', '')),
        '일별': date_str,
        '통화': mets.get('currency', 'KRW'),
    }
    if include_age or include_audience:
        row['나이'] = dims.get('age', '')
    if include_audience:
        row['성별'] = dims.get('gender', '')
    if include_hour:
        row['시간'] = hour_str
    if include_province:
        row['province_id'] = str(dims.get('province_id', ''))
    for api_key, csv_key in METRIC_TO_CSV.items():
        row[csv_key] = mets.get(api_key, 0)
    return row


def merge_with_existing(new_df: pd.DataFrame, existing_path: str, columns: list) -> pd.DataFrame:
    """기존 CSV와 병합: new_df 의 일자는 덮어쓰기, 그 외는 유지."""
    path = Path(existing_path)
    if not path.exists():
        return new_df

    existing = pd.read_csv(path, encoding='utf-8-sig', dtype={'광고 ID': str})
    for col in columns:
        if col not in existing.columns:
            existing[col] = '' if col in ('캠페인 이름', '광고 이름', '나이', '통화') else 0
    existing = existing[columns]

    new_dates = set(new_df['일별'].unique())
    kept = existing[~existing['일별'].isin(new_dates)]

    merged = pd.concat([kept, new_df], ignore_index=True)
    sort_keys = ['일별', '광고 이름']
    if '나이' in columns:
        sort_keys.append('나이')
    merged = merged.sort_values(sort_keys).reset_index(drop=True)
    return merged


def backup_existing(path: str):
    """기존 CSV를 .bak_YYYYMMDD 로 백업 (당일 1회만)."""
    p = Path(path)
    if not p.exists():
        return
    stamp = datetime.now().strftime('%Y%m%d')
    bak = p.with_suffix(p.suffix + f'.bak_{stamp}')
    if not bak.exists():
        bak.write_bytes(p.read_bytes())
        print(f"[backup] {bak.name}")


def fetch_and_save(
    start_date: date,
    end_date: date,
    advertiser_id: str,
    access_token: str,
    output_path: str,
    include_age: bool = False,
    include_hour: bool = False,
    include_audience: bool = False,
    include_province: bool = False,
):
    dimensions = ['ad_id', 'stat_time_day']
    columns = CSV_COLUMNS
    report_type = 'BASIC'
    metrics = None
    label = '일별 × 광고'
    if include_province:
        dimensions = ['ad_id', 'stat_time_day', 'province_id']
        columns = CSV_COLUMNS_BY_PROVINCE
        report_type = 'AUDIENCE'
        audience_metrics = [
            'spend', 'impressions', 'clicks', 'ctr',
            'conversion', 'cost_per_conversion', 'conversion_rate',
            METRIC_LANDING, METRIC_REACH,
        ]
        metrics = audience_metrics + META_FIELDS
        label = '일별 × 광고 × 지역 (AUDIENCE)'
    elif include_audience:
        dimensions = ['ad_id', 'stat_time_day', 'age', 'gender']
        columns = CSV_COLUMNS_BY_AUDIENCE
        report_type = 'AUDIENCE'
        audience_metrics = [
            'spend', 'impressions', 'clicks', 'ctr',
            'conversion', 'cost_per_conversion', 'conversion_rate',
            METRIC_LANDING, METRIC_REACH,
        ]
        metrics = audience_metrics + META_FIELDS
        label = '일별 × 광고 × 나이 × 성별 (AUDIENCE)'
    elif include_age:
        dimensions = ['ad_id', 'stat_time_day', 'age']
        columns = CSV_COLUMNS_BY_AGE
        report_type = 'AUDIENCE'
        audience_metrics = [
            'spend', 'impressions', 'clicks', 'ctr',
            'conversion', 'cost_per_conversion', 'conversion_rate',
            METRIC_LANDING, METRIC_REACH,
        ]
        metrics = audience_metrics + META_FIELDS
        label = '일별 × 광고 × 나이대 (AUDIENCE)'
    elif include_hour:
        dimensions = ['ad_id', 'stat_time_hour']
        columns = CSV_COLUMNS_BY_HOUR
        label = '일별 × 광고 × 시간'

    print(f"[fetch] {label} 기간={start_date} ~ {end_date}")

    # 시간대 수집은 TikTok API 제약상 1일씩만 조회 가능
    all_rows = []
    if include_hour:
        cur = start_date
        while cur <= end_date:
            day_str = cur.strftime('%Y-%m-%d')
            try:
                rows = fetch_report(
                    day_str, day_str, advertiser_id, access_token,
                    dimensions=dimensions, report_type=report_type, metrics=metrics,
                )
                print(f"[fetch]   {day_str} - {len(rows)}건")
                all_rows.extend(rows)
            except Exception as e:
                print(f"[fetch]   {day_str} 실패: {e}")
            cur += timedelta(days=1)
    else:
        all_rows = fetch_report(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            advertiser_id, access_token,
            dimensions=dimensions, report_type=report_type, metrics=metrics,
        )
    print(f"[fetch] API 응답 총 {len(all_rows)}개 레코드")

    if not all_rows:
        print("[fetch] 수신 데이터 없음 - 기존 CSV 유지")
        return

    new_df = pd.DataFrame([
        api_row_to_csv_row(r, include_age=include_age, include_hour=include_hour, include_audience=include_audience, include_province=include_province) for r in all_rows
    ])
    for col in columns:
        if col not in new_df.columns:
            new_df[col] = 0
    new_df = new_df[columns]

    backup_existing(output_path)
    merged = merge_with_existing(new_df, output_path, columns)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"[fetch] 저장 완료 -> {output_path} ({len(merged)}행)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=14, help='최근 N일 (기본 14)')
    parser.add_argument('--start', default=None, help='YYYY-MM-DD (--days 무시)')
    parser.add_argument('--end', default=None, help='YYYY-MM-DD (기본: 오늘)')
    parser.add_argument('--output', default='input/tiktok_raw.csv')
    parser.add_argument('--age-output', default='input/tiktok_raw_by_age.csv')
    parser.add_argument('--hour-output', default='input/tiktok_raw_by_hour.csv')
    parser.add_argument('--audience-output', default='input/tiktok_raw_by_audience.csv')
    parser.add_argument('--province-output', default='input/tiktok_raw_by_province.csv')
    parser.add_argument('--include-age', action='store_true', help='나이대 breakdown도 함께 수집')
    parser.add_argument('--only-age', action='store_true', help='나이대 수집만 실행')
    parser.add_argument('--include-hour', action='store_true', help='시간대 breakdown도 함께 수집')
    parser.add_argument('--only-hour', action='store_true', help='시간대 수집만 실행')
    parser.add_argument('--include-audience', action='store_true', help='나이+성별 breakdown 수집')
    parser.add_argument('--only-audience', action='store_true', help='오디언스(나이+성별) 수집만 실행')
    parser.add_argument('--include-province', action='store_true', help='지역(province_id) breakdown 수집')
    parser.add_argument('--only-province', action='store_true', help='지역 수집만 실행')
    args = parser.parse_args()

    access_token = require('TIKTOK_ACCESS_TOKEN', TIKTOK_ACCESS_TOKEN)
    advertiser_id = require('TIKTOK_ADVERTISER_ID', TIKTOK_ADVERTISER_ID)

    end_date = (
        datetime.strptime(args.end, '%Y-%m-%d').date()
        if args.end else date.today()
    )
    if args.start:
        start_date = datetime.strptime(args.start, '%Y-%m-%d').date()
    else:
        start_date = end_date - timedelta(days=args.days - 1)

    only_any = args.only_age or args.only_hour or args.only_audience or args.only_province
    if not only_any:
        fetch_and_save(start_date, end_date, advertiser_id, access_token, args.output)

    if args.include_age or args.only_age:
        fetch_and_save(start_date, end_date, advertiser_id, access_token, args.age_output, include_age=True)

    if args.include_hour or args.only_hour:
        fetch_and_save(start_date, end_date, advertiser_id, access_token, args.hour_output, include_hour=True)

    if args.include_audience or args.only_audience:
        fetch_and_save(start_date, end_date, advertiser_id, access_token, args.audience_output, include_audience=True)

    if args.include_province or args.only_province:
        fetch_and_save(start_date, end_date, advertiser_id, access_token, args.province_output, include_province=True)


if __name__ == '__main__':
    main()
