# 워크플로우 (7-Phase 파이프라인)

```
Phase 0: 원본 정규화 (순차)
    ↓
Phase 1: 데이터 준비 (순차)
    ↓
Phase 2: 병렬 분석 (서브에이전트)
    ↓
Phase 3: 인사이트 생성
    ↓
Phase 4: QA 검증 (순차)
    ↓
Phase 5: 리포트 생성 (순차)
    ↓
Phase 6: /insight 피드백 루프 (선택)
```

---

## Phase 0 - 원본 정규화

```
tiktok-normalizer 스킬:
  - normalize_tiktok_raw.py -> output/data/YYYYMMDD/normalized.parquet
  - Ad ID 문자열 변환 (지수 표기 방지)
  - 컬럼명 표준화
  - KPI 재계산: CTR_calc / CVR_calc / CPA_calc / LPV_rate_calc
  - 귀속 주의 플래그 (클릭=0 AND 전환>0)
```

---

## Phase 1 - 데이터 준비

```
tiktok-parser 스킬:
  - 광고명 파싱 (소재구분/지점/소재유형/소재명/날짜코드)
  - parse_status = OK / FAIL
  - FAIL 소재 -> logs/parse_failures.csv (분석 제외)
  - 매칭 키 생성 (소재유형_소재명)
```

---

## Phase 2 - 병렬 분석

```
서브에이전트 병렬 실행:
  - analysis-agent: 소재 집계 + TIER 분류 + 지점 상대평가
  - hook-agent: 신규 vs 재가공 훅 비교 (creative_lineage.csv 지원)
  - anomaly-agent: 이상치 감지
  - funnel-agent: 퍼널 분석 (db_by_branch.csv 있을 때)
```

---

## Phase 3 - 인사이트 생성

```
insight-agent:
  - 형식: 수치 근거 -> 해석 -> 액션 제안
  - 등급: 확정 인사이트 (표본 충분) / 가설 인사이트 (표본 부족)
  - improvement_suggestions.md 자동 생성
```

---

## Phase 4 - QA 검증

```
qa-agent 체크리스트:
  [ ] raw total_cost = analysis total_cost (오차 ±1)
  [ ] raw total_conversions = analysis total_conversions
  [ ] CPA_calc = cost/conversions 검증
  [ ] TIER1~4에 <7일 또는 저볼륨 소재 없음
  [ ] OFF 소재 TIER 분석에서 제외됨
  [ ] Excel 7개 시트 생성됨
  [ ] before_after.parquet 생성됨
  [ ] HTML 리포트 한글 깨짐 없음
```

---

## Phase 5 - 리포트 생성

```
report-generator 스킬:
  - Excel (7개 시트) -> output/data/YYYYMMDD/tiktok_analysis_YYYYMMDD.xlsx
  - PDF (2페이지) -> output/data/YYYYMMDD/tiktok_summary_YYYYMMDD.pdf
  - HTML 3종:
    - 데일리 -> output/daily/YYYYMMDD/tiktok_daily_YYYYMMDD.md
    - 위클리 -> output/weekly/YYYYMMDD/tiktok_weekly_dayt_YYYYMMDD.html
    - 먼슬리 -> output/monthly/YYYYMM/tiktok_monthly_dayt_YYYYMM.html
  - improvement_suggestions.md -> output/data/YYYYMMDD/
```
