# QA 에이전트

> 역할: 리포트 생성 전 데이터 무결성 및 분석 품질 검증

## 전제 조건
- Phase 2와 Phase 3 완료
- 모든 분석 출력물이 `output/`에 존재

## 입력 파일
- `output/normalized.parquet` - 정규화된 원본 데이터
- `output/parsed.parquet` - 파싱된 데이터
- `output/creative_tier.parquet` - 소재 TIER 데이터
- `output/hook_type_comparison.parquet` - 훅 비교
- `output/age_analysis.parquet` - 나이대 분석
- `output/anomalies.csv` - 이상치 감지 결과

## 출력 파일
- `output/YYYYMMDD/qa_report.json` - QA 검증 결과

## QA 체크리스트

### 데이터 무결성
1. **비용 일치**: raw 총비용 = 분석 총비용 (오차: +-1원)
2. **전환 일치**: raw 총전환 = 분석 총전환
3. **파싱 실패 제외**: FAIL 소재가 TIER 분석에 없음

### TIER 품질
1. **7일 미만 없음**: 집행일수 < 7인 소재가 TIER1~4에 없음
2. **저볼륨 없음**: 클릭<100 AND 비용<10만원 소재가 TIER1~4에 없음
3. **TIER3 확인**: TIER3 개수가 0이면 classify_tier() elif 순서 확인

### 계산 검증
1. **CPA**: CPA = 총비용 / 총전환 (랜덤 3개 소재 스팟 체크)
2. **CVR**: CVR = 총전환 / 총클릭 (소재 단위, 행 단위 아님)
3. **CTR**: CTR = 총클릭 / 총노출

### 훅 비교
1. strict_pairs 또는 type_comparison 중 하나 이상 존재
2. 매칭 안 된 재가공 소재 목록 생성됨

### OFF 소재
1. `_off`로 끝나는 광고명에서 `is_off` 플래그 정상 파싱
2. OFF 소재가 TIER 분석에서 제외됨 (df_on)
3. Excel에 OFF 소재 시트 존재

### 출력물
1. Excel 파일에 7개 시트 존재
2. PDF 파일 존재
3. analysis_validation.json 존재

## 차단 규칙
- **all_pass = false** → Phase 5 (리포트 생성) 차단
- 콘솔에 실패 항목 눈에 띄게 출력
- 통과/실패 여부와 관계없이 `qa_report.json` 생성

## 실패 시 콘솔 출력
```
============================================================
QA 검증 실패
============================================================
실패 항목:
  - [각 실패 항목 설명]

문제 해결 전까지 Phase 5 (리포트 생성) 차단됨.
============================================================
```
