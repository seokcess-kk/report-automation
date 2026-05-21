"""텔레그램 봇 일일 알림 워커

매일 03:30 (또는 운영자 트리거) 실행:
  python -m dashboard.workers.telegram_notifier               # 실제 발송
  python -m dashboard.workers.telegram_notifier --dry-run     # 출력만, 발송 안 함
  python -m dashboard.workers.telegram_notifier --today 2026-06-01  # 특정 날짜로

환경변수 (필수):
  TELEGRAM_BOT_TOKEN — BotFather에서 받은 token
  TELEGRAM_CHAT_ID   — 메시지 받을 chat·channel·user의 id

봇 설정 가이드:
  1. Telegram 앱에서 @BotFather에 /newbot 보내고 봇 생성 → token 받음
  2. 운영자 단톡방에 봇 초대 (필요 시 봇에게 메시지 보내고 chat_id 확인)
  3. .env에 두 값 추가, 또는 GitHub Actions secrets에 추가
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / '.claude' / 'skills'))

# .env 자동 로드 (있을 경우)
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / '.env')
except ImportError:
    pass

from dashboard.services.data_loader import load_bundle
from dashboard.services.notification_builder import build as build_message


TELEGRAM_API = 'https://api.telegram.org/bot{token}/sendMessage'


def send(token: str, chat_id: str, text: str, parse_mode: str = 'Markdown') -> dict:
    """Telegram Bot API sendMessage 호출."""
    url = TELEGRAM_API.format(token=token)
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
        'disable_web_page_preview': True,
    }
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='메시지 출력만, 발송 안 함')
    parser.add_argument('--today', default=None, help='기준 날짜 YYYY-MM-DD')
    args = parser.parse_args()

    today = date.today()
    if args.today:
        try:
            today = datetime.strptime(args.today, '%Y-%m-%d').date()
        except ValueError:
            print(f'[ERROR] --today 형식: YYYY-MM-DD')
            sys.exit(1)

    bundle = load_bundle()
    text = build_message(bundle, today=today)

    if args.dry_run:
        print('[DRY-RUN] 메시지 출력만 (발송 안 함)')
        print('=' * 60)
        print(text)
        print('=' * 60)
        return

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print('[ERROR] TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID 환경변수 없음')
        print('  → .env 파일에 추가하거나 export TELEGRAM_BOT_TOKEN=...')
        print('  → 또는 --dry-run 으로 메시지 출력만 확인')
        sys.exit(1)

    try:
        result = send(token, chat_id, text)
        if result.get('ok'):
            msg_id = result.get('result', {}).get('message_id')
            print(f'[OK] 메시지 발송 완료 (message_id={msg_id})')
        else:
            print(f'[FAIL] 응답: {result}')
            sys.exit(1)
    except requests.HTTPError as e:
        print(f'[FAIL] HTTP 오류: {e}')
        print(f'  응답: {e.response.text if e.response else "없음"}')
        sys.exit(1)
    except Exception as e:
        print(f'[FAIL] 예외: {e}')
        sys.exit(1)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    main()
