"""TikTok API로 ad → adgroup → 지점 매핑 생성.

출력: output/data/YYYYMMDD/ad_mapping.json
구조:
{
  "updated": "ISO timestamp",
  "ads": { "<ad_id>": { "adgroup_id": "...", "adgroup_name": "...",
                        "campaign_id": "...", "지점": "..." } },
  "adgroups_by_branch": {
    "서울": [ { "adgroup_id": "...", "adgroup_name": "...",
                 "budget": 500000, "budget_mode": "BUDGET_MODE_DAY" } ],
    ...
  }
}

실행 전제: .env 의 TIKTOK_ACCESS_TOKEN, TIKTOK_ADVERTISER_ID

사용법:
    python .claude/skills/action-advisor/scripts/build_ad_mapping.py output/data/20260421
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import VALID_BRANCHES
from common.parsers import parse_branch

# config.py는 tiktok-api 스킬 소유 — 경로 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tiktok-api' / 'scripts'))
from config import HOST, TIKTOK_ACCESS_TOKEN, TIKTOK_ADVERTISER_ID, require

MAX_RETRIES = 3
RETRY_BACKOFF = 5


def _fetch_paged(endpoint: str, params: dict, token: str) -> list:
    """페이지네이션 공통 처리 — total_page 와 수신 행 수 양쪽 기준으로 종료."""
    url = f'{HOST}{endpoint}'
    headers = {'Access-Token': token}
    PAGE_SIZE = 500  # TikTok API 안전선 (1000 한계 대비 여유)
    TOKEN_ERROR_CODES = {40100, 40104, 40105, 40107, 40109, 40113, 40114}
    all_rows = []
    page = 1
    MAX_PAGES = 200  # 안전 상한 (10만건까지)
    while page <= MAX_PAGES:
        p = {**params, 'page': page, 'page_size': PAGE_SIZE}
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(url, headers=headers, params=p, timeout=60)
                if resp.status_code in (401, 403):
                    raise SystemExit(
                        f"[FATAL] {endpoint} HTTP {resp.status_code} — "
                        f"TIKTOK_ACCESS_TOKEN 만료/권한 없음. 재발급 필요."
                    )
                resp.raise_for_status()
                payload = resp.json()
                code = payload.get('code')
                if code != 0:
                    if code in TOKEN_ERROR_CODES:
                        raise SystemExit(f"[FATAL] 토큰 만료/무효 (code={code}). 갱신 필요.")
                    raise RuntimeError(f"{endpoint} code={code} msg={payload.get('message')}")
                break
            except SystemExit:
                raise
            except (requests.RequestException, RuntimeError) as e:
                if attempt == MAX_RETRIES:
                    raise
                print(f"[retry {attempt}/{MAX_RETRIES}] {e}")
                time.sleep(RETRY_BACKOFF * attempt)

        data = payload.get('data') or {}
        rows = data.get('list') or []
        all_rows.extend(rows)

        page_info = data.get('page_info') or {}
        total_page = page_info.get('total_page') or 0
        total_number = page_info.get('total_number') or 0

        # 종료 조건: (1) 수신 rows < page_size 이거나 (2) 누적 >= total_number 이거나 (3) page >= total_page
        if not rows or len(rows) < PAGE_SIZE:
            break
        if total_number and len(all_rows) >= total_number:
            break
        if total_page and page >= total_page:
            break
        page += 1

    if page >= MAX_PAGES:
        print(f"[WARNING] {endpoint}: 페이지 상한({MAX_PAGES}) 도달. 일부 데이터 누락 가능.")

    return all_rows


def fetch_ads(advertiser_id: str, token: str) -> list:
    """모든 ad 조회 (ad_id, adgroup_id, ad_name)."""
    params = {
        'advertiser_id': advertiser_id,
        'fields': json.dumps(['ad_id', 'adgroup_id', 'campaign_id', 'ad_name', 'operation_status']),
    }
    return _fetch_paged('/ad/get/', params, token)


def fetch_adgroups(advertiser_id: str, token: str) -> list:
    """모든 adgroup 조회."""
    params = {
        'advertiser_id': advertiser_id,
        'fields': json.dumps([
            'adgroup_id', 'adgroup_name', 'campaign_id', 'campaign_name',
            'budget', 'budget_mode', 'operation_status',
        ]),
    }
    return _fetch_paged('/adgroup/get/', params, token)


def build(advertiser_id: str, token: str) -> dict:
    print(f"[mapping] advertiser_id={advertiser_id}")

    adgroups = fetch_adgroups(advertiser_id, token)
    print(f"[mapping] adgroup {len(adgroups)}개")

    ads = fetch_ads(advertiser_id, token)
    print(f"[mapping] ad {len(ads)}개")

    # adgroup_id -> meta
    ag_meta = {}
    for ag in adgroups:
        aid = str(ag.get('adgroup_id', ''))
        if not aid:
            continue
        name = ag.get('adgroup_name', '')
        branch = parse_branch(name) or parse_branch(ag.get('campaign_name', ''))
        ag_meta[aid] = {
            'adgroup_id': aid,
            'adgroup_name': name,
            'campaign_id': str(ag.get('campaign_id', '')),
            'campaign_name': ag.get('campaign_name', ''),
            'budget': int(ag.get('budget') or 0),
            'budget_mode': ag.get('budget_mode', ''),
            'operation_status': ag.get('operation_status', ''),
            '지점': branch,
        }

    # ad_id -> adgroup mapping
    ads_map = {}
    for ad in ads:
        adid = str(ad.get('ad_id', ''))
        if not adid:
            continue
        agid = str(ad.get('adgroup_id', ''))
        ag = ag_meta.get(agid, {})
        ads_map[adid] = {
            'ad_id': adid,
            'ad_name': ad.get('ad_name', ''),
            'adgroup_id': agid,
            'adgroup_name': ag.get('adgroup_name', ''),
            'campaign_id': str(ad.get('campaign_id', '')),
            'operation_status': ad.get('operation_status', ''),
            '지점': ag.get('지점'),
        }

    # 지점별 adgroup
    by_branch = {b: [] for b in VALID_BRANCHES}
    for ag in ag_meta.values():
        b = ag.get('지점')
        if b in by_branch:
            by_branch[b].append(ag)

    # 지점별 정렬 (예산 큰 순)
    for b in by_branch:
        by_branch[b].sort(key=lambda x: -x.get('budget', 0))

    unmatched = sum(1 for ag in ag_meta.values() if not ag.get('지점'))
    if unmatched:
        print(f"[mapping] 지점 미매칭 adgroup {unmatched}개 (adgroup_name/campaign_name에 지점 키워드 없음)")

    return {
        'updated': datetime.now().isoformat(),
        'ads': ads_map,
        'adgroups_by_branch': by_branch,
    }


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else None
    if not data_dir:
        base = Path('output/data')
        data_dir = str(max(base.iterdir())) if base.exists() else None
    if not data_dir:
        print("[ERROR] data_dir 필요")
        sys.exit(1)

    token = require('TIKTOK_ACCESS_TOKEN', TIKTOK_ACCESS_TOKEN)
    advertiser_id = require('TIKTOK_ADVERTISER_ID', TIKTOK_ADVERTISER_ID)

    result = build(advertiser_id, token)
    out_path = os.path.join(data_dir, 'ad_mapping.json')
    os.makedirs(data_dir, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 요약
    total_ads = len(result['ads'])
    branches = {b: len(v) for b, v in result['adgroups_by_branch'].items() if v}
    print(f"[OK] {out_path}")
    print(f"  ads: {total_ads}, adgroups_by_branch: {branches}")


if __name__ == '__main__':
    main()
