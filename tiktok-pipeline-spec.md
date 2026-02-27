# 다이트한의원 TikTok 광고 분석 파이프라인 — CLAUDE.md

> Claude Code 전달용 프로젝트 기억 문서  
> 작성일: 2026.02.27 | 상태: 먼슬리 리포트 확정, 데일리·위클리 통합 필요

---

## 프로젝트 개요

다이트한의원(한국 의료 다이어트 한의원 체인)의 TikTok 광고 성과를 분석하고  
**데일리 / 위클리 / 먼슬리** 3종 리포트를 자동 생성하는 Python 파이프라인.

**운영자**: 쏭 (광고 대행사 내부)  
**클라이언트**: 다이트한의원  
**데이터 소스**: TikTok Ads Manager에서 수동 다운로드한 CSV  

---

## 디렉토리 구조

```
project/
├── CLAUDE.md                     ← 이 파일
├── data/
│   └── tiktok_raw.csv            ← TikTok 원본 CSV (매월 업로드)
├── pipeline/
│   ├── build_monthly.py          ← 먼슬리 리포트 빌더 (확정)
│   ├── build_weekly.py           ← 위클리 리포트 빌더 (미구현)
│   └── build_daily.py            ← 데일리 리포트 빌더 (미구현)
├── data_out/
│   ├── monthly_data.json         ← 먼슬리 파이프라인 출력 JSON
│   ├── weekly_data.json          ← 위클리 파이프라인 출력 JSON
│   └── daily_snapshot.json       ← 데일리용 전일 스냅샷 (누적)
└── reports/
    ├── tiktok_monthly_dayt_YYYYMM.html
    ├── tiktok_weekly_dayt_YYYYMMDD.html
    └── tiktok_daily_YYYYMMDD.md
```

---

## 데이터 파싱 규칙

### CSV 컬럼명 → Python 변수명

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

### OFF 소재 판별

```python
df['is_off'] = df['ad_name'].str.lower().str.endswith('_off')
df_on  = df[~df['is_off']]   # KPI·TIER 계산에 사용
df_off = df[df['is_off']]    # OFF 분석 섹션에만 사용
```

**⚠️ 중요**: OFF 소재는 KPI, TIER 분류, 지점 CPA 등 모든 성과 지표 계산에서 제외한다.

### 광고명 파싱

```python
BRANCHES  = ['서울', '일산', '대구', '천안', '부평', '수원', '창원']
CTYPES    = ['인플방문후기', '의료진정보', '진료셀프캠']

def parse_ad(name):
    branch = next((b for b in BRANCHES if b in name), None)
    ctype  = next((t for t in CTYPES  if t in name), '기타')
    hook   = '재가공' if name.startswith('(재)') else ('신규' if name.startswith('(신)') else '일반')
    return branch, ctype, hook
```

### 소재명(creative_name)

- **광고 이름(`ad_name`) 원본을 그대로 사용**
- OFF 소재의 경우 `_off` 접미사만 제거: `re.sub(r'_off\s*$', '', name, flags=re.IGNORECASE)`

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

## TIER 분류 기준

**Target CPA**: ON 소재 전체 CPA 중앙값 (동적 계산)

```python
TARGET_CPA = cr[cr['총전환'] > 0]['CPA'].median()
```

| TIER | 조건 |
|------|------|
| **TIER1** | CPA ≤ TARGET_CPA AND CVR ≥ 5.0% |
| **TIER2** | CPA ≤ TARGET_CPA AND CVR < 5.0% AND 랜딩도달률 ≥ 50% |
| **TIER3** | CPA > TARGET_CPA AND CVR ≥ 5.0% |
| **TIER4** | 나머지 |
| **LOW_VOLUME** | 클릭 < 100 AND 비용 < 100,000원 (전환 여부 무관) |
| **UNCLASSIFIED** | 집행일수 < 7일 |

**⚠️ 주의**: LOW_VOLUME, UNCLASSIFIED는 먼슬리 기준. 위클리는 집행일수 < 3일이면 UNCLASSIFIED, 클릭 < 50 AND 비용 < 50,000원이면 LOW_VOLUME.

---

## ON/OFF 액션 권고 기준

### OFF 권고 (위클리·먼슬리)

```python
# 지점 평균 CPA의 3배 이상 비용 소진 + CPA 1.5배 초과 + CVR < 3%
if (소재×지점 비용 >= 지점평균CPA × 3
    and 소재CPA > 지점평균CPA × 1.5
    and CVR < 3.0):
    → OFF 권고
```

### ON 권고 (위클리·먼슬리)

```python
# TIER1 소재 중 집행하지 않는 지점 존재 시
if TIER == 'TIER1' and len(미집행_지점) > 0:
    → 해당 미집행 지점에 ON 권고
```

---

## 3종 리포트 시스템

### 1. 데일리 리포트 (build_daily.py)

| 항목 | 내용 |
|------|------|
| **형태** | Markdown 텍스트 (카카오톡 전송용) |
| **발행** | 매일 아침 (전일 데이터) |
| **수신자** | 쏭 (내부 모니터링) |
| **분량** | 10줄 이내 |

**포함 내용**:

```markdown
📊 [MM/DD] 다이트한의원 TikTok 전일 성과

📌 전체
• 전환: XX건 (전일 대비 ±XX건)
• CPA: XX,XXX원 (전일 대비 ±X,XXX원)
• CTR: X.XX% (전일 대비 ±X.XX%p)

🏢 지점별
• 서울: CPA XX,XXX원 (±XX원) | CTR X.XX% (±X.XXp)
• 부평: CPA XX,XXX원 (±XX원) | CTR X.XX% (±X.XXp)
[... 각 지점 1줄]

⚠️ 이상 감지
• [지점] [소재명] — CPA X.Xx배 (지점 평균 대비), OFF 검토 권고
• (없으면 "이상 없음")
```

**이상 감지 기준**: CPA가 지점 평균의 2배 이상 AND 비용 ≥ 지점평균CPA × 2

**데이터 처리**:
- 전일 스냅샷을 `daily_snapshot.json`에 저장하고, 다음 날 비교에 사용
- `daily_snapshot.json` 구조: `{"YYYY-MM-DD": {"branch": {...}, "total": {...}}}`

---

### 2. 위클리 리포트 (build_weekly.py)

| 항목 | 내용 |
|------|------|
| **형태** | HTML 단일 스크롤 페이지 |
| **발행** | 매주 월요일 (전 주 월~일 기준) |
| **수신자** | 클라이언트 직접 열람 |
| **TIER 기준** | 해당 주 데이터만 (7일 윈도우) |

**섹션 구성**:

1. 헤더: 분석기간, 비교기간, 발행일
2. 이번 주 KPI — 전주 대비 (광고비, 전환, CPA, CTR, CVR)
3. 핵심 인사이트 — 변화 원인 분석 (TIER 변동, 지점 CPA 급등/급락)
4. 소재 TIER 현황 — 이번 주 TIER + 전주 대비 변동 표
5. 지점별 성과 — CPA/CTR/CVR 전주 대비 차트 + 테이블
6. 예산 페이스 — 지점별 소진율 vs 기간 경과율 바 차트
7. 소재 ON/OFF 액션플랜 — OFF 권고 / ON 권고 (참고용)
8. 이번 달 전환 목표 달성 예상 — 현재 누적 + 페이스 기준 월말 예상

**주간 TIER 기준 차이**: 집행일수 < 3일 = UNCLASSIFIED, 클릭 < 50 AND 비용 < 50,000원 = LOW_VOLUME

**JSON 출력 스키마** (`weekly_data.json`):

```json
{
  "period_this": "MM/DD~MM/DD",
  "period_prev": "MM/DD~MM/DD",
  "issue_date": "YYYY.MM.DD(요일)",
  "kpi_this": {"cost": int, "conv": int, "cpa": int, "ctr": float, "cvr": float},
  "kpi_prev": {"cost": int, "conv": int, "cpa": int, "ctr": float, "cvr": float},
  "target_cpa": int,
  "tier_list": [{"creative_name": str, "tier_this": str, "tier_prev": str, "change": str}],
  "tier_this": [...],
  "branch": [{"branch": str, "CPA": float, "CPA_prev": float, "CPA_diff": float, "CTR": float, "CTR_diff": float, "CVR": float, "CVR_diff": float, "총전환": int}],
  "off_list": [{"branch": str, "creative_name": str, "CPA": int, "CVR": float, "avg_cpa": int, "ratio": float, "cost": int}],
  "on_list": [{"creative_name": str, "missing": [str], "CPA": int}],
  "pace": [{"branch": str, "budget": int, "spent": int, "rate": float, "remaining": int, "status": str}],
  "elapsed_rate": float,
  "monthly_target_conv": int,
  "conv_so_far": int,
  "proj_conv": int,
  "conv_pct": float,
  "proj_pct": float,
  "insights": [{"type": str, "color": str, "title": str, "points": [str]}],
  "daily": [{"date_str": str, "cost": int, "conv": int, "cpa": int, "ctr": float}],
  "budget": {"지점명": int}
}
```

---

### 3. 먼슬리 리포트 (build_monthly.py) ✅ 확정

| 항목 | 내용 |
|------|------|
| **형태** | HTML 7탭 구조 |
| **발행** | 익월 1~3일 |
| **수신자** | 클라이언트 + 의사결정자 |
| **TIER 기준** | 전체 월간 데이터 (집행일수 ≥ 7일) |

**7탭 구조**:

1. **월간 요약**: KPI 카드 6개, TIER 분포 도넛차트, 지점별 CPA 바차트, 핵심 인사이트 4개
2. **소재 TIER**: 버블차트 (X:CTR, Y:CVR, 크기:비용), ON 소재 테이블, TIER1 확장 기회, **OFF 소재 성과**, **OFF 전후 지점 CPA 참고**
3. **지점 분석**: CPA/효율 차트, 지점 상세 테이블, 소재×지점 CPA 편차, 지점×나이대 히트맵
4. **나이대 분석**: 비용비중 vs 전환비중 차트, 소재유형×나이대 CTR/CVR 히트맵, 나이대 상세
5. **소재 수명**: 신규 vs 재가공 비교, 집행일수별 CTR 추이 라인차트, 소재 수명 테이블
6. **일별 트렌드**: 광고비+전환수 콤보차트, CTR/CPA 추이
7. **다음 달 전략**: 지점별 예산 배분 권고, 신규 소재 기획 방향, ON 소재 중 OFF 권고

**OFF 소재 섹션 (소재 TIER 탭 내)**:

```
[OFF 소재 집행 성과 테이블]
컬럼: 광고 이름 | 지점 | 상태(OFF 배지) | 총비용 | 전환 | CPA | CTR | CVR | 집행일

[OFF 전후 지점 CPA 참고]
⚠️ 해석 주의 안내: 지점 전체 CPA이며 복합 요인 반영. 단정 불가.

카드 구조 (소재별):
├── OFF 소재 성과 (CPA, CTR, CVR, 비용, 전환)
├── → OFF 전 지점 CPA (X일 평균)
└── → OFF 후 지점 CPA (X일 평균, 변화율)
하단: 예산 점유율 바 + 영향 가능성 (높음/중간/낮음)
```

**점유율 기반 영향 가능성 기준**:

```python
if share_pct >= 20: impact_level = 'high'   # 영향 가능성 높음
elif share_pct >= 8: impact_level = 'mid'   # 영향 가능성 중간
else:                impact_level = 'low'   # 영향 가능성 낮음
```

**신뢰도(after 기간) 기준**:

```python
if after_days == 0: reliability = 'no_after'
elif after_days <= 2: reliability = 'low'
elif after_days <= 5: reliability = 'mid'
else:                 reliability = 'high'
```

**먼슬리 JSON 스키마** (`monthly_data.json`) — 주요 필드:

```json
{
  "period": "YYYY.MM.DD ~ MM.DD",
  "kpi": {"cost": int, "conv": int, "cpa": int, "ctr": float, "cvr": float, "lpv": float},
  "target_cpa": int,
  "monthly_target_conv": int,
  "budget": {"지점명": int},
  "creative": [...],
  "branch": [...],
  "cross_gap": [...],
  "age": [...],
  "hm_ctr": [...],
  "hm_cvr": [...],
  "hm_br_age": [...],
  "lifetime": [...],
  "hook_compare": [...],
  "daily": [...],
  "next_budget": [...],
  "off_cumul": [...],
  "expansion": [...],
  "off_perf": [
    {
      "creative_name": str,   // 광고 이름 원본 (_off 제외)
      "branch": str,
      "총비용": int, "총전환": int, "총클릭": int, "총노출": int,
      "집행일수": int, "소재유형": str,
      "CPA": float, "CTR": float, "CVR": float
    }
  ],
  "before_after": [
    {
      "creative_name": str, "branch": str, "off_date": "MM/DD",
      "off_cpa": int, "off_ctr": float, "off_cvr": float,
      "off_cost": int, "off_conv": int,
      "before_cpa": int, "before_days": int,
      "after_cpa": int, "after_days": int,
      "cpa_change": int, "cpa_change_pct": float,
      "effect": "improved|worsened|neutral|null",
      "reliability": "high|mid|low|no_after",
      "share_pct": float,
      "impact_level": "high|mid|low",
      "impact_label": str
    }
  ]
}
```

---

## 디자인 시스템

모든 리포트에서 공통으로 사용하는 색상/폰트.

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

### 폰트

- 본문: `Noto Sans KR` (Google Fonts)
- 숫자: `DM Mono` (Google Fonts)

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

### 차트 공통 설정 (Chart.js 4.4.x)

```javascript
const ax = { grid: { color: 'rgba(255,255,255,.04)' }, ticks: { color: '#2e3648', font: { size: 10 } } };
const tt = { backgroundColor: '#11141c', titleColor: '#dde4f0', bodyColor: '#7a8499', borderColor: '#1c2030', borderWidth: 1 };
```

---

## 파일 명명 규칙

```
tiktok_monthly_dayt_YYYYMM.html      # 먼슬리 (예: tiktok_monthly_dayt_202602.html)
tiktok_weekly_dayt_YYYYMMDD.html     # 위클리 (발행일 기준, 예: tiktok_weekly_dayt_20260302.html)
tiktok_daily_YYYYMMDD.md             # 데일리 (전일 기준, 예: tiktok_daily_20260302.md)
```

---

## 현재 구현 상태

| 리포트 | 데이터 파이프라인 | HTML/템플릿 | 상태 |
|--------|-----------------|------------|------|
| 먼슬리 | `build_monthly.py` ✅ | 7탭 HTML ✅ | **확정 완료** |
| 위클리 | 파이프라인 로직 완성 ✅ | HTML 빌더 완성 ✅ | OFF 필터링 미적용 |
| 데일리 | 미구현 ❌ | Markdown 형태 설계 완료 ✅ | 구현 필요 |

---

## 즉시 구현 필요 사항

### Task 1: 위클리 — OFF 소재 필터링 통합

현재 위클리 파이프라인이 `is_off` 플래그를 생성하지만, TIER 계산과 KPI에서 완전히 분리되지 않았을 수 있음.

**검증 방법**:
```python
# OFF 소재가 KPI/TIER에서 제외되는지 확인
df_on = df[~df['is_off']].copy()
# 이하 모든 계산은 df_on 기준으로
```

### Task 2: 데일리 리포트 구현 (build_daily.py)

**핵심 로직**:

```python
# 1. 전일 데이터 필터
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
df_yd = df_on[df_on['date'] == yesterday]

# 2. 스냅샷 로드 (없으면 빈 dict)
with open('daily_snapshot.json') as f:
    snapshot = json.load(f)
prev = snapshot.get(prev_date, {})

# 3. 지점별 집계 + 전일 대비
# 4. 이상 감지 (CPA가 지점 평균 2배 이상 AND 비용 ≥ 지점평균CPA×2)
# 5. Markdown 출력
# 6. 스냅샷 업데이트 (오늘 데이터 저장)
```

---

## 주의사항 (반드시 준수)

1. **OFF 소재는 항상 분리**: `df_on = df[~df['is_off']]` — 이 이후 모든 KPI/TIER 계산
2. **소재명은 광고 이름 원본 사용**: `_off` 접미사만 제거, 나머지 파싱 없음
3. **TIER TARGET_CPA는 동적 계산**: 하드코딩 금지, 항상 `df_on` 중앙값으로
4. **NaN 처리**: 전환=0인 경우 CPA=None (0 아님), JSON 직렬화 시 `clean()` 함수 사용
5. **OFF 전후 CPA는 인과관계 아님**: 지점 전체 CPA 참고값, 단정 불가 문구 항상 표시
6. **예산 점유율**: OFF 전 기간 해당 소재의 지점 내 비용 비중 (before 기간 기준)

---

## 실행 방법

```bash
# 먼슬리 (월별 CSV 업로드 후)
python3 pipeline/build_monthly.py --csv data/tiktok_raw.csv --month 202602

# 위클리 (매주 월요일 자동 실행)
python3 pipeline/build_weekly.py --csv data/tiktok_raw.csv --week 20260224

# 데일리 (매일 아침 크론잡)
python3 pipeline/build_daily.py --csv data/tiktok_raw.csv
```

---

## 참고: 클린 함수 (JSON 직렬화)

```python
import numpy as np

def clean(obj):
    if isinstance(obj, dict):   return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, list):   return [clean(v) for v in obj]
    if isinstance(obj, float) and np.isnan(obj): return None
    if isinstance(obj, np.integer):  return int(obj)
    if isinstance(obj, np.floating): return None if np.isnan(obj) else float(obj)
    if isinstance(obj, pd.Timestamp): return obj.strftime('%Y-%m-%d')
    return obj
```
