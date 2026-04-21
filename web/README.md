# report-automation-web

Next.js UI for TikTok 리포트 대시보드.

## 개발

```bash
cd web
npm install
ACCESS_PASSWORD=dev npm run dev   # http://localhost:3000
```

## 배포 (Vercel)

Vercel 새 프로젝트 생성 시:
- **Root Directory**: `web`
- **Framework**: Next.js (자동 감지)
- **Build Command**: `npm run build` (기본)
- **Environment Variables**:
  - `ACCESS_PASSWORD` = 접속 비밀번호

## 데이터 소스

`../output/weekly/YYYYMMDD/*.json` 등을 빌드 타임에 `fs`로 읽음.
report-automation pipeline이 commit하면 Vercel이 자동 재배포 → 최신 리포트 반영.

## 현재 지원 (Phase 1)

- 홈: 최신 위클리 KPI + 인사이트
- 위클리 목록/상세: KPI, 인사이트, 월 목표, 일별 추이 차트, 지점 테이블(정렬), TIER 분류(필터)

## Phase 2 (예정)

먼슬리/데일리 페이지, 소재 드릴다운, 날짜 필터.
