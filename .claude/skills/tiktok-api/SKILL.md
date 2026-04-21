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
# 기본 14일 (일별 × 광고)
python .claude/skills/tiktok-api/scripts/fetch_tiktok_raw.py

# 기간 지정
python .claude/skills/tiktok-api/scripts/fetch_tiktok_raw.py --days 30
python .claude/skills/tiktok-api/scripts/fetch_tiktok_raw.py --start 2026-04-01 --end 2026-04-20

# 나이대 breakdown 함께 수집 (input/tiktok_raw_by_age.csv 별도 생성)
python .claude/skills/tiktok-api/scripts/fetch_tiktok_raw.py --include-age

# 나이대만
python .claude/skills/tiktok-api/scripts/fetch_tiktok_raw.py --only-age

# 파이프라인 통합 (수집 + 분석 + 리포트 한 번에)
python run_analysis.py --collect
python run_analysis.py --collect --include-age --days 30
```

## 수집 컬럼

### `input/tiktok_raw.csv` (일별 × 광고)

| 컬럼 | API 메트릭 |
|------|-----------|
| 캠페인 이름 / 광고 이름 / 광고 ID / 일별 / 통화 | meta |
| 비용, 노출수, CPM | spend / impressions / cpm |
| 클릭수(목적지), CPC(목적지), CTR(목적지) | clicks / cpc / ctr |
| 전환수, 전환당 비용, 전환율(CVR) | conversion / cost_per_conversion / conversion_rate |
| 빈도, 동영상 조회수 | frequency / video_play_actions |
| **랜딩 페이지 조회(웹사이트)** | `total_pageview` *(환경변수 오버라이드 가능)* |
| **도달** | `reach` |

### `input/tiktok_raw_by_age.csv` (일별 × 광고 × 나이대, `--include-age` 시)

동일 컬럼 + `나이` 디멘션 포함.

## 메트릭명 오버라이드

계정별로 API 메트릭 이름이 다를 수 있음. 첫 실행 시 `code=40002` 또는 `Invalid metric` 에러가 나면:

```bash
# .env 에 추가
TIKTOK_METRIC_LANDING=total_pageview        # 예: real_time_landing_page_view 대신
TIKTOK_METRIC_REACH=reach
```

참고: TikTok API 메트릭 전체 목록은 Developer Portal → Reporting → Supported Metrics 참고.

## 안전장치

- **자동 백업**: 덮어쓰기 전 `input/tiktok_raw.csv.bak_YYYYMMDD` 생성 (당일 최초 1회)
- **병합 모드**: 수집 기간만 덮어쓰고, 그 이전 날짜 데이터는 그대로 유지
- **재시도**: 일시적 API 오류 시 최대 3회 재시도 (지수 백오프)
- **수집 실패 시**: `run_analysis.py --collect`는 에러 로그 남기고 기존 CSV로 분석 계속 진행

## 출력

`input/tiktok_raw.csv` — 수동 Ads Manager export와 **동일한 스키마**로 저장.
기존 파일이 있으면 수집 기간만 덮어쓰고 그 이전 데이터는 그대로 유지.
