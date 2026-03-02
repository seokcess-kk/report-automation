# 데이터 명세

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
BRANCHES = ['서울', '부평', '수원', '일산', '대구', '창원', '천안']
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

## 지점별 월 예산

```python
BUDGET = {
    '서울':  2_000_000,
    '일산':  1_000_000,
    '대구':  3_000_000,
    '천안':  2_000_000,
    '부평':  3_000_000,
    '창원':  2_000_000,
    '수원':  3_000_000,
}
MONTHLY_TARGET_CONV = 600  # 전체 지점 합산 월 목표 전환
```

---

## 클린 함수 (JSON 직렬화)

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
