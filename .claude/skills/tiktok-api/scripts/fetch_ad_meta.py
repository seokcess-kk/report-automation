"""TikTok Marketing API → input/tiktok_ad_meta.csv

전체 광고(ad)의 메타데이터를 /ad/get/ 으로 수집하여 애드온 적용 여부를 식별.

사용법:
    python .claude/skills/tiktok-api/scripts/fetch_ad_meta.py
    python .claude/skills/tiktok-api/scripts/fetch_ad_meta.py --output input/tiktok_ad_meta.csv

수집 필드 (TikTok Marketing API v1.3 /ad/get/ 지원 필드):
    ad_id, ad_name, campaign_id, campaign_name, adgroup_id,
    create_time, modify_time,
    creative_type, image_mode, ad_format, display_name,
    vertical_video_strategy,
    interactive_motion_id, card_id, end_card_cta, call_to_action_id,
    identity_id, identity_type,
    image_ids, video_id

식별 로직 (애드온 = 광고 본 영상 위에 얹는 인터랙티브 요소):
    is_addon = (interactive_motion_id != None/empty) OR
               (card_id != None/empty) OR
               (end_card_cta != None/empty)

필수 환경변수: TIKTOK_ACCESS_TOKEN, TIKTOK_ADVERTISER_ID
"""
import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import HOST, TIKTOK_ACCESS_TOKEN, TIKTOK_ADVERTISER_ID, require

AD_FIELDS = [
    'ad_id', 'ad_name', 'campaign_id', 'campaign_name', 'adgroup_id',
    'adgroup_name', 'create_time', 'modify_time',
    'creative_type', 'image_mode', 'ad_format', 'display_name',
    'vertical_video_strategy',
    'interactive_motion_id', 'card_id', 'end_card_cta', 'call_to_action_id',
    'identity_id', 'identity_type',
    'image_ids', 'video_id',
    'operation_status', 'secondary_status',
]

CSV_COLUMNS = [
    'ad_id', 'ad_name', 'campaign_id', 'campaign_name', 'adgroup_id',
    'adgroup_name', 'create_time', 'modify_time',
    'creative_type', 'image_mode', 'ad_format', 'display_name',
    'vertical_video_strategy',
    'interactive_motion_id', 'card_id', 'end_card_cta', 'call_to_action_id',
    'identity_id', 'identity_type',
    'image_ids', 'video_id',
    'operation_status', 'secondary_status',
    'is_addon', 'addon_kind',
]

MAX_RETRIES = 3
RETRY_BACKOFF_SEC = 5


def fetch_ads(advertiser_id: str, access_token: str, page_size: int = 1000) -> list:
    """/ad/get/ 페이지네이션 수집."""
    url = f'{HOST}/ad/get/'
    headers = {'Access-Token': access_token}

    all_rows = []
    page = 1

    while True:
        params = {
            'advertiser_id': advertiser_id,
            'fields': json.dumps(AD_FIELDS),
            'page': page,
            'page_size': page_size,
        }

        TOKEN_ERROR_CODES = {40100, 40104, 40105, 40107, 40109, 40113, 40114}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=60)
                if resp.status_code in (401, 403):
                    raise SystemExit(
                        f"[FATAL] HTTP {resp.status_code} — TIKTOK_ACCESS_TOKEN 만료 또는 권한 없음."
                    )
                resp.raise_for_status()
                payload = resp.json()
                code = payload.get('code')
                if code != 0:
                    msg = payload.get('message', '')
                    if code in TOKEN_ERROR_CODES:
                        raise SystemExit(
                            f"[FATAL] TikTok 토큰 만료/무효 (code={code} msg={msg})."
                        )
                    # 일부 필드가 계정에서 지원되지 않으면 fields 가 거부될 수 있음
                    if 'field' in msg.lower():
                        raise RuntimeError(
                            f"API error code={code} msg={msg}\n"
                            f"  -> 일부 fields 가 계정에서 지원되지 않습니다. "
                            f"AD_FIELDS 에서 문제 필드를 제거하세요."
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
        print(f"[fetch] page={page} rows={len(rows)} (누적 {len(all_rows)})")

        page_info = data.get('page_info') or {}
        total_page = page_info.get('total_page', 0)
        if page >= total_page or total_page == 0:
            break
        page += 1

    return all_rows


def _has_value(v) -> bool:
    """TikTok API는 미설정 필드를 '', 0, None 등으로 반환 — 모두 무시."""
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip() not in ('', '0')
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, (list, dict)):
        return bool(v)
    return bool(v)


def classify_addon(row: dict) -> tuple[bool, str]:
    """애드온 적용 여부와 종류 판정.

    Returns:
        (is_addon, addon_kind)
        addon_kind: 'interactive' | 'display_card' | 'end_card' | 'composite' | ''
    """
    kinds = []
    if _has_value(row.get('interactive_motion_id')):
        kinds.append('interactive')
    if _has_value(row.get('card_id')):
        kinds.append('display_card')
    if _has_value(row.get('end_card_cta')):
        kinds.append('end_card')

    if not kinds:
        return False, ''
    if len(kinds) > 1:
        return True, 'composite'
    return True, kinds[0]


def normalize_row(api_row: dict) -> dict:
    """API row → CSV row. 리스트 필드는 JSON 직렬화."""
    row = {}
    for col in AD_FIELDS:
        val = api_row.get(col)
        if isinstance(val, (list, dict)):
            row[col] = json.dumps(val, ensure_ascii=False) if val else ''
        else:
            row[col] = val if val is not None else ''
    is_addon, kind = classify_addon(api_row)
    row['is_addon'] = is_addon
    row['addon_kind'] = kind
    # ad_id 는 항상 문자열
    if row.get('ad_id') is not None:
        row['ad_id'] = str(row['ad_id'])
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='input/tiktok_ad_meta.csv')
    parser.add_argument('--page-size', type=int, default=1000)
    args = parser.parse_args()

    access_token = require('TIKTOK_ACCESS_TOKEN', TIKTOK_ACCESS_TOKEN)
    advertiser_id = require('TIKTOK_ADVERTISER_ID', TIKTOK_ADVERTISER_ID)

    print(f"[fetch] 광고 메타 수집 (advertiser_id={advertiser_id})")
    rows = fetch_ads(advertiser_id, access_token, page_size=args.page_size)
    print(f"[fetch] 총 {len(rows)}개 광고 메타 수신")

    if not rows:
        print("[fetch] 수신 데이터 없음")
        return

    df = pd.DataFrame([normalize_row(r) for r in rows])
    for col in CSV_COLUMNS:
        if col not in df.columns:
            df[col] = ''
    df = df[CSV_COLUMNS]

    addon_count = int(df['is_addon'].sum())
    print(f"[summary] 애드온 적용 광고: {addon_count} / {len(df)} ({addon_count/len(df)*100:.1f}%)")
    if addon_count > 0:
        kind_counts = df[df['is_addon']]['addon_kind'].value_counts()
        print(f"[summary] 종류별:\n{kind_counts.to_string()}")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"[save] {out_path} ({len(df)}행)")


if __name__ == '__main__':
    main()
