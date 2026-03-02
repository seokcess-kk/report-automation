# TikTok 광고 분석 파이프라인 — CLAUDE.md

> 클라이언트: 다이트한의원 | 목표: 상담 전환 (소재 중심 분석) | v3.3.0

---

## 핵심 철학

**"AI에게 추측하게 하지 말고, 명시적으로 알려줘라."**

> "AI는 그냥 쓰면 50점짜리 도구이지만, 시스템을 만들어 주면 95점짜리 에이스가 된다."

---

## 디렉토리 구조

```
project/
├── CLAUDE.md                 ← 핵심 규칙 (이 파일)
├── docs/                     ← 상세 문서 (필요시 참조)
│   ├── pipeline-spec.md      ← 7-Phase 파이프라인 상세
│   ├── report-formats.md     ← 3종 리포트 포맷
│   ├── design-system.md      ← CSS/차트 설정
│   ├── data-spec.md          ← 입력 파일/파싱 규칙
│   ├── skills-agents.md      ← 스킬/에이전트 정의
│   └── qa-checklist.md       ← QA 체크리스트
├── input/tiktok_raw.csv      ← TikTok 원본 CSV (필수)
├── output/
│   ├── daily/YYYYMMDD/       ← 데일리 리포트 (.md)
│   ├── weekly/YYYYMMDD/      ← 위클리 리포트 (.html)
│   ├── monthly/YYYYMM/       ← 먼슬리 리포트 (.html)
│   ├── data/YYYYMMDD/        ← 분석 데이터 (.parquet)
│   └── _ref/                 ← 디자인 레퍼런스
└── .claude/skills/           ← 스킬 스크립트
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
BUDGET = {'서울': 2_800_000, '부평': 4_000_000, '수원': 3_000_000,
          '일산': 1_007_617, '대구': 2_500_000, '창원': 2_000_000, '천안': 2_000_000}
MONTHLY_TARGET_CONV = 600
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
| v3.4 | 2026-03-02 | 지점 순서 고정 (서울→부평→수원→일산→대구→창원→천안) |
| v3.3 | 2026-03-02 | CLAUDE.md 분리 (컨텍스트 최적화) |
| v3.2 | 2026-03-02 | output 폴더 구조 리팩토링 |

*실행: `python run_analysis.py`*
