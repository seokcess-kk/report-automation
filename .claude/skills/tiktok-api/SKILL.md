# tiktok-api

TikTok Marketing API 연동 — 수동 CSV 다운로드를 자동화.

## 구조

```
scripts/
├── config.py             ← 환경변수 로더 (.env 또는 CI env)
├── oauth_bootstrap.py    ← 최초 1회 access_token 발급 (대화형)
└── fetch_tiktok_raw.py   ← 일일 자동 실행 (GitHub Actions)
```

## 최초 설정 (1회)

1. **TikTok for Business Developer Portal** 에서 앱 생성
2. 앱 redirect URI 설정 (예: `https://localhost/callback`)
3. 권한: **Reporting - Read** 스코프 포함
4. 로컬에서 `oauth_bootstrap.py` 실행 → 인증 → `access_token` 획득
5. 아래 4개를 GitHub Secrets (또는 로컬 `.env`) 에 저장:
   - `TIKTOK_APP_ID`
   - `TIKTOK_APP_SECRET`
   - `TIKTOK_ACCESS_TOKEN`
   - `TIKTOK_ADVERTISER_ID`

## 실행

```bash
# 로컬 테스트
python .claude/skills/tiktok-api/scripts/fetch_tiktok_raw.py --days 14

# CI (GitHub Actions) 에서는 .github/workflows/daily-report.yml 이 매일 자동 실행
```

## 출력

`input/tiktok_raw.csv` — 수동 Ads Manager export와 **동일한 스키마**로 저장.
기존 파일이 있으면 최근 N일(기본 14일) 데이터만 새로 덮어쓰고 그 이전 데이터는 그대로 유지.
