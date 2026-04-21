"""TikTok API 환경 설정 로더

환경변수 우선순위:
1. OS 환경변수 (GitHub Actions의 secrets)
2. 프로젝트 루트의 .env 파일 (로컬 개발용)
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    ROOT = Path(__file__).resolve().parents[4]
    load_dotenv(ROOT / '.env')
except ImportError:
    pass

HOST = 'https://business-api.tiktok.com/open_api/v1.3'

TIKTOK_APP_ID = os.getenv('TIKTOK_APP_ID')
TIKTOK_APP_SECRET = os.getenv('TIKTOK_APP_SECRET')
TIKTOK_ACCESS_TOKEN = os.getenv('TIKTOK_ACCESS_TOKEN')
TIKTOK_ADVERTISER_ID = os.getenv('TIKTOK_ADVERTISER_ID')


def require(name: str, val):
    if not val:
        raise RuntimeError(
            f"환경변수 {name} 누락. GitHub Secrets 또는 .env 파일에 설정 필요."
        )
    return val
