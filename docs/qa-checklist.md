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

## 자동 업데이트 정책

- **파서 패턴 오류**: 자동 업데이트 허용
- **분석 로직 변경**: `output/data/YYYYMMDD/improvement_suggestions.md`에만 저장
