# 3차 — 구현 결과 검토 요청

지난 1, 2차 논의를 바탕으로 구현 완료했습니다. 마지막 검수 부탁드립니다.

## 구현된 변경 사항

### 1. 데이터 레이어
- `build_june_targets.py` 확장: 전환수·CPA 목표 추가 (Primary KPI)
  - 전 지점 합산: 전환 762건 (4월), CPA 27,278원 (2월)
  - 야심 목표: 822건 (지점별 베스트월 합산)
- `derive_consulting_signals.py` 신규: codex 권장 8개 보조 지표
  - primary_gap, funnel_status, bottleneck_type, priority_score
  - expected_impact_range, guardrail, creative_role, confidence_level

### 2. HTML 템플릿 (`html_template.py`)
- 5개 페이지: 01 Executive Summary / 02 성과 진단 / 03 6월 목표·액션 / 04 타겟팅·콘텐츠 / 05 애드온
- 컴포넌트:
  - Page Header Strip (Key Message + 메타)
  - Insight / Evidence / Action / Appendix 4등급 카드
  - 섹션 번호 (1.1, 1.2 / Appendix A.1 등)
  - 상태 배지(good/warn/bad/mid/na/new + group A/B/C + priority)
  - Primary KPI 카드 (큰 사이즈, top border) / Funnel KPI 카드 (작은 사이즈, left border)
  - 사분면 차트 (좌상/우상/좌하/우하 라벨)
  - 지점×퍼널 진단 매트릭스 (셀 배경 ✕, 상태 배지)
  - 지점×퍼널 통합 실행 매트릭스 (CPM/CTR/CVR 셀 안에 상태/액션/역할/추천)
  - 3대 운영 판단 카드 (판단/대상/근거/액션/중단조건/기대효과)
  - 그룹별 지점 처방 카드 (진단·소재역할·액션·KPI·중단조건·기대효과)
  - 콘텐츠 큐레이션 카드 (유지/확대/신규 3-rail)
  - 퍼널별 TOP3 (CPM/CTR/CVR 동등)

### 3. JS 렌더링 (`js_body.py`)
- 페이지별 IIFE 분리
- consulting_signals를 모든 페이지에서 활용
- 헬퍼: statusBadge, gapBadge, priorityBadge, groupBadge, heatClass

## 디자인 시스템 결정 사항
- 다크 테마 유지 (--bg #0a0a0c)
- 색 코딩: 빨강=우려, 주황=주의, 초록=양호/확대, 보라=신규, 회색=부록
- 셀 배경 색칠 ✕ → 상태 배지 + 좌측 border
- 폰트: 페이지 24px / 메시지 15px / 섹션 16px / 카드 14px / 본문 12-13px / 메타 10-11px
- 차트 수: P0:1개, P1:2개, P2:0개, P3:0개, P4:1개 (총 4개)

## 4.1 지점×퍼널 통합 실행 매트릭스 셀 구조 (확정)
각 퍼널 셀 안에:
1. 상태 배지 (good/warn/bad)
2. 액션 1줄 ("유지" 또는 병목 기반 처방)
3. 소재 역할 (우려/주의 셀에만)
4. 추천 소재 1개 (병목 셀에만, 18자 자름)

## 최종 검토 요청

위 모든 변경을 종합해, 다음 질문에 답해주세요.

1. **컨설팅 deck로서 완성형인지** — 추가로 다듬어야 할 결정적 결함이 있는지
2. **클라이언트가 첫 화면에서 6월 운영 방향을 한 줄로 알 수 있는지**
3. **타겟팅·콘텐츠 페이지가 "분석 모음"이 아니라 "실행안"으로 읽히는지** — 4.1 매트릭스의 27셀 정보 밀도가 적절한지
4. **부록(A/B/C) 사용이 자연스러운지** — 본문/부록 위계가 명확한지
5. **놓친 보강점** — 컨설팅 보고서 기준으로 마지막에 더 넣어야 할 요소가 있는지

이번에는 짧고 임팩트 있게, 결정적 개선 3가지만 짚어주세요. 한국어, 500자 이내 권장.
