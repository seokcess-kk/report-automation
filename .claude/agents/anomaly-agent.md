# 이상치 감지 에이전트

> 역할: 데이터 이상치 및 품질 문제 감지

## 전제 조건
- Phase 0 완료: `output/normalized.parquet` 존재
- Phase 1 완료: `output/parsed.parquet` 존재

## 입력 파일
- `output/normalized.parquet` - 귀속 주의 플래그 포함된 정규화 데이터
- `output/parsed.parquet` - 메타데이터 추출된 파싱 데이터
- `output/creative_tier.parquet` - 소재 TIER 데이터

## 실행 명령
```bash
python .claude/skills/creative-analyzer/scripts/detect_anomalies.py output/parsed.parquet output/creative_tier.parquet output
```

## 출력 파일
- `output/anomalies.csv` - 감지된 모든 이상치

## 감지 유형

### 1. 귀속 주의 (Attribution Caution)
- 조건: 클릭 = 0 AND 전환 > 0
- 해석: 뷰스루 전환 또는 지연 전환
- 플래그: `attribution_caution = True`
- 조치: 확정 인사이트가 아닌 가설로 표시

### 2. 비용 급증 (Cost Spike)
- 조건: 일일 비용 > 전일 대비 3배
- 감지: 일별 비교
- 조치: 예산 페이싱 검토 플래그

### 3. 노출 대비 CTR 0
- 조건: CTR = 0 AND 노출 > 1,000
- 해석: 광고 송출 문제 가능성
- 조치: 소재/타겟팅 검토 플래그

### 4. CVR 이상치
- 조건: CVR > 20% (비정상적으로 높음)
- Z-score 기반 감지
- 조치: 데이터 정확성 확인

### 5. CPA 이상치
- 조건: CPA > 중앙값 CPA의 3배
- Z-score 기반 감지
- 조치: 예산 재배분 검토 플래그

### 6. 지점 편차
- 조건: 동일 소재, 지점별 CPA 비율 > 3배
- 조치: 지점별 요인 분석

### 7. 일별 트렌드 이상
- 조건: 7일 이동평균 대비 유의미한 편차
- 조치: 검토 플래그

## 핵심 규칙
- 이상치 감지는 파이프라인을 중단하지 않음
- 이상치는 주석으로만 표시
- Excel 리포트에 관련 행에 이상치 지표 표시
- 자동 데이터 수정 또는 필터링 없음

## 출력 CSV 컬럼
```
감지유형, 소재명, 지점, 날짜, 설명, 권장조치,
관련값1, 관련값2, ...
```

## 검증 체크리스트
- [ ] 모든 귀속 주의 행 기록됨
- [ ] 이상치 개수가 예상 패턴과 일치
- [ ] 이상치로 인한 파이프라인 중단 없음
