# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# TikTok 광고 분석 파이프라인

> 클라이언트: 다이트한의원 | 목표: 상담 전환 (소재 중심 분석) | v3.8

---

## 아키텍처 개요

```
input/tiktok_raw.csv
        ↓
[1] normalize_tiktok_raw.py  → output/normalized.parquet
        ↓
[2] parse_tiktok.py          → output/parsed.parquet (광고명 파싱)
        ↓
[3] score_creatives.py       → output/data/YYYYMMDD/creative_tier.parquet (TIER 분류)
        ↓
[4] build_daily.py           → output/daily/YYYYMMDD/*.txt
    build_weekly.py          → output/weekly/YYYYMMDD/*.html
    build_monthly.py         → output/monthly/YYYYMM/*.html
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
├── tiktok-normalizer/        ← CSV → Parquet 변환
├── tiktok-parser/            ← 광고명 파싱 (소재구분, 지점, 소재유형 추출)
├── creative-analyzer/        ← TIER 분류, 훅 비교, 나이대 분석
├── report-generator/         ← 3종 리포트 생성 (daily/weekly/monthly)
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

## 실행 방법

```bash
# 전체 파이프라인 (분석 + 먼슬리)
python run_analysis.py

# 개별 리포트
python .claude/skills/report-generator/scripts/build_monthly.py output/data/YYYYMMDD 202603
python .claude/skills/report-generator/scripts/build_weekly.py input/tiktok_raw.csv output
python .claude/skills/report-generator/scripts/build_daily.py input/tiktok_raw.csv output
```

---

## 흔한 실수 경고

⚠️ **경로**: `skills/` → `.claude/skills/`

⚠️ **_calc 컬럼만 사용**: `CTR_calc`, `CVR_calc`, `CPA_calc`, `LPV_rate_calc`

⚠️ **NaN 처리**: 전환=0 → CPA=None, JSON 직렬화 시 `clean()` 사용

⚠️ **cross_gap 집계**: **절대 `ad_name` 기준 그룹화 금지** → `creative_name` 사용

⚠️ **디자인 레퍼런스**: 리포트 생성 전 `output/_ref/*.html` 먼저 확인

---

## 지점 순서 (고정)

```python
VALID_BRANCHES = ['서울', '부평', '수원', '일산', '대구', '창원', '천안']
```

## 지점별 월 예산

```python
# .claude/skills/common/constants.py 에서 import
from common import VALID_BRANCHES, MONTHLY_BUDGET, MONTHLY_TARGET_CONV

MONTHLY_BUDGET = {'서울': 2_800_000, '부평': 4_000_000, '수원': 3_000_000,
                  '일산': 1_007_617, '대구': 2_500_000, '창원': 2_000_000, '천안': 2_000_000}
MONTHLY_TARGET_CONV = 600
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
| v3.8 | 2026-03-09 | 위클리 KPI OFF 소재 포함, 데일리 전일비 fallback 로직 추가 |
| v3.7 | 2026-03-03 | 공용 모듈 생성 (.claude/skills/common/), 코드 품질 개선 |
| v3.6 | 2026-03-03 | 먼슬리 지점 분석 탭에 지점별 소재 분석 섹션 추가 |
| v3.5.1 | 2026-03-03 | 위클리 전환 목표 차트 개선 (이중 Y축, CPA 원 단위 표시) |
| v3.5 | 2026-03-03 | 위클리 리포트 먼슬리 기준 통일 (신규소재 섹션, 효율점수, 확장 기회 인사이트) |
| v3.4 | 2026-03-02 | 지점 순서 고정 (서울→부평→수원→일산→대구→창원→천안) |
| v3.3 | 2026-03-02 | CLAUDE.md 분리 (컨텍스트 최적화) |
| v3.2 | 2026-03-02 | output 폴더 구조 리팩토링 |

*실행: `python run_analysis.py`*
