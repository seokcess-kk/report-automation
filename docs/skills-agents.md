# 스킬 & 에이전트 정의

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
