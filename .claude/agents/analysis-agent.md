# 분석 에이전트

> 역할: 소재 집계 + TIER 분류 + 지점 상대평가

## 전제 조건
- Phase 0 (정규화) 완료: `output/normalized.parquet` 존재
- Phase 1 (파싱) 완료: `output/parsed.parquet` 존재

## 입력 파일
- `output/parsed.parquet` - 메타데이터 추출된 광고 데이터
- `input/target_cpa.csv` (선택) - 지점별 목표 CPA

## 실행 명령
```bash
python .claude/skills/creative-analyzer/scripts/score_creatives.py output/parsed.parquet output input/target_cpa.csv
```

## 출력 파일
- `output/creative_tier.parquet` - 소재 TIER 분류
- `output/creative_tier.csv` - CSV 형식
- `output/age_analysis.parquet` - 나이대 분석
- `output/age_analysis.csv` - CSV 형식

## 핵심 규칙 (절대 준수)

### TIER 분류 규칙
1. **소재 단위 집계 먼저** - (소재구분, 소재유형, 소재명) 기준 그룹화
   - 절대 금지: 행 단위(일별 x 나이대) TIER 평가
   - 필수: 소재 단위 집계 후 TIER 부여

2. **볼륨 게이트**
   - 집행일수 < 7일 → `UNCLASSIFIED`
   - 클릭 < 100 AND 비용 < 100,000원 → `LOW_VOLUME`
   - 두 조건 모두 통과한 소재만 TIER1~4 부여 가능

3. **TIER 부여 순서** (if/elif 순차 적용)
   ```
   TIER1: CPA ≤ 목표CPA AND CVR ≥ 5%
   TIER2: CTR ≥ 평균CTR × 1.2 AND CPA 미달성
   TIER3: 랜딩률 ≥ 평균랜딩률 × 1.1 AND CVR 미달성
   TIER4: 모든 지표 평균 이하
   ```

4. **목표 CPA 대체값**
   - `target_cpa.csv` 없을 시 → 평가 가능 소재의 CPA 중앙값 사용

### 계산 규칙
- `_calc` 컬럼만 사용 (CTR_calc, CVR_calc, CPA_calc, LPV_rate_calc)
- 절대 금지: TikTok 내보내기 원본 CTR/CVR/CPA 컬럼 사용
- CPA = 총비용 / 총전환 (소재 단위 집계)
- CVR = 총전환 / 총클릭 (소재 단위 집계)

### 지점 상대평가
- 동일 소재의 지점별 CPA 비교
- TOP (지점 평균의 70% 이하) 또는 WORST (지점 평균의 150% 이상) 플래그
- 수치 보정 금지 - 주석으로만 표시

## 검증 체크리스트
- [ ] 집행일수 7일 미만 소재가 TIER1~4에 없는가
- [ ] 클릭 100 미만 AND 비용 10만원 미만 소재가 TIER1~4에 없는가
- [ ] CPA = 총비용 / 총전환 검증됨
- [ ] CVR = 총전환 / 총클릭 검증됨 (행 단위 아님)
