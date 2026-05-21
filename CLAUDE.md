# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# TikTok 광고 분석 파이프라인

> 클라이언트: 다이트한의원 | 목표: 상담 전환 (소재 중심 분석) | v3.10

---

## 아키텍처 개요

```
[0] fetch_tiktok_raw.py      → input/tiktok_raw.csv
                               (+ tiktok_raw_by_age.csv      ※ --include-age)
                               (+ tiktok_raw_by_audience.csv ※ --include-audience: age+gender)
                               (+ tiktok_raw_by_province.csv ※ --include-province: 광역 지역)
        ↓
[1] normalize_tiktok_raw.py  → output/data/YYYYMMDD/normalized*.parquet
        ↓
[2] parse_tiktok.py          → output/data/YYYYMMDD/parsed.parquet (광고명 파싱)
        ↓
[3] score_creatives.py       → output/data/YYYYMMDD/creative_tier.parquet (TIER 분류)
        ↓
[4] build_daily.py           → output/daily/YYYYMMDD/*.txt
    build_weekly.py          → output/weekly/YYYYMMDD/*.html
    build_monthly.py         → output/monthly/YYYYMM/*.html
    build_proposal.py        → output/proposal/YYYYMM/*.html  (월간 운영 제안서)
```

## 핵심 모듈 구조

```
.claude/skills/
├── common/                   ← 공용 모듈 (상수, 유틸리티)
│   ├── constants.py          ← VALID_BRANCHES, MONTHLY_BUDGET, VALID_AD_TYPES
│   ├── parsers.py            ← strip_date_code, load_target_cpa
│   ├── kpi.py                ← calc_kpi, calc_branch_kpi
│   ├── utils.py              ← clean, fmt, fmt_man, fmt_pct
│   └── logger.py             ← 에러 처리 유틸리티
├── tiktok-api/               ← Phase 0: TikTok Marketing API 수집
├── tiktok-normalizer/        ← CSV → Parquet 변환 + 지역/성별 코드 한글화
├── tiktok-parser/            ← 광고명 파싱 (소재구분, 지점, 소재유형 추출)
├── creative-analyzer/        ← TIER 분류, 훅 비교, 나이대 분석
├── report-generator/         ← 3종 리포트 생성 (daily/weekly/monthly)
├── proposal-builder/         ← 월간 운영 제안서 (5장 본문 + 부록 A·B·C)
│   ├── analyze_addon_effect.py    ← 애드온 v1/v2 디자인 분리 분석 (부산 제외)
│   ├── analyze_targeting_health.py ← 부록 A: 성별·연령 타겟팅 정합성
│   ├── analyze_geo_leakage.py      ← 부록 B: 지점-광역 노출 정합성
│   ├── build_creative_appendix.py  ← 부록 C: 지점×소재 KPI 재집계
│   ├── build_proposal.py           ← 통합 빌드
│   └── html_template.py / js_body.py ← 렌더링
└── insight-writer/           ← 인사이트 자동 생성
```

---

## 절대 규칙 (6대 금지)

1. **원본 CTR/CVR/CPA 컬럼 사용 금지** → `_calc` 재계산 값만 사용
2. **클릭=0 AND 전환>0일 때 행 단위 CVR 계산 금지**
3. **parse_status=FAIL 소재 TIER 분류 금지**
4. **저볼륨 소재 TIER 분류 금지** (클릭<100 AND 비용<100,000)
5. **지점 편중 소재 수치 보정 금지** → 주석 처리만
6. **행 단위 TIER 평가 금지** → 소재별 집계 후 TIER 부여

---

## TIER 분류 기준

**TARGET_CPA**: `target_cpa.csv` 우선, 없으면 `df_on` CPA 중앙값

| TIER | 조건 |
|------|------|
| **TIER1** | CPA ≤ TARGET_CPA AND CVR ≥ 5.0% |
| **TIER2** | CPA ≤ TARGET_CPA AND CVR < 5.0% AND 랜딩도달률 ≥ 50% |
| **TIER3** | CPA > TARGET_CPA AND CVR ≥ 5.0% |
| **TIER4** | 나머지 |
| **LOW_VOLUME** | 클릭 < 100 AND 비용 < 100,000원 |
| **UNCLASSIFIED** | 집행일수 < 7일 |

**위클리**: 집행일수 < 3일 = UNCLASSIFIED, 클릭 < 50 AND 비용 < 50,000원 = LOW_VOLUME

---

## OFF/ON 소재 처리 규칙

| 영역 | OFF 소재 (`_off` 접미사) | ON 소재 |
|------|-------------------------|---------|
| **KPI 계산** (비용/전환/CPA/CTR/CVR) | ✅ 포함 | ✅ 포함 |
| **지점별 요약** | ✅ 포함 | ✅ 포함 |
| **소재 TIER 분류** | ❌ 제외 | ✅ 분류 대상 |

> OFF 소재는 실제 집행되었으므로 KPI에 반영해야 하지만, 현재 라이브 상태가 아니므로 TIER 분석에서는 제외

---

## 데일리 스냅샷 시스템

```
output/daily/daily_snapshot.json
```

- 매일 데일리 리포트 생성 시 당일 KPI를 스냅샷에 저장
- 전일비 계산 시 스냅샷에서 전일 데이터 조회
- **Fallback**: 스냅샷에 전일 데이터 없으면 CSV에서 직접 계산

```python
# 전일비 계산 우선순위
1. daily_snapshot.json에서 전일 데이터 조회
2. 없으면 → CSV에서 전일 날짜 필터링 후 KPI 직접 계산
```

---

## 최초 로컬 세팅 (1회)

```bash
# 자동 생성 산출물 merge 충돌 방지 (GitHub Actions가 매일 커밋하므로 필수)
git config merge.ours.driver true
```

이후 `git pull` 시 output/ 파일 충돌은 로컬 버전으로 자동 유지됨.

---

## 실행 방법

```bash
# 전체 파이프라인 (분석 + 먼슬리) — 수동 CSV 사용
python run_analysis.py

# API로 수집 후 분석
python run_analysis.py --collect                       # 최근 14일
python run_analysis.py --collect --days 30
python run_analysis.py --collect --include-age         # 나이대 breakdown
python run_analysis.py --collect --start 2026-04-01 --end 2026-04-20

# Phase 0 디멘션 수집 (단독 실행) — 30일 윈도우 제한 있음
python .claude/skills/tiktok-api/scripts/fetch_tiktok_raw.py --days 14
python .claude/skills/tiktok-api/scripts/fetch_tiktok_raw.py --start 2026-03-01 --end 2026-03-30 --only-audience  # age+gender
python .claude/skills/tiktok-api/scripts/fetch_tiktok_raw.py --start 2026-03-01 --end 2026-03-30 --only-province  # 광역 지역

# 개별 리포트
python .claude/skills/report-generator/scripts/build_monthly.py output/data/YYYYMMDD 202603
python .claude/skills/report-generator/scripts/build_weekly.py input/tiktok_raw.csv output
python .claude/skills/report-generator/scripts/build_daily.py input/tiktok_raw.csv output
python .claude/skills/proposal-builder/scripts/build_proposal.py output/data/YYYYMMDD/parsed.parquet input/tiktok_ad_meta.csv output/proposal/YYYYMM
```

---

## 흔한 실수 경고

⚠️ **경로**: `skills/` → `.claude/skills/`

⚠️ **_calc 컬럼만 사용**: `CTR_calc`, `CVR_calc`, `CPA_calc`, `LPV_rate_calc`

⚠️ **NaN 처리**: 전환=0 → CPA=None, JSON 직렬화 시 `clean()` 사용

⚠️ **cross_gap 집계**: **절대 `ad_name` 기준 그룹화 금지** → `creative_name` 사용

⚠️ **디자인 레퍼런스**: 리포트 생성 전 `output/_ref/*.html` 먼저 확인

⚠️ **부록 C 정합성** (v3.10): `creative_tier`는 **소재 단위 누적 KPI**. 지점별 효율을 부록 C에 표시하려면 `parsed.parquet`에서 `(지점, 소재)` 단위로 **별도 재집계**해야 함. `build_creative_appendix._aggregate_branch_creative_kpi()` 참조 — TIER 부여는 소재 단위 그대로, KPI 수치만 지점별로 분리.

⚠️ **5월 부분월 부록 C fallback**: 5월처럼 ON 광고가 부족해 `creative_tier`가 0행이면 `_find_latest_creative_tier()`가 비어있지 않은 가장 최신 디렉토리로 자동 fallback. 데이터 출처는 `data_source_dir` 필드로 본문에 명시.

⚠️ **부산점 별도 처리** (5장 애드온 분석): 5월에 부산만 애드온 일부 미적용 + R10 학습 룰 대상이라 `analyze_addon_effect`에서 `EXCLUDE_BRANCHES = ['부산']`로 분리. 부산 학습 평가는 3.4 부산 학습 박스에서 별도 모니터링.

⚠️ **광고 표준 약어 유지**: 사용자 노출 영역에서 CPM/CTR/CVR/CPA/KPI/TIER/CTA/hero/LPV/v1/v2/p25~p100 등은 광고 업계 관행이므로 **한글화하지 않음**. 그 외 일반 영문 문구(Executive Summary, Stretch, Guardrail 등)는 한글로.

⚠️ **TikTok API 30일 윈도우**: `dimensions=['ad_id', 'stat_time_day', ...]` 사용 시 한 번에 최대 30일. 긴 기간 재수집은 30일 단위로 4단계 분할 필요.

⚠️ **province_id는 추정 메트릭**: TikTok reach·province는 추정·샘플링 성격. 부록 B(지역 도달)는 단정형이 아닌 **누수 진단형**으로만 사용. 본문 톤도 그렇게 유지.

---

## 지점 순서 (고정)

```python
VALID_BRANCHES = ['서울', '부평', '수원', '일산', '대구', '창원', '천안', '대전', '부산']
# 9개 지점. 부산은 R10 학습 룰 대상 — 정상 산식 미적용
```

## 지점별 월 예산

```python
# .claude/skills/common/constants.py 에서 import
from common import VALID_BRANCHES, MONTHLY_BUDGET, MONTHLY_TARGET_CONV

MONTHLY_BUDGET = {'서울': 2_000_000, '부평': 2_000_000, '수원': 2_000_000,
                  '일산': 2_000_000, '대구': 2_000_000, '창원': 2_000_000,
                  '천안': 2_000_000, '대전': 2_000_000, '부산': 2_000_000}
MONTHLY_TARGET_CONV = 891   # 지점별 합산 (2026-05 기준)
MONTHLY_TARGET_IMP = 1_675_675
MONTHLY_TARGET_CLICK = 11_646
```

---

## 공용 모듈 사용법

스크립트에서 공용 모듈 import:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common import (
    VALID_BRANCHES, MONTHLY_BUDGET, MONTHLY_TARGET_CONV,
    strip_date_code, load_target_cpa,
    calc_kpi, calc_branch_kpi,
    clean, fmt, fmt_man, fmt_pct,
)
```

---

## 상세 문서 참조

| 주제 | 파일 |
|------|------|
| 7-Phase 파이프라인 | `docs/pipeline-spec.md` |
| 3종 리포트 포맷 | `docs/report-formats.md` |
| CSS/차트/폰트 | `docs/design-system.md` |
| 입력 파일/파싱 | `docs/data-spec.md` |
| 스킬/에이전트 | `docs/skills-agents.md` |
| QA 체크리스트 | `docs/qa-checklist.md` |

---

| 버전 | 날짜 | 변경 |
|------|------|------|
| v3.10 | 2026-05-21 | API 디멘션 확장 (성별·지역·시청 깊이·인게이지먼트) + 6월 운영 제안서 재구성 (5장 본문 + 부록 A·B·C) + 부록 C 지점×소재 재집계 |
| v3.9 | 2026-04-21 | Phase 0 자동화 (`--collect`), 랜딩/도달/나이 컬럼 API 수집 추가 |
| v3.8 | 2026-03-09 | 위클리 KPI OFF 소재 포함, 데일리 전일비 fallback 로직 추가 |
| v3.7 | 2026-03-03 | 공용 모듈 생성 (.claude/skills/common/), 코드 품질 개선 |
| v3.6 | 2026-03-03 | 먼슬리 지점 분석 탭에 지점별 소재 분석 섹션 추가 |
| v3.5.1 | 2026-03-03 | 위클리 전환 목표 차트 개선 (이중 Y축, CPA 원 단위 표시) |
| v3.5 | 2026-03-03 | 위클리 리포트 먼슬리 기준 통일 (신규소재 섹션, 효율점수, 확장 기회 인사이트) |
| v3.4 | 2026-03-02 | 지점 순서 고정 (서울→부평→수원→일산→대구→창원→천안) |
| v3.3 | 2026-03-02 | CLAUDE.md 분리 (컨텍스트 최적화) |
| v3.2 | 2026-03-02 | output 폴더 구조 리팩토링 |

*실행: `python run_analysis.py`*
