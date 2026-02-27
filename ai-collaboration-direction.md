# 바이브 코딩 AI 협업 시스템 — 프로젝트 설계 지침 v2.0

> Claude Code / Claude Project 지침용
> SDD(Spec Driven Development) + DDD(Domain Driven Design) 통합 버전
> AI 기반 개발 시 할루시네이션 방지 + 일관된 코드 품질 + 방향 통제를 위한 표준

---

## 🎯 핵심 철학

**"AI에게 추측하게 하지 말고, 명시적으로 알려줘라."**

바이브 코딩에서 AI가 실수하는 4대 원인:

| # | 원인 | 증상 | 해법 |
|---|------|------|------|
| 1 | 방향 부재 | 엉뚱한 기능 구현 | **SDD — 주문서(Spec) 먼저 작성** |
| 2 | 프로젝트 맥락 부족 | 잘못된 패턴/경로 추측 | **DDD — 비즈니스 언어 = 코드명** |
| 3 | 지침 무시 (금붕어 기억력) | 매뉴얼 안 읽음, 앞부분 망각 | **훅 시스템 — 자동 매뉴얼 활성화** |
| 4 | 검증 부재 | 깨진 코드 방치 | **자동 QC — 완료 후 즉시 검사** |

> "AI는 그냥 쓰면 50점짜리 도구이지만, 시스템을 만들어 주면 95점짜리 에이스가 된다."

---

## 📋 전체 워크플로우 요약 (7-Phase 파이프라인)

```
Phase 0: SDD — 주문서(Spec) 작성 ← 🆕 최우선 단계
    ↓
Phase 1: CLAUDE.md — 프로젝트 기억 계층
    ↓
Phase 2: Skills — 도메인별 자동 참조 가이드라인
    ↓
Phase 3: skill-rules.json — 3중 트리거 자동 활성화
    ↓
Phase 4: Agents — 전문 에이전트 분업
    ↓
Phase 5: Hooks — 자동 품질 게이트
    ↓
Phase 6: /insight — 데이터 기반 지속 개선
    ↓
Phase 7: 코드 작성 시작
```

**⚠️ 중요: Phase 0~5를 건너뛰고 바로 코딩하지 말 것.**
인프라 구축에 30분~1시간 투자 → 이후 수십 시간의 디버깅/할루시네이션 대응 시간 절약.

---

## 🗺️ Phase 0: SDD (Spec Driven Development) — 주문서 먼저 써라

### 왜 SDD인가?

단순히 "결제 기능 만들어줘"라고 던지면 AI는 추측으로 작업한다.
**주문서(Spec)를 먼저 작성**하면 AI가 정확한 방향으로 움직인다.

```
기존 (바이브 코딩)          SDD 워크플로우
────────────────          ──────────────────
"결제 기능 만들어"  →  ❌    Spec 작성 → 검토 → 승인 → 구현  →  ✅
추측 → 오류 → 재작업        명확한 방향 → 정확한 결과물
```

### Spec 필수 섹션

```markdown
# [프로젝트/기능명] 개발 Spec

## 1. 개요
- 목적: [한 줄 요약]
- 범위: [포함/제외 사항 명확히]
- 성공 기준: [완료 조건 — 측정 가능하게]

## 2. 기술 스택 (정확한 버전 필수)
| 영역 | 기술 | 버전 | 비고 |
|------|------|------|------|
| Backend | FastAPI | 0.104+ | async/await 필수 |
| Frontend | Next.js | 15 | App Router |
| DB | PostgreSQL | 15+ | asyncpg 드라이버 |

## 3. 아키텍처
- 디렉토리 구조 (트리 형태)
- 계층 구조 (Routes → Controllers → Services → Repositories)
- 데이터 흐름도

## 4. 핵심 패턴 & 컨벤션
- 네이밍 규칙
- 파일 구조 규칙 (DDD 3파일 세트 기반)
- import 순서
- 에러 처리 패턴

## 5. 단계별 구현 계획 (Small Chunks)
| Phase | 작업 | 산출물 | 검증 방법 |
|-------|------|--------|----------|
| 1 | 프로젝트 초기화 | 디렉토리 구조 | 빌드 성공 |
| 2 | 첫 도메인 수동 작성 | model/service/repo | 타입 체크 |
| 3 | 패턴 복제 | 나머지 도메인 | 일관성 검토 |

## 6. 검증 체크리스트
- [ ] 타입 체크 통과
- [ ] 린트 통과
- [ ] 빌드 성공
- [ ] 핵심 기능 테스트
```

### Spec 작성 원칙 (4대 법칙)

| # | 원칙 | ❌ 나쁜 예 | ✅ 좋은 예 |
|---|------|-----------|-----------|
| 1 | 버전까지 명시 | "React" | "React 19 + Next.js 15 App Router" |
| 2 | 경로는 정확하게 | "main 모듈" | "`backend.main:app`" |
| 3 | 패턴은 코드 예시와 함께 | "DDD 패턴 사용" | 구체적 디렉토리 구조 + 코드 템플릿 |
| 4 | 검증은 실행 가능하게 | "테스트" | "`pytest backend/tests/ -v`" |

### Spec → 실행 프로세스

```
Spec 초안 작성 (planner 에이전트 활용)
    ↓
검토 & 수정 (plan-reviewer 에이전트 or 직접)
    ↓
승인 — "이 Spec대로 진행해"
    ↓
3대 문서 생성 (Phase 4의 외부 기억 장치)
    ↓
Phase 1부터 단계별 구현
```

---

## 🏗️ Phase 1: CLAUDE.md — 프로젝트 기억 계층

AI가 프로젝트에 대해 알아야 할 **모든 핵심 맥락**을 담는 파일.
모든 대화 시작 시 자동으로 읽힌다.

### 필수 섹션

```markdown
# CLAUDE.md

## 프로젝트 구조
[모노레포/단일앱 여부, 디렉토리 트리]

## 기술 스택
[프레임워크, 언어, DB, 패키지 매니저 — 정확한 버전]

## 빌드 & 실행 명령어
[dev/build/test/lint — 복붙으로 바로 실행 가능하게]

## 아키텍처 패턴
[계층 구조, 파일 네이밍, DDD 3파일 세트 패턴]

## 중요 주의사항
[실수하기 쉬운 포인트, 반드시 지켜야 할 규칙]

## 작업 프로세스
[Spec → Plan → Review → Approve → Implement 플로우]

## 배포
[CI/CD 파이프라인, 환경 설정]
```

### 작성 원칙

- **구체적이고 실행 가능하게**: "uvicorn 실행" (X) → "`uvicorn backend.main:app --reload --port 28080`" (O)
- **흔한 실수를 명시적으로 경고**: "주의: 모듈 경로는 `backend.main:app`이지 `app.main:app`이 아님"
- **핵심 함수명까지 기술**: "`get_read_session_dependency()` / `get_write_session_dependency()`"
- **분량 목표**: 5~15KB (너무 짧으면 맥락 부족, 너무 길면 토큰 낭비)

---

## 🧠 Phase 2: Skills — 도메인별 자동 참조 가이드라인

AI가 **특정 도메인 작업 시 자동으로 참조**하는 전문 지식 모듈.

### 디렉토리 구조

```
.claude/skills/
├── skill-rules.json              ← 자동 활성화 규칙 (핵심!)
├── [backend-framework]-guidelines/
│   ├── SKILL.md                  ← 핵심 요약 (~100줄)
│   └── resources/
│       ├── architecture.md       ← 아키텍처 패턴 (~200줄)
│       ├── error-handling.md
│       └── database.md
├── [frontend-framework]-guidelines/
│   ├── SKILL.md
│   └── resources/
└── [domain-specific]/
    └── SKILL.md
```

### Progressive Disclosure (점진적 공개) 원칙

```
SKILL.md (핵심 요약 ~100줄)
  └→ resources/topic.md (상세 ~200줄)
      └→ resources/examples/example.md (코드 예시)
```

AI가 **필요한 깊이만큼만 읽게** 구성. 수천 줄을 한번에 컨텍스트에 넣지 않는다.

### SKILL.md 작성 템플릿

```markdown
---
name: [skill-name]
description: "[AI가 자동 활성화 판단에 사용할 설명]"
---

# [스킬 제목]

## Purpose
[이 스킬이 존재하는 이유]

## When to Use
[자동 활성화 시나리오]

## Quick Reference
[핵심 패턴 3~5개, 코드 예시 포함]

## ✅ DO
[올바른 패턴]

## ❌ DON'T
[안티패턴 — 구체적 코드 예시]

## Resource Files
- [topic-1.md](resources/topic-1.md)
- [topic-2.md](resources/topic-2.md)
```

---

## 🔧 Phase 3: skill-rules.json — 3중 트리거 자동 활성화

**바이브 코딩의 핵심 접착제.** AI가 매뉴얼을 "무시"하는 문제를 해결한다.
특정 조건에서 관련 스킬이 자동으로 활성화되어 AI에게 강제로 읽히게 만든다.

### 4대 활성화 조건

| # | 조건 | 예시 |
|---|------|------|
| 1 | 키워드 | "API", "백엔드", "결제" |
| 2 | 의도 패턴 | "(만들|create).*?(API|엔드포인트)" |
| 3 | 작업 위치 | `backend/**/*.py` |
| 4 | 파일 내 패턴 | `from fastapi import`, `async def` |

**세 가지 중 하나라도 매칭되면 스킬 활성화.**

### 구조

```json
{
  "version": "1.0",
  "skills": {
    "[skill-name]": {
      "type": "domain | guardrail",
      "enforcement": "suggest | block",
      "priority": "critical | high | medium | low",
      "description": "[스킬 설명]",
      "promptTriggers": {
        "keywords": ["백엔드", "API", "route", "endpoint"],
        "intentPatterns": [
          "(create|add|implement|만들|추가).*?(route|endpoint|API|엔드포인트)",
          "(fix|debug|수정|디버그).*?(error|backend|에러|백엔드)"
        ]
      },
      "fileTriggers": {
        "pathPatterns": ["backend/**/*.py"],
        "pathExclusions": ["**/__pycache__/**", "**/test_*.py"],
        "contentPatterns": ["from fastapi import", "async def"]
      }
    }
  }
}
```

### enforcement 전략

| 타입 | 용도 | 예시 |
|------|------|------|
| **suggest** | 일반 가이드라인 | 백엔드 패턴, 테스팅 가이드 |
| **block** | 반드시 준수 (위반 시 작업 중단) | 프레임워크 호환성, 보안 패턴, 브랜드 가이드 |

### block 모드 필수 적용 상황

- 프레임워크 메이저 버전 호환성 (예: MUI v5 vs v7)
- 보안 관련 코드 패턴
- 브랜드/디자인 시스템 준수
- 데이터베이스 마이그레이션 패턴

---

## 🤖 Phase 4: Agents + 외부 기억 장치 — 분업화 & 맥락 유지

### 4-A: 전문 에이전트 구성

단일 AI에게 모든 것을 맡기지 않고, 역할별 전문 에이전트로 분업한다.

#### 필수 에이전트 (모든 프로젝트)

```
.claude/agents/
├── planner.md                     ← Spec 기반 구현 계획 수립 (코드 작성 금지)
├── plan-reviewer.md               ← 계획 검증 (계획의 계획)
├── code-architecture-reviewer.md  ← 아키텍처 리뷰 + 교차 검증
├── auto-error-resolver.md         ← 빌드 에러 자동 해결
└── documentation-architect.md     ← 문서 자동 생성
```

#### 선택 에이전트 (프로젝트별)

```
├── [framework]-error-fixer.md     ← 프레임워크별 에러 해결
├── auth-route-tester.md           ← 인증 라우트 테스트
├── code-refactor-master.md        ← 리팩토링 전문
└── web-research-specialist.md     ← 기술 리서치
```

#### 에이전트 작성 템플릿

```markdown
# [에이전트 이름]

## Purpose
[한 줄 목적]

## When to Use
- [시나리오 1]
- [시나리오 2]

## Instructions
1. [단계 1 — 구체적으로]
2. [단계 2]
3. [단계 3]

## Tools Available
- Read, Grep, Glob (코드 탐색)
- Edit, Write (코드 수정)
- Bash (명령어 실행)

## Expected Output Format
[리포트/코드/체크리스트 등 구체적 출력 형태]

## Success Criteria
- [ ] [검증 기준 1]
- [ ] [검증 기준 2]
```

#### 에이전트 vs 스킬 사용 기준

| 상황 | 스킬 | 에이전트 |
|------|------|---------|
| 코드 작성 중 패턴 참조 | ✅ | |
| 전체 아키텍처 리뷰 | | ✅ |
| 인라인 가이드라인 | ✅ | |
| 멀티파일 리팩토링 | | ✅ |
| 빌드 에러 자동 해결 | | ✅ |

### 4-B: 외부 기억 장치 (3대 문서)

대화가 길어져도 AI가 방향을 잃지 않도록 **반드시 3개 문서를 유지**한다.

```
dev/active/[task]/
├── [task]-plan.md      ← 전략 & 아키텍처 (Phase 0 Spec 기반)
├── [task]-context.md   ← 결정 이유, 관련 자료 위치 기록
└── [task]-tasks.md     ← 진행 체크리스트 (실시간 업데이트)
```

#### 운영 원칙

| 원칙 | 설명 |
|------|------|
| **선 문서화, 후 코딩** | Spec 승인 → "먼저 이 계획을 문서로 저장해" → 코딩 시작 |
| **마이크로 매니지먼트** | 한 번에 다 시키지 않고 Phase별 순차 진행 |
| **중간 체크** | 각 Phase 완료 시 "방금 한 거 체크하고 다음 할 일 정리해" |
| **맥락 복구** | 새 대화 시작 시 "dev/active/[task]/ 문서들 먼저 읽어" |

---

## 🪝 Phase 5: Hooks — 자동 품질 게이트

AI의 작업 흐름에 **자동 검증 포인트**를 삽입한다.
AI가 "다 했습니다"라고 해도 시스템이 한번 더 검증한다.

### settings.json 설정

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [{
          "type": "command",
          "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/skill-activation-prompt.sh"
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|MultiEdit|Write",
        "hooks": [{
          "type": "command",
          "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post-tool-use-tracker.sh"
        }]
      }
    ],
    "Stop": [
      {
        "hooks": [{
          "type": "command",
          "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/build-check.sh"
        }]
      }
    ]
  }
}
```

### 3대 핵심 훅

| 훅 | 이벤트 타이밍 | 역할 | 효과 |
|---|---|---|---|
| **skill-activation** | 작업 시작 전 (UserPromptSubmit) | 프롬프트 분석 → 관련 스킬 자동 제안 | 올바른 패턴 참조 강제 |
| **post-tool-tracker** | 파일 수정 직후 (PostToolUse) | 변경 파일 추적 → 맥락 유지 | 긴 대화 맥락 소실 방지 |
| **build-check** | 작업 완료 시 (Stop) | 빌드/린트 자동 검증 | 깨진 코드 방치 방지 |

### 추가: 셀프 체크 리마인더

훅 외에도 AI에게 작업 완료 시 스스로 던질 질문 목록을 설정:

```markdown
## 완료 시 자가 점검 (AI가 스스로 확인)
- "보안 위험은 없는가?"
- "에러 처리가 모든 경우에 되어 있는가?"
- "타입이 정확한가?"
- "Spec에서 요구한 검증 기준을 충족하는가?"
```

### Stop 훅 주의사항

- Stop 훅 실패 → 작업 종료 자체가 블록됨
- **반드시 수동 테스트 후 등록**
- 단순 프로젝트에서는 Stop 훅 생략 가능

---

## 📊 Phase 6: /insight — 데이터 기반 지속 개선

시스템을 고정하지 않고, AI의 성찰 기능으로 **지속적으로 최적화**한다.

### 활용 타이밍

2~4주간 사용 후 `/insight` 명령어 실행

### 분석 지표

| 지표 | 설명 | 활용법 |
|------|------|--------|
| **마찰 분석** | AI가 성급하게 행동하는 등 협업 방해 요소 파악 | 훅/에이전트 규칙 보완 |
| **만족도 평가** | 세션별 5단계 체점 | 저점 세션 원인 분석 |
| **맞춤형 규칙 제안** | 마찰 패턴 기반 설정 규칙 자동 생성 | skill-rules.json에 반영 |

### 주의사항

| ✅ 활용 | ❌ 주의 |
|---------|---------|
| AI가 제안하는 **경향성과 개선 패턴** | 구체적 **수치(세션 횟수 등)**는 부정확할 수 있음 |
| 마찰 지점 파악 → 규칙 추가 | 숫자에 의존하지 말 것 |

### 개선 루프

```
/insight 실행
    ↓
마찰 패턴 확인 (예: "코드 작성 전 Spec 확인 안 함")
    ↓
맞춤 규칙 추출
    ↓
skill-rules.json 또는 에이전트에 반영
    ↓
2~4주 후 다시 /insight → 반복
```

---

## 📐 DDD (도메인 주도 설계) — Phase 0~1에 관통하는 구조 원칙

### 핵심 비유: 편의점 진열대

음료는 음료 코너에, 과자는 과자 코너에.
비즈니스 개념(유저, 결제, 주문)별로 코드를 격리 관리.

### DDD 3파일 세트 (모든 도메인에 적용)

```
domain/[도메인명]/
├── model.py        ← Entity 정의 (데이터 구조)
├── repository.py   ← DB 접근 (꺼내오기/저장)
└── service.py      ← 비즈니스 로직 (규칙 처리)
```

### AI가 DDD에서 탁월한 이유

| 이유 | 설명 |
|------|------|
| **패턴 복제** | 첫 도메인(유저) 구조를 보고 다른 도메인(결제)을 정확히 복제 |
| **컨텍스트 집중** | 전체 코드가 아닌 해당 도메인 폴더만 보여줘서 정보량↓ 품질↑ |
| **환각 방지** | 비즈니스 용어 = 코드명이면 추측 의존도↓ 정확도↑ |

### DDD 실전 규칙

| # | 규칙 |
|---|------|
| 1 | **첫 도메인은 반드시 수동 작성** — AI에게 완벽한 패턴을 학습시킨다 |
| 2 | **비즈니스 언어 = 코드명** — 현업 용어를 그대로 함수명/파일명에 반영 |
| 3 | **도메인 간 격리** — A 도메인이 B 도메인의 repository를 직접 호출하지 않는다 |
| 4 | **패턴 복제 지시** — "유저 도메인 패턴 그대로 결제 도메인 만들어" |

---

## 📁 최종 디렉토리 구조 (전체 조감도)

```
프로젝트루트/
├── CLAUDE.md                          ← Phase 1: 프로젝트 기억
├── .claude/
│   ├── settings.json                  ← Phase 5: 훅 설정
│   ├── skills/
│   │   ├── skill-rules.json           ← Phase 3: 자동 활성화 규칙
│   │   ├── [backend]-guidelines/
│   │   │   ├── SKILL.md
│   │   │   └── resources/
│   │   ├── [frontend]-guidelines/
│   │   │   ├── SKILL.md
│   │   │   └── resources/
│   │   └── [domain]-specific/
│   │       └── SKILL.md
│   ├── agents/                        ← Phase 4: 전문 에이전트
│   │   ├── planner.md
│   │   ├── plan-reviewer.md
│   │   ├── code-architecture-reviewer.md
│   │   ├── auto-error-resolver.md
│   │   └── documentation-architect.md
│   ├── commands/
│   │   └── dev-docs.md
│   └── hooks/                         ← Phase 5: 자동 검증
│       ├── skill-activation-prompt.sh
│       ├── post-tool-use-tracker.sh
│       └── build-check.sh
├── dev/
│   └── active/                        ← Phase 4-B: 외부 기억 장치
│       └── [task]/
│           ├── [task]-plan.md
│           ├── [task]-context.md
│           └── [task]-tasks.md
└── domain/                            ← DDD 도메인 구조
    ├── user/
    │   ├── model.py
    │   ├── repository.py
    │   └── service.py
    ├── payment/
    │   ├── model.py
    │   ├── repository.py
    │   └── service.py
    └── order/
        ├── ...
```

---

## ✅ 통합 품질 체크리스트

### Phase 0: Spec 체크

- [ ] 기술 스택이 정확한 버전까지 명시되어 있는가?
- [ ] 모듈 경로가 복붙 가능한 수준으로 정확한가?
- [ ] 단계별 구현 계획이 Small Chunks로 나뉘어 있는가?
- [ ] 검증 방법이 실행 가능한 명령어로 되어 있는가?
- [ ] 성공 기준이 측정 가능한가?

### Phase 1: CLAUDE.md 체크

- [ ] 프로젝트 구조가 트리 형태로 명시되어 있는가?
- [ ] 실행 명령어가 복붙으로 바로 동작하는가?
- [ ] 흔한 실수 포인트가 경고로 명시되어 있는가?
- [ ] 핵심 함수/클래스명이 정확하게 기술되어 있는가?
- [ ] DDD 3파일 세트 패턴이 포함되어 있는가?

### Phase 3: skill-rules.json 체크

- [ ] 모든 스킬에 keyword + intentPattern + fileTrigger가 있는가?
- [ ] 한국어 + 영어 키워드가 모두 포함되어 있는가?
- [ ] pathPatterns가 실제 프로젝트 구조와 일치하는가?
- [ ] block 모드가 필요한 곳(보안, 호환성)에 적용되어 있는가?

### Phase 4: Agent + 기억 장치 체크

- [ ] planner + plan-reviewer가 존재하는가?
- [ ] 각 에이전트에 Success Criteria가 명시되어 있는가?
- [ ] 3대 문서(plan, context, tasks)가 작업 시작 전 생성되는가?
- [ ] tasks.md가 Phase 완료 시마다 업데이트되는가?

### Phase 5: Hook 체크

- [ ] skill-activation 훅이 UserPromptSubmit에 등록되어 있는가?
- [ ] post-tool-tracker가 PostToolUse에 등록되어 있는가?
- [ ] Stop 훅은 수동 테스트 후 등록했는가?

---

## 🔄 v1.0 → v2.0 변경 요약

| 영역 | v1.0 | v2.0 |
|------|------|------|
| **최우선 단계** | Phase 1 (CLAUDE.md) | **Phase 0 (SDD Spec)** ← 주문서 먼저 |
| **방향 통제** | planner 에이전트만 | **SDD 워크플로우 + planner 통합** |
| **DDD 위치** | Phase 2 Skills 내 | **별도 관통 원칙으로 격상** |
| **기억 장치** | 언급만 | **3대 문서 의무화 + 운영 원칙 구체화** |
| **품질 검증** | Hook 기반 | **Hook + 셀프 체크 리마인더 + 교차 검증** |
| **지속 개선** | 없음 | **/insight 기반 피드백 루프 추가** |
| **작업 단위** | "Small Chunks" 원칙 | **Phase별 마이크로 매니지먼트 구체화** |

---

## 🌐 멀티 IDE 호환 (선택)

| Claude Code | Cursor | Codex CLI | Antigravity |
|---|---|---|---|
| `CLAUDE.md` | `.cursor/rules/*.mdc` | `AGENTS.md` | `.agent/rules/*.md` |
| `.claude/skills/` | `.cursor/rules/` | AGENTS.md 섹션 | `.agent/skills/` |
| `.claude/agents/` | N/A | N/A | N/A |
| `CLAUDE.local.md` | Settings > Rules | `AGENTS.override.md` | `~/.gemini/GEMINI.md` |

---

## 📝 변경 이력

| 버전 | 날짜 | 주요 변경 |
|------|------|----------|
| v1.0 | 2026-02-23 | 초기 버전 — advanced-harness 구조 분석 기반 |
| v2.0 | 2026-02-24 | SDD(Spec Driven Development) 통합, DDD 관통 원칙 격상, 외부 기억 장치 의무화, /insight 피드백 루프, 셀프 체크 리마인더 추가 |

---

*"주문서(Spec) 없는 코딩은, 설계도 없는 건축과 같다."*
*"AI는 그냥 쓰면 50점, 시스템을 만들어주면 95점짜리 에이스가 된다."*
