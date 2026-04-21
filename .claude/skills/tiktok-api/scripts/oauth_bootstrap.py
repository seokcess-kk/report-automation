"""TikTok Business API OAuth — 최초 1회 대화형 실행

사용법:
    python .claude/skills/tiktok-api/scripts/oauth_bootstrap.py

실행 전 .env 또는 환경변수에 TIKTOK_APP_ID, TIKTOK_APP_SECRET 설정.

단계:
1. 이 스크립트가 authorize URL을 출력
2. 브라우저에서 해당 URL 접속 → TikTok 계정 로그인 → 권한 승인
3. 리다이렉트 URL의 `auth_code=` 값 복사
4. 터미널에 붙여넣기 → access_token 출력
5. 출력된 TIKTOK_ACCESS_TOKEN, TIKTOK_ADVERTISER_ID를 GitHub Secrets 또는 .env에 저장
"""
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import HOST, TIKTOK_APP_ID, TIKTOK_APP_SECRET, require


def build_authorize_url(redirect_uri: str) -> str:
    return (
        'https://business-api.tiktok.com/portal/auth'
        f'?app_id={TIKTOK_APP_ID}&state=bootstrap&redirect_uri={redirect_uri}'
    )


def exchange_auth_code(auth_code: str) -> dict:
    resp = requests.post(
        f'{HOST}/oauth2/access_token/',
        json={
            'app_id': TIKTOK_APP_ID,
            'secret': TIKTOK_APP_SECRET,
            'auth_code': auth_code,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    require('TIKTOK_APP_ID', TIKTOK_APP_ID)
    require('TIKTOK_APP_SECRET', TIKTOK_APP_SECRET)

    redirect_uri = input(
        "앱 등록 시 설정한 redirect URI 입력 (예: https://localhost/callback): "
    ).strip()
    if not redirect_uri:
        print("redirect_uri 필수.")
        sys.exit(1)

    print("\n[1] 아래 URL을 브라우저에서 열어 인증하세요:\n")
    print(build_authorize_url(redirect_uri))
    print("\n[2] 인증 후 브라우저 주소창의 URL 중 'auth_code=...' 값만 복사.\n")

    auth_code = input("auth_code 입력: ").strip()
    if not auth_code:
        print("auth_code 필수.")
        sys.exit(1)

    result = exchange_auth_code(auth_code)
    print("\n=== API 응답 ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    data = result.get('data') or {}
    token = data.get('access_token')
    advertiser_ids = data.get('advertiser_ids') or []

    if not token:
        print("\n[X] access_token 발급 실패 — 응답 확인.")
        sys.exit(1)

    print("\n=== GitHub Secrets / .env 에 저장할 값 ===")
    print(f"TIKTOK_ACCESS_TOKEN={token}")
    if len(advertiser_ids) == 1:
        print(f"TIKTOK_ADVERTISER_ID={advertiser_ids[0]}")
    elif len(advertiser_ids) > 1:
        print(f"TIKTOK_ADVERTISER_ID=<다음 중 선택> {advertiser_ids}")
    else:
        print("TIKTOK_ADVERTISER_ID=<advertiser 조회 필요>")


if __name__ == '__main__':
    main()
