# QA 체크리스트

## 데이터 무결성

- [ ] raw total_cost = analysis total_cost (오차 ±1)
- [ ] raw total_conversions = analysis total_conversions
- [ ] CPA_calc = cost/conversions 검증

## TIER 분류

- [ ] TIER1~4에 <7일 또는 저볼륨 소재 없음
- [ ] OFF 소재 TIER 분석에서 제외됨
- [ ] LOW_VOLUME, UNCLASSIFIED 올바르게 분류됨

## 리포트 출력

- [ ] Excel 7개 시트 생성됨
- [ ] before_after.parquet 생성됨
- [ ] HTML 리포트 한글 깨짐 없음 (Noto Sans KR CDN 로드 확인)
- [ ] OFF 소재가 TIER 테이블에 미포함

---

## 먼슬리 리포트 검증 (v3.4)

### 효율점수 검증 (다음 달 전략 탭)
- [ ] 지점별 효율점수가 1.0 고정이 아닌 다양한 값 표시
- [ ] 효율점수에 따른 색상 구분 (녹/파/빨)
- [ ] 권고 문구가 효율점수에 맞게 표시 (증액/유지/감액)
- [ ] 예산 조정 계산 정확성 (×1.15 / 유지 / ×0.85)

### 신규 vs 재가공 섹션 (소재 수명 탭)
- [ ] 막대+선 복합 차트 정상 렌더링
- [ ] 상세 테이블에 6개 지표 모두 표시 (소재수, 비용, 전환, CPA, CTR, CVR)
- [ ] 신규/재가공 분류 정확성

### 신규 소재 섹션 (소재 TIER 탭)
- [ ] UNCLASSIFIED 소재만 표시됨
- [ ] 집행일수 7일 미만 소재만 포함
- [ ] 소재명, 지점, 비용, 전환, CPA, CTR, CVR 컬럼 표시

### Before/After 필터 (OFF 전후 탭)
- [ ] 소재명 필터 드롭다운 동작
- [ ] 지점 필터 드롭다운 동작
- [ ] "전체" 선택 시 모든 데이터 표시
- [ ] 복합 필터링 (소재+지점) 정상 동작

---

## 자동 업데이트 정책

- **파서 패턴 오류**: 자동 업데이트 허용
- **분석 로직 변경**: `output/data/YYYYMMDD/improvement_suggestions.md`에만 저장
