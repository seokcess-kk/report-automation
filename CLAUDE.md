# TikTok 광고 분석 파이프라인 — CLAUDE.md

> Claude Code 전달용 프로젝트 기억 문서
> 클라이언트: 다이트한의원
> 목표: 상담 전환 (소재 중심 분석)
> 버전: 3.0.0 (완전 자동화)

---

## 핵심 철학

**"AI에게 추측하게 하지 말고, 명시적으로 알려줘라."**

| # | 원인 | 증상 | 해법 |
|---|------|------|------|
| 1 | 방향 부재 | 엉뚱한 기능 구현 | **SDD — 주문서(Spec) 먼저 작성** |
| 2 | 프로젝트 맥락 부족 | 잘못된 패턴/경로 추측 | **DDD — 비즈니스 언어 = 코드명** |
| 3 | 지침 무시 (금붕어 기억력) | 매뉴얼 안 읽음, 앞부분 망각 | **훅 시스템 — 자동 매뉴얼 활성화** |
| 4 | 검증 부재 | 깨진 코드 방치 | **자동 QC — 완료 후 즉시 검사** |

> "AI는 그냥 쓰면 50점짜리 도구이지만, 시스템을 만들어 주면 95점짜리 에이스가 된다."

---

## 디렉토리 구조

```
project/
├── CLAUDE.md                         ← 이 파일 (프로젝트 기억)
├── input/
│   └── tiktok_raw.csv                ← TikTok 원본 CSV (필수)
├── output/
│   └── YYYYMMDD/                     ← 날짜별 출력
│       ├── tiktok_analysis_YYYYMMDD.xlsx
│       ├── tiktok_summary_YYYYMMDD.pdf
│       ├── tiktok_monthly_dayt_YYYYMM.html
│       ├── tiktok_weekly_dayt_YYYYMMDD.html
│       ├── tiktok_daily_YYYYMMDD.md
│       └── improvement_suggestions.md
├── .claude/
│   ├── settings.json                 ← 훅 설정
│   ├── skills/
│   │   ├── skill-rules.json          ← 자동 활성화 규칙
│   │   ├── creative-analyzer/
│   │   ├── report-generator/
│   │   └── tiktok-parser/
│   ├── agents/
│   │   ├── planner.md
│   │   ├── analysis-agent.md
│   │   ├── hook-agent.md
│   │   ├── insight-agent.md
│   │   ├── anomaly-agent.md
│   │   └── qa-agent.md
│   └── hooks/
├── dev/active/                       ← 외부 기억 장치 (작업별)
│   └── [task]/
│       ├── [task]-plan.md
│       ├── [task]-context.md
│       └── [task]-tasks.md
└── logs/
    └── parse_failures.csv
```

---

## 워크플로우 (7-Phase 파이프라인)

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

### Phase 0 - 원본 정규화

```
tiktok-normalizer 스킬:
  - normalize_tiktok_raw.py -> output/normalized.parquet
  - Ad ID 문자열 변환 (지수 표기 방지)
  - 컬럼명 표준화
  - KPI 재계산: CTR_calc / CVR_calc / CPA_calc / LPV_rate_calc
  - 귀속 주의 플래그 (클릭=0 AND 전환>0)
```

### Phase 1 - 데이터 준비

```
tiktok-parser 스킬:
  - 광고명 파싱 (소재구분/지점/소재유형/소재명/날짜코드)
  - parse_status = OK / FAIL
  - FAIL 소재 -> logs/parse_failures.csv (분석 제외)
  - 매칭 키 생성 (소재유형_소재명)
```

### Phase 2 - 병렬 분석

```
서브에이전트 병렬 실행:
  - analysis-agent: 소재 집계 + TIER 분류 + 지점 상대평가
  - hook-agent: 신규 vs 재가공 훅 비교 (creative_lineage.csv 지원)
  - anomaly-agent: 이상치 감지
  - funnel-agent: 퍼널 분석 (db_by_branch.csv 있을 때)
```

### Phase 3 - 인사이트 생성

```
insight-agent:
  - 형식: 수치 근거 -> 해석 -> 액션 제안
  - 등급: 확정 인사이트 (표본 충분) / 가설 인사이트 (표본 부족)
  - improvement_suggestions.md 자동 생성
```

### Phase 4 - QA 검증

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

### Phase 5 - 리포트 생성

```
report-generator 스킬:
  - Excel (7개 시트) -> output/YYYYMMDD/tiktok_analysis_YYYYMMDD.xlsx
  - PDF (2페이지) -> output/YYYYMMDD/tiktok_summary_YYYYMMDD.pdf
  - HTML 3종 (데일리/위클리/먼슬리)
  - improvement_suggestions.md -> output/YYYYMMDD/
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

**위클리 기준 차이**: 집행일수 < 3일 = UNCLASSIFIED, 클릭 < 50 AND 비용 < 50,000원 = LOW_VOLUME

---

## 3종 리포트 시스템

| 리포트 | 파일 | 발행 주기 | 수신자 |
|--------|------|----------|--------|
| 데일리 | `tiktok_daily_YYYYMMDD.md` | 매일 아침 | 내부 (쏭) |
| 위클리 | `tiktok_weekly_dayt_YYYYMMDD.html` | 매주 월요일 | 클라이언트 |
| 먼슬리 | `tiktok_monthly_dayt_YYYYMM.html` | 익월 1~3일 | 클라이언트 + 의사결정자 |

### 데일리 리포트 (Markdown)

```markdown
📊 [MM/DD] 다이트한의원 TikTok 전일 성과

📌 전체
• 전환: XX건 (전일 대비 ±XX건)
• CPA: XX,XXX원 (전일 대비 ±X,XXX원)
• CTR: X.XX% (전일 대비 ±X.XX%p)

🏢 지점별
• 서울: CPA XX,XXX원 (±XX원) | CTR X.XX% (±X.XXp)
[... 각 지점 1줄]

⚠️ 이상 감지
• [지점] [소재명] — CPA X.Xx배 (지점 평균 대비), OFF 검토 권고
• (없으면 "이상 없음")
```

**이상 감지 기준**: CPA가 지점 평균의 2배 이상 AND 비용 ≥ 지점평균CPA × 2

### 데일리 스냅샷 관리

```
경로: output/daily_snapshot.json
구조: {"YYYY-MM-DD": {"total": {...}, "branch": {...}}}
```

- 매일 실행 후 **전일 데이터를 스냅샷에 저장**
- 전일 대비 계산 = 오늘 데이터 - `snapshot[어제 날짜]`
- 스냅샷 없으면 전일 대비 항목은 **"N/A"** 표시
- 스냅샷은 최근 30일분만 유지 (오래된 것 자동 삭제)

### 위클리 리포트 (HTML 단일 스크롤)

> **⚠️ TIER 기준 (위클리 전용)**
> - 해당 주 7일 데이터만 사용 (월간 누적 아님)
> - **LOW_VOLUME**: 클릭 < 50 AND 비용 < 50,000원
> - **UNCLASSIFIED**: 집행일수 < 3일

**섹션 구성**:
1. 헤더 — 분석기간, 비교기간, 발행일
2. 이번 주 KPI — 전주 대비 (광고비, 전환, CPA, CTR, CVR)
3. 핵심 인사이트 — 변화 원인 분석
4. 소재 TIER 현황 — 이번 주 TIER + 전주 대비 변동
5. 지점별 성과 — CPA/CTR/CVR 전주 대비 차트 + 테이블
6. 예산 페이스 — 지점별 소진율 vs 기간 경과율
7. 소재 ON/OFF 액션플랜 — OFF 권고 / ON 권고
8. 이번 달 전환 목표 달성 예상

### 먼슬리 리포트 (HTML 7탭)

**7탭 구조**:
1. **월간 요약** — KPI 카드 6개, TIER 분포 도넛, 지점별 CPA 바차트
2. **소재 TIER** — 버블차트, ON 소재 테이블, **OFF 소재 성과**, **OFF 전후 CPA 참고**
3. **지점 분석** — CPA/효율 차트, 소재×지점 CPA 편차, 지점×나이대 히트맵
4. **나이대 분석** — 비용비중 vs 전환비중, 소재유형×나이대 히트맵
5. **소재 수명** — 신규 vs 재가공 비교, 집행일수별 CTR 추이
6. **일별 트렌드** — 광고비+전환수 콤보차트, CTR/CPA 추이
7. **다음 달 전략** — 예산 배분 권고, 신규 소재 기획 방향

---

## OFF 소재 처리 원칙

### 판별 방식

```python
df['is_off'] = df['ad_name'].str.lower().str.endswith('_off')
df_on  = df[~df['is_off']]   # KPI·TIER 계산에 사용
df_off = df[df['is_off']]    # OFF 분석 섹션에만 사용
```

### 원칙

- OFF 소재는 **KPI/TIER 계산 전체에서 제외**
- OFF 소재명: `_off` 접미사만 제거, 나머지 원본 유지
- OFF 소재는 별도 `off_perf` + `before_after` 섹션에만 표시

### before_after 분석 스키마

OFF 소재별 OFF 전후 지점 CPA 참고 분석.
**⚠️ 인과관계 아님** — 지점 전체 CPA이며 복합 요인 반영.

```json
{
  "creative_name": "광고명 원본(_off 제외)",
  "branch": "지점명",
  "off_date": "MM/DD",
  "before_cpa": int, "before_days": int,
  "after_cpa": int,  "after_days": int,
  "cpa_change_pct": float,
  "share_pct": float,
  "impact_level": "high|mid|low",
  "reliability": "high|mid|low|no_after"
}
```

**점유율 기준**: ≥20% → high, ≥8% → mid, <8% → low

**신뢰도 기준**:
- `after_days == 0` → `no_after`
- `after_days ≤ 2` → `low`
- `after_days ≤ 5` → `mid`
- `after_days > 5` → `high`

---

## 데이터 파싱 규칙

### CSV 컬럼명 매핑

```python
df = df.rename(columns={
    '클릭수(목적지)': 'clicks',
    '노출수': 'impressions',
    '전환수': 'conversions',
    '비용': 'cost',
    '랜딩 페이지 조회(웹사이트)': 'landing_views',
    '일별': 'date',
    '나이': 'age_group',
    '광고 이름': 'ad_name',
})
```

### 광고명 파싱

```python
BRANCHES = ['서울', '일산', '대구', '천안', '부평', '수원', '창원']
CTYPES   = ['인플방문후기', '의료진정보', '진료셀프캠']

def parse_ad(name):
    branch = next((b for b in BRANCHES if b in name), None)
    ctype  = next((t for t in CTYPES  if t in name), '기타')
    hook   = '재가공' if name.startswith('(재)') else ('신규' if name.startswith('(신)') else '일반')
    return branch, ctype, hook
```

### 소재명(creative_name)

- 광고 이름(`ad_name`) 원본을 그대로 사용
- OFF 소재: `_off` 접미사만 제거
  ```python
  re.sub(r'_off\s*$', '', name, flags=re.IGNORECASE)
  ```

---

## 디자인 레퍼런스

HTML 리포트 생성 시 **반드시 아래 파일을 먼저 읽고** 디자인 시스템 통일:

```
레퍼런스: output/tiktok_monthly_dayt_202602.html ← 확정된 디자인 기준
```

- 위클리/데일리는 이 파일과 **같은 시리즈처럼 보여야 함**
- CSS 변수, 폰트, 차트 설정을 **그대로 따를 것**
- 새 리포트 빌더 작성 시 먼슬리 HTML 구조를 참고

---

## 디자인 시스템

### CSS 변수

```css
:root {
  --bg: #0b0d12;
  --s1: #11141c;
  --s2: #171b25;
  --bd: #1c2030;
  --acc: #4ade80;    /* 성공/좋음/TIER1 */
  --blue: #60a5fa;   /* 정보/TIER2 */
  --pur: #a78bfa;    /* TIER3 */
  --warn: #fb923c;   /* 경고/OFF */
  --red: #f87171;    /* 위험/TIER4 */
  --tx: #dde4f0;
  --tx2: #7a8499;
  --tx3: #2e3648;
}
```

### TIER 색상

```javascript
const TC = {
  TIER1: '#4ade80',
  TIER2: '#60a5fa',
  TIER3: '#a78bfa',
  TIER4: '#f87171',
  LOW_VOLUME: '#6b7280',
  UNCLASSIFIED: '#8b5cf6',
};
```

### 폰트

- 본문: `Noto Sans KR` (Google Fonts CDN)
- 숫자: `DM Mono` (Google Fonts CDN)

### Chart.js 공통 설정 (4.4.x)

```javascript
const ax = { grid: { color: 'rgba(255,255,255,.04)' }, ticks: { color: '#2e3648', font: { size: 10 } } };
const tt = { backgroundColor: '#11141c', titleColor: '#dde4f0', bodyColor: '#7a8499', borderColor: '#1c2030', borderWidth: 1 };
```

---

## 입력 파일 형식

### tiktok_raw.csv (필수)

TikTok 광고 관리자 내보내기 컬럼:
- Ad Name, Ad ID, Date, Age, Cost, Impressions, Clicks, Conversions 등

### target_cpa.csv (선택)

```csv
지점,목표CPA
서울,20000
일산,20000
...
```

### db_by_branch.csv (선택)

```csv
지점,날짜,매체DB,실제DB,내원율,ROAS
서울,2026-02-01,50,40,30,150
...
```

### creative_lineage.csv (선택 - Phase 3)

```csv
creative_group_id,원본소재명,재가공소재명,변경요소,비고
GROUP_001,주사형비만치료제 10년은,체지방만쏙빼는(부산잇츠),썸네일+초기카피,2월 재가공
...
```

---

## 스킬 정의

### tiktok-normalizer

```yaml
name: tiktok-normalizer
description: TikTok 원본 CSV를 분석 가능한 형식으로 변환
triggers: tiktok csv 업로드, 분석 시작, 정규화
```

### tiktok-parser

```yaml
name: tiktok-parser
description: 광고명에서 지점/소재유형/훅 정보 파싱
triggers: 파싱, 광고명 분석, 지점 추출
```

### creative-analyzer

```yaml
name: creative-analyzer
description: CTR/CVR/CPA/랜딩률 복합 지표로 소재 평가, TIER1~4/LOW_VOLUME/UNCLASSIFIED 분류
triggers: 소재 분석, TIER 분류, 효율 좋은 소재
```

### hook-comparison

```yaml
name: hook-comparison
description: 신규 vs 재가공 소재 비교로 훅 효과 측정
triggers: 훅 비교, A/B 테스트, 재가공 효과
```

### funnel-analyzer

```yaml
name: funnel-analyzer
description: 매체DB -> 실제DB -> 내원 전환 퍼널 분석
triggers: 퍼널 분석, 내부 DB, 지점별 전환율
```

### insight-writer

```yaml
name: insight-writer
description: 분석 결과 기반 AI 인사이트 생성
triggers: 인사이트 생성, 액션 플랜, 개선 제안
```

### report-generator

```yaml
name: report-generator
description: Excel/PDF/HTML 리포트 생성
triggers: 리포트, 보고서, 엑셀, PDF, HTML
```

---

## 에이전트 정의

| 에이전트 | 역할 |
|---------|------|
| **planner** | Spec 기반 구현 계획 수립 (코드 작성 금지) |
| **plan-reviewer** | 계획 검증 및 리뷰 |
| **analysis-agent** | 소재 집계 + TIER 분류 + 지점 상대평가 |
| **hook-agent** | 신규 vs 재가공 훅 비교 |
| **insight-agent** | 수치 근거 → 해석 → 액션 제안 |
| **anomaly-agent** | 이상치 감지 |
| **qa-agent** | QA 체크리스트 검증 |
| **bug-resolver** | 빌드/런타임 에러 자동 해결 |

---

## 외부 기억 장치 (3대 문서)

새 작업 시작 전: `dev/active/[task]/` 폴더 확인

```
dev/active/[task]/
├── [task]-plan.md      ← 전략 & 아키텍처
├── [task]-context.md   ← 결정 이유, 관련 자료 위치
└── [task]-tasks.md     ← 진행 체크리스트 (실시간 업데이트)
```

### 운영 원칙

| 원칙 | 설명 |
|------|------|
| **선 문서화, 후 코딩** | Spec 승인 → 문서 저장 → 코딩 시작 |
| **마이크로 매니지먼트** | Phase별 순차 진행 |
| **중간 체크** | Phase 완료 시마다 확인 |
| **맥락 복구** | 새 대화 시작 시 `dev/active/[task]/` 문서 먼저 읽기 |

---

## 스킬 자동 활성화

`skill-rules.json` 위치: `.claude/skills/skill-rules.json`

| 작업 유형 | 자동 참조 스킬 |
|----------|---------------|
| CTR/TIER/소재 관련 | creative-analyzer |
| Excel/PDF/차트 관련 | report-generator |
| 데일리/스냅샷 관련 | daily-monitor |
| 수치 하드코딩 감지 | data-integrity-guardrail (block) |

### 활성화 조건 (4대)

| # | 조건 | 예시 |
|---|------|------|
| 1 | 키워드 | "TIER", "소재", "CPA" |
| 2 | 의도 패턴 | "(분석\|analyze).*?(소재\|creative)" |
| 3 | 작업 위치 | `skills/**/*.py` |
| 4 | 파일 내 패턴 | `import pandas`, `def calculate_tier` |

---

## 흔한 실수 경고

⚠️ **경로 변경됨**
- `skills/` → `.claude/skills/`
- `agents/` → `.claude/agents/`

⚠️ **훅 판정 방향**
- CTR 양수 = "부분 효과" 또는 "재가공 유효"
- CTR 음수만 "재가공 효과 없음"
- (방향 역전 버그 수정됨)

⚠️ **PDF 한글 폰트**
- `TTFont('NanumGothic', 경로)` 명시 필수
- 테이블에도 폰트 적용 필요

⚠️ **_calc 컬럼만 사용**
- raw CTR/CVR/CPA 컬럼 직접 사용 금지
- `CTR_calc`, `CVR_calc`, `CPA_calc`, `LPV_rate_calc` 사용

⚠️ **NaN 처리**
- 전환=0인 경우 CPA=None (0 아님)
- JSON 직렬화 시 `clean()` 함수 사용

---

## 지점별 월 예산

```python
BUDGET = {
    '서울':  2_800_000,
    '일산':  1_007_617,
    '대구':  2_500_000,
    '천안':  2_000_000,
    '부평':  4_000_000,
    '창원':  2_000_000,
    '수원':  3_000_000,
}
MONTHLY_TARGET_CONV = 600  # 전체 지점 합산 월 목표 전환
```

---

## 실행 방법

```bash
# 전체 파이프라인 실행
python run_analysis.py

# 먼슬리 리포트 생성
python pipeline/build_monthly.py --csv input/tiktok_raw.csv --month 202602

# 위클리 리포트 생성
python pipeline/build_weekly.py --csv input/tiktok_raw.csv --week 20260224

# 데일리 리포트 생성
python pipeline/build_daily.py --csv input/tiktok_raw.csv
```

---

## 자동 업데이트 정책

- **파서 패턴 오류**: 자동 업데이트 허용
- **분석 로직 변경**: `output/YYYYMMDD/improvement_suggestions.md`에만 저장

---

## QA 체크리스트

### 데이터 무결성

- [ ] raw total_cost = analysis total_cost (오차 ±1)
- [ ] raw total_conversions = analysis total_conversions
- [ ] CPA_calc = cost/conversions 검증

### TIER 분류

- [ ] TIER1~4에 <7일 또는 저볼륨 소재 없음
- [ ] OFF 소재 TIER 분석에서 제외됨
- [ ] LOW_VOLUME, UNCLASSIFIED 올바르게 분류됨

### 리포트 출력

- [ ] Excel 7개 시트 생성됨
- [ ] before_after.parquet 생성됨
- [ ] HTML 리포트 한글 깨짐 없음 (Noto Sans KR CDN 로드 확인)
- [ ] OFF 소재가 TIER 테이블에 미포함

---

## 참고: 클린 함수 (JSON 직렬화)

```python
import numpy as np
import pandas as pd

def clean(obj):
    if isinstance(obj, dict):   return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, list):   return [clean(v) for v in obj]
    if isinstance(obj, float) and np.isnan(obj): return None
    if isinstance(obj, np.integer):  return int(obj)
    if isinstance(obj, np.floating): return None if np.isnan(obj) else float(obj)
    if isinstance(obj, pd.Timestamp): return obj.strftime('%Y-%m-%d')
    return obj
```

---

## 변경 이력

| 버전 | 날짜 | 주요 변경 |
|------|------|----------|
| v1.0 | 2026-02-23 | 초기 버전 |
| v2.0 | 2026-02-24 | SDD 통합, 외부 기억 장치 의무화, 스킬 자동 활성화 |
| v3.0 | 2026-02-27 | 3개 문서 통합 (ai-collaboration-direction + tiktok-pipeline-spec + CLAUDE.md) |
| v3.1 | 2026-02-27 | 위클리 TIER 기준 명시, 데일리 스냅샷 로직 추가, 디자인 레퍼런스 경로 추가 |

---

*"주문서(Spec) 없는 코딩은, 설계도 없는 건축과 같다."*

*실행: `python run_analysis.py`*
