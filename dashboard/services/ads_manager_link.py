"""TikTok Ads Manager Deep Link 생성 — 반자동 광고 제어 (Phase 5-B)

운영자가 추천 액션 카드의 [Ads Manager 열기] 버튼을 누르면
TikTok 광고 매니저의 해당 광고/광고그룹/캠페인 페이지로 새 탭에서 이동.
거기서 직접 변경 후 콘솔로 돌아와 [기록] 버튼으로 actions.jsonl에 남김.

URL 패턴 (TikTok Ads Manager 2024 기준):
  - 광고 단위:   /i18n/perf/ad?aadvid=<adv>&search_type=ad_id&search_value=<ad_id>
  - 광고 그룹:   /i18n/perf/adgroup?aadvid=<adv>&search_type=adgroup_id&search_value=<id>
  - 캠페인:     /i18n/perf/campaign?aadvid=<adv>&search_type=campaign_id&search_value=<id>
  - 메인:       /i18n/perf

URL 패턴이 변경 가능하므로 환경변수로 base URL 오버라이드 지원.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# .env 자동 로드
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / '.env')
except ImportError:
    pass

ADS_MANAGER_BASE = os.getenv('TIKTOK_ADS_MANAGER_BASE', 'https://ads.tiktok.com')
ADVERTISER_ID = os.getenv('TIKTOK_ADVERTISER_ID', '')


@lru_cache(maxsize=1)
def _load_ad_meta() -> pd.DataFrame:
    """tiktok_ad_meta.csv 캐시 로드."""
    p = PROJECT_ROOT / 'input' / 'tiktok_ad_meta.csv'
    if not p.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(p, dtype={'ad_id': str, 'campaign_id': str, 'adgroup_id': str}, encoding='utf-8-sig')
    except Exception:
        return pd.DataFrame()


def _find_ad(ad_id: Optional[str] = None, ad_name: Optional[str] = None) -> Optional[dict]:
    df = _load_ad_meta()
    if df.empty:
        return None
    if ad_id:
        m = df[df['ad_id'] == str(ad_id)]
    elif ad_name:
        # 소재명에 ad_name 포함된 경우 매칭 (부분 일치)
        m = df[df['ad_name'].astype(str).str.contains(ad_name, regex=False, na=False)]
    else:
        return None
    if m.empty:
        return None
    r = m.iloc[0]
    return {
        'ad_id': str(r.get('ad_id', '')),
        'ad_name': str(r.get('ad_name', '')),
        'adgroup_id': str(r.get('adgroup_id', '')),
        'adgroup_name': str(r.get('adgroup_name', '')),
        'campaign_id': str(r.get('campaign_id', '')),
        'campaign_name': str(r.get('campaign_name', '')),
    }


def _branch_adgroups(branch: str) -> list[dict]:
    """지점명으로 광고 그룹 목록 반환. 그룹명에 지점명 포함된 row 그룹화."""
    df = _load_ad_meta()
    if df.empty or not branch:
        return []
    m = df[df['adgroup_name'].astype(str).str.contains(branch, regex=False, na=False)]
    if m.empty:
        return []
    grouped = m.groupby('adgroup_id').first().reset_index()
    return [
        {
            'adgroup_id': str(r['adgroup_id']),
            'adgroup_name': str(r['adgroup_name']),
            'campaign_id': str(r.get('campaign_id', '')),
        }
        for _, r in grouped.iterrows()
    ]


def _build_url(perf_type: str, search_type: str, search_value: str) -> str:
    """공통 URL 빌더."""
    if not ADVERTISER_ID:
        return f'{ADS_MANAGER_BASE}/i18n/perf'
    return (
        f'{ADS_MANAGER_BASE}/i18n/perf/{perf_type}'
        f'?aadvid={ADVERTISER_ID}'
        f'&search_type={search_type}&search_value={search_value}'
    )


def url_for_ad(ad_id: str) -> str:
    return _build_url('ad', 'ad_id', ad_id)


def url_for_adgroup(adgroup_id: str) -> str:
    return _build_url('adgroup', 'adgroup_id', adgroup_id)


def url_for_campaign(campaign_id: str) -> str:
    return _build_url('campaign', 'campaign_id', campaign_id)


def url_for_main() -> str:
    if not ADVERTISER_ID:
        return f'{ADS_MANAGER_BASE}/i18n/perf'
    return f'{ADS_MANAGER_BASE}/i18n/perf?aadvid={ADVERTISER_ID}'


def url_for_recommendation(target_type: str, target_name: Optional[str]) -> Optional[dict]:
    """Recommendation의 target을 Ads Manager URL로 매핑.

    반환: { url, scope_label, hint }
      - url: 새 탭에서 열 URL
      - scope_label: "광고 단위 / 광고 그룹 / 캠페인 / 메인"
      - hint: 어떻게 찾으면 되는지 짧은 안내 (운영자용)
    """
    if not target_name:
        return {'url': url_for_main(), 'scope_label': '메인', 'hint': 'Ads Manager 메인에서 직접 광고를 찾아 변경'}

    if target_type == 'ad':
        # ad_name(소재명)으로 ad_meta에서 ad_id 매핑
        ad = _find_ad(ad_name=target_name)
        if ad and ad['ad_id']:
            return {
                'url': url_for_ad(ad['ad_id']),
                'scope_label': '광고 단위',
                'hint': f'광고 ID {ad["ad_id"]} · {ad["adgroup_name"] or ""}',
                'ad_id': ad['ad_id'], 'adgroup_id': ad['adgroup_id'],
            }
        # ad_meta에서 못 찾으면 그룹 검색으로 fallback
        return {
            'url': _build_url('ad', 'ad_name', target_name[:50]),
            'scope_label': '광고 단위',
            'hint': f'"{target_name}" 검색 결과에서 광고 선택',
        }

    if target_type == 'branch':
        # 지점명으로 해당 지점 광고 그룹들 찾기
        groups = _branch_adgroups(target_name)
        if groups:
            ids = ','.join(g['adgroup_id'] for g in groups[:5])
            return {
                'url': _build_url('adgroup', 'adgroup_id', ids),
                'scope_label': '광고 그룹 (지점)',
                'hint': f'{target_name} 지점 광고 그룹 {len(groups)}개',
                'adgroup_ids': [g['adgroup_id'] for g in groups],
            }
        return {
            'url': _build_url('adgroup', 'adgroup_name', target_name),
            'scope_label': '광고 그룹',
            'hint': f'"{target_name}" 검색 결과에서 그룹 선택',
        }

    # 그 외 — 메인 페이지
    return {'url': url_for_main(), 'scope_label': '메인', 'hint': '메인에서 직접 검색'}


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    print(f'[base] {ADS_MANAGER_BASE}')
    print(f'[advertiser_id] {ADVERTISER_ID or "<unset>"}')
    print()
    df = _load_ad_meta()
    print(f'[ad_meta rows] {len(df)}')
    print()
    # 천안 지점 광고그룹
    groups = _branch_adgroups('천안')
    print(f'[천안 광고그룹] {len(groups)}개')
    for g in groups[:3]:
        print(f'  {g["adgroup_id"]}: {g["adgroup_name"]}')
    print()
    # 추천 매핑 테스트
    r1 = url_for_recommendation('branch', '천안')
    print(f'[branch 천안] {r1}')
    r2 = url_for_recommendation('ad', '주사형비만치료제 고민끝에 50대부부 -32kg')
    print(f'[ad 주사형*] {r2}')
