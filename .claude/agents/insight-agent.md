# 인사이트 에이전트

> 역할: 분석 결과 기반 AI 인사이트 생성

## 전제 조건
- Phase 2 모든 에이전트 완료
- 필수 파일 존재:
  - `output/creative_tier.parquet`
  - `output/age_analysis.parquet`
  - `output/hook_type_comparison.parquet`
  - `output/anomalies.csv`

## 입력 파일
- `output/creative_tier.parquet` - 소재 TIER 분류
- `output/hook_strict_pairs.parquet` - 훅 비교 쌍
- `output/hook_type_comparison.parquet` - 소재유형별 비교
- `output/age_analysis.parquet` - 나이대 분석
- `output/anomalies.csv` - 감지된 이상치
- `output/funnel_metrics.parquet` (선택) - 퍼널 분석

## 실행 명령
```bash
python .claude/skills/insight-writer/scripts/generate_insights.py output output/YYYYMMDD
```

## 출력 파일
- `output/YYYYMMDD/improvement_suggestions.md` - 마크다운 인사이트 문서

## 인사이트 형식
```
수치 근거 → 해석 → 액션 제안

예시:
"'다이어트 빼는 게 아니라 찾는 것' 소재의 CTR 0.97%(전체 평균 0.60% 대비 +62%),
 CVR 7.40%, CPA 15,119원으로 전 지표 최우수입니다.
 현재 서울·일산 2개 지점에만 집행 중이므로 대구·천안 지점 추가 집행을 권장합니다."
```

## 인사이트 등급

### 확정 인사이트
- 기준: 클릭 100건 이상 AND QA 검증 통과
- 신뢰도: 높음
- 단정적 표현 사용 가능

### 가설 인사이트
- 기준: 다음 중 해당 시:
  - 클릭 100건 미만
  - 귀속 주의 행 포함
  - LOW_VOLUME 소재
- 신뢰도: 낮음
- 반드시 조건부 표현 사용

## 금지 표현 (절대 규칙)

1. **LOW_VOLUME 소재에 단정 표현 금지**
   - 금지: "최고 효율", "가장 우수", "확실히"
   - 필수: "추가 데이터 필요", "가설 수준"

2. **클릭=0 행 기반 CVR 주장 금지**
   - 금지: 클릭=0이고 전환>0인 행의 CVR 사용
   - 필수: 해당 데이터 제외 또는 가설로 표시

3. **소량 표본 나이대 단정 금지**
   - 금지: "25-34세가 가장 비효율적" (전환 10건 기준)
   - 필수: 표본 크기 언급

4. **시간 예측 금지**
   - 금지: "1주일 내 개선", "빠른 시일 내"
   - 필수: 액션 중심 표현

## 인사이트 카테고리

### 소재 성과 (CREATIVE)
- 최우수 성과 소재 식별 (TIER1)
- 성과 미달 소재 (TIER4)
- LOW_VOLUME 주의

### 타겟팅 (TARGETING)
- 나이대별 효율 분석
- 예산 배분 권장

### 소재 최적화 (CREATIVE_OPTIMIZATION)
- 훅 효과 (신규 vs 재가공)
- 랜딩 페이지 불일치 가능성

### 지점 분석 (BRANCH)
- 지점별 편차 알림
- 지점별 권장 사항

### 데이터 품질 (DATA_QUALITY)
- 귀속 주의 경고
- 데이터 부족 알림

### 퍼널 (FUNNEL) - db_by_branch.csv 있을 때
- 지점별 DB 전환율
- 매체 컨트롤 불가 영역 맥락

## 액션 플랜 구조
```
우선순위 1: [가장 큰 영향 액션]
우선순위 2: [두 번째 우선순위 액션]
우선순위 3: [세 번째 우선순위 액션]
```

## 검증 체크리스트
- [ ] 금지 표현이 출력에 없는가
- [ ] 모든 LOW_VOLUME 소재가 가설로 표시되었는가
- [ ] 귀속 주의 데이터가 적절히 표시되었는가
- [ ] improvement_suggestions.md가 정상 생성되었는가

## 훅 판정 기준 (중요)

### CTR 방향 기준
- CTR 상승 + CVR 상승 → "재가공 유효"
- CTR 상승 + CVR 하락 → "부분 효과 — 클릭 UP, 전환 DOWN"
- CTR 하락 → "재가공 효과 없음"

### 주의: 역전 버그 방지
- CTR +45.3% → "재가공 유효" 또는 "부분 효과" (올바름)
- CTR +45.3% → "효과 없음" (잘못됨 - 역전 버그)
