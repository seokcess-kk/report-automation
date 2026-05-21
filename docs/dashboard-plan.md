# 6월 TikTok 운영 콘솔 — 기획안

> 작성일: 2026-05-21 (v2 — 사용자 피드백 반영) · 목표: 대행사 운영자가 6월 운영안의 액션을 매일 실행 단위로 쪼개고 KPI·이상 신호·액션 효과를 추적하는 내부 운영 도구

---

## 1. 솔루션 정의

**6월 TikTok 운영 콘솔**은 "대시보드(분석 결과 조회)"가 아닌 **운영 콘솔(실행 큐 + 효과 추적)**입니다. 분석 결과는 보여주는 부산물일 뿐, 핵심은 다음 3개:

1. **오늘 실행할 액션 큐** (광고 ON/OFF·예산 조정·세팅 확인)
2. **수행한 액션의 변경 이력 + 사후 효과 추적** (D+1/D+3/D+7)
3. **운영 룰 기반 자동 상태 평가** (사람이 룰을 정의, 데이터가 상태 계산)

---

## 2. 운영자 use case (홈 5분 안에 결정)

운영자가 홈 화면에서 결정해야 하는 4가지:

1. **오늘 예산을 늘릴 지점**
2. **오늘 예산을 줄이거나 보류할 지점**
3. **OFF 후보 소재**
4. **반드시 확인해야 할 세팅/예외 이슈**

(분석 보고서 톤이 아니라 **실행 큐**로 표현)

---

## 3. 홈 화면 구조 (4개 영역)

```
┌── 3.1 오늘의 결론 (요약 헤드) ────────────────────────┐
│ 정상 ○지점 · 주의 ○지점 · 긴급 ○지점                  │
│ 오늘 실행 필요 액션 ○건 · 6월 목표 페이스 ○○%          │
└─────────────────────────────────────────────────────┘
┌── 3.2 오늘 해야 할 일 (실행 큐) ──────────────────────┐
│ 💰 예산 조정    │ • 부평 +10% (CPA 우수 + 노출 여유)   │
│                 │ • 천안 -10% (가드레일 초과)           │
│ 🎬 소재 ON/OFF  │ • OFF: ad_id 123 (CPA 7만/CVR 1%)    │
│                 │ • ON:  (신)_식욕억제주사실패…         │
│ ⚙️  세팅 확인   │ • 천안 광고그룹 지역 타겟팅 점검       │
│ ⏸  보류·관찰   │ • 25-34 수원 한정 — D+7 결과 대기     │
└─────────────────────────────────────────────────────┘
┌── 3.3 이상 신호 (3가지 기준 병행) ────────────────────┐
│ 🔴 천안: CPA 3일 MA 가드레일 +24%                     │
│ 🟡 인플방문후기_X: CVR 전일 -32% (단, 클릭 28 — 보류)  │
│ 🔴 전환 페이스 목표 대비 82% (액션 필요)               │
│ ✓  25-34 수원: D+3 CVR 1.9%로 회복 추세                │
└─────────────────────────────────────────────────────┘
┌── 3.4 액션 후 효과 추적 ──────────────────────────────┐
│ 6/01 천안 예산 -10% → D+1 CPA 17K (-22%)            │
│ 5/30 ad_id 123 OFF → D+3 측정 대기                   │
│ 5/28 ad_id 456 ON  → D+7 CVR 8.2% (예상치 달성)      │
└─────────────────────────────────────────────────────┘
```

---

## 4. 운영 룰 정의표 (Phase 1 시작 전 필수)

화면 와이어프레임보다 **언제 무엇을 할지** 수치 기준 정의가 먼저. 매일 같은 판단을 가능하게 하는 핵심 자산.

`config/operation_rules.yaml`:

### 4.1 예산 조정 룰
```yaml
budget_increase:
  - condition: cpa_3day_avg <= target_cpa * 0.85 AND impression_share < 0.70
    action: 광고 그룹 예산 +10% 점진 증액
    stop_if: cpa_today > target_cpa * 1.10 OR cpm_jump_pct > 15

budget_decrease:
  - condition: cpa_3day_avg > target_cpa * 1.20 OR cvr_3day_avg < target_cvr * 0.70
    action: 광고 그룹 예산 -10%
  - condition: target_pace_pct < 0.85 AND days_remaining < 7
    action: 광고 그룹 예산 -20% (가드레일 우선)
```

### 4.2 광고 단위 ON/OFF 룰
```yaml
ad_off_candidate:
  - condition: tier == TIER4 AND days_active >= 7 AND cpa > target_cpa * 1.5
    priority: high
  - condition: cvr_3day_avg < 1.0 AND clicks >= 100 AND cost >= 100000
    priority: high
  - condition: 광고 그룹 평균 CVR 대비 50% 미만
    priority: medium

ad_on_candidate:
  - condition: tier == TIER1 AND impression_share < 0.10 (확장 여지)
    action: 동일 지점 다른 광고 그룹에 복제
```

### 4.3 세팅 확인 룰
```yaml
setting_alert:
  - condition: branch == 천안 AND province_leakage_pct > 15
    action: 지역 타겟팅 광역 설정 점검
  - condition: targeting_health.age_signal == inefficient
    action: 해당 연령대 타겟팅 제외 확인
  - condition: gender_male_impr_pct > 0
    action: 성별 타겟팅 여성 고정 확인
```

### 4.4 보류·관찰 룰 (판단 보류 신호)
```yaml
hold_observation:
  - condition: clicks < 30
    reason: 표본 부족 — 판단 보류
  - condition: days_active < 7
    reason: 학습 기간 부족 — 7일 도달 시 재평가
  - condition: tier == LOW_VOLUME OR UNCLASSIFIED
    reason: 운영 데이터 누적 중
```

### 4.5 클라이언트 확인 요청 룰
```yaml
client_escalation:
  - condition: 가드레일 초과 3일 연속 AND 액션 후 회복 불가
    action: 클라이언트 보고 (소재 메시지 변경 등 운영 외 결정 요청)
  - condition: 랜딩 폼 이탈률 추정 > 50% (LPV/clicks < 50%)
    action: 클라이언트 랜딩 점검 요청
```

---

## 5. 체크리스트 시스템 (사람 정의 + 데이터 자동 평가)

**원칙**: 제안서 JSON 자동 추출 ❌ → **`config/june_checklist.yaml`에 사람이 정의 + 상태는 데이터가 자동 계산**.

이유: 제안서 문장은 보고용, 운영 체크리스트는 실행 단위가 더 명확해야.

### 5.1 체크리스트 항목 스키마
```yaml
- id: addon_v2_v1_split
  title: v2 유지 그룹과 v1 복원·부분 변경 그룹 분리 운영
  owner: operator
  week: W1                            # W1~W4
  related_section: "5.3"              # 제안서 참조
  success_metric: cvr
  target: "D+7 CVR 회복 여부"
  status_rule: addon_design_test      # 4.x 룰 ID
  manual_override: false              # 운영자가 수동 토글 가능 여부

- id: cheonan_geo_setting
  title: 천안 광고그룹 지역 타겟팅 광역 설정 점검
  owner: operator
  week: W1
  related_section: 부록 B
  status_rule: geo_leakage_resolved   # 룰: 천안 누수 < 15%면 ✓
  manual_override: true

- id: age_25_34_suwon_tracking
  title: 25-34 수원 한정 테스트 결과 추적
  owner: operator
  week: W2-W3
  related_section: 부록 A
  status_rule: age_test_recovery      # 룰: 수원 25-34 CVR D+7 회복
  manual_override: false
```

### 5.2 상태 자동 평가
`checklist_engine.py`가 데이터를 보고 룰별 상태 계산:
- ✓ 완료 (success_metric 도달)
- 🔄 진행 중 (운영 시작했지만 measure 기간 미도달)
- ⚠️ 부분 진행 (target 미달)
- ☐ 미시작 (운영 흔적 없음)

운영자가 `manual_override: true` 항목은 수동 토글 가능.

---

## 6. 액션 트래커 (Phase 1 MVP 포함)

운영 솔루션의 핵심은 **"무슨 액션을 했고 효과가 있었는가"**. Phase 2로 미루지 않고 MVP부터 포함.

### 6.1 단순화된 스키마

`output/tracker/actions.jsonl` (append-only):

```json
{
  "date": "2026-06-03",
  "timestamp": "2026-06-03T09:30:00",
  "action_type": "budget_change | ad_off | ad_on | creative_swap | setting_change",
  "branch": "천안",
  "ad_id": null,
  "creative_name": null,
  "before": "daily_budget 70000",
  "after": "daily_budget 50000",
  "reason": "CPA 가드레일 초과 + 경기 누수 확인",
  "expected_metric": "CPA",
  "review_after_days": [1, 3, 7],
  "operator": "agency"
}
```

처음엔 **수동 로그**여도 OK. 자동 실행보다 변경 이력과 사후 평가가 우선.

### 6.2 효과 추적

`workers/effect_tracker.py` 매일 03:30 실행:
- `actions.jsonl`에서 `review_after_days` 미평가 항목 찾기
- D+N 시점의 데이터로 expected_metric 변동 계산
- 결과를 `actions.jsonl` 같은 줄에 `effects` 필드로 append (rewrite)

---

## 7. 이상 신호 감지 (3가지 기준 병행)

전일비만으로는 노이즈가 큼 — 3가지 기준 동시 평가:

### 7.1 감지 룰
| 기준 | 용도 | 임계값 (default) |
|------|------|------------------|
| **전일비** | 급변 감지 | CPA +30% / CVR -30% |
| **3일 이동평균** | 추세 감지 | CPA 3일 MA가 가드레일 +20% |
| **6월 목표 페이스** | 미달 감지 | 누적 전환 / 목표 페이스 < 85% |

### 7.2 노이즈 필터
- 클릭 < 30 → 표본 부족, 신호 보류
- 광고 그룹 신규 (집행 < 7일) → 학습 기간, 신호 보류

### 7.3 신호 등급
- 🔴 Critical: 3일 MA가 가드레일 초과 OR 전환 페이스 < 80%
- 🟡 Warning: 전일 급변이지만 3일 MA는 정상
- ✓ Recovery: 직전 신호가 해소된 경우 (긍정 알림)

설정 파일: `config/alert_rules.yaml`

---

## 8. 기술 스택 (이미 있는 web/ Next.js 고려)

### 8.1 기존 자산 확인
- `web/` Next.js 14 + React 18 + Tailwind + Recharts + lucide-react
- 이미 운영 UI 후보가 존재

### 8.2 단계별 전략 (Phase 1 = Flask, Phase 3 = web/ 이전)

| Phase | 스택 | 이유 |
|-------|------|------|
| **Phase 1 MVP** | `dashboard/` Flask | 기존 Python 분석 코드 직접 재사용, 1주 안에 빠른 구축 |
| **Phase 3 장기** | `web/` Next.js에 운영 탭 추가 | 운영 UI 통합, 더 풍부한 인터랙션 |

**핵심**: Phase 1에서 services/ 분리해서 **Phase 3 이전 시 services 로직만 API endpoint로 노출하면 web/이 호출 가능**한 구조로 설계.

### 8.3 디렉토리 구조

```
report-automation/
├── dashboard/                       ← Phase 1 Flask
│   ├── app.py                       ← Flask 부트 + 라우트
│   ├── services/                    ← API/계산 로직 (web/ 이전 시 그대로 재사용)
│   │   ├── data_loader.py
│   │   ├── kpi_progress.py
│   │   ├── alert_engine.py          ← 7장 룰 평가
│   │   ├── checklist_engine.py      ← 5장 상태 자동 평가
│   │   ├── action_recommender.py
│   │   └── action_tracker.py
│   ├── workers/
│   │   └── effect_tracker.py        ← D+1/D+3/D+7 자동 계산
│   ├── templates/
│   │   └── home.html
│   ├── static/
│   │   └── dashboard.css
│   └── api/                         ← Phase 3 web/ 이전 대비 JSON 응답 endpoint
│       ├── kpi.py
│       ├── alerts.py
│       └── ...
├── config/
│   ├── operation_rules.yaml         ← 4장 운영 룰
│   ├── june_checklist.yaml          ← 5장 체크리스트 정의
│   └── alert_rules.yaml             ← 7장 신호 임계값
└── output/
    └── tracker/
        ├── actions.jsonl            ← 6장 액션 로그
        └── checklist_state.json     ← 체크박스 상태 (수동 override)
```

---

## 9. Phase 1 MVP 작업 분해 (1주)

순서:

1. **`config/` 3개 YAML 정의** — 운영 룰 / 체크리스트 / 알림 임계값 — 가장 먼저
2. **`services/data_loader.py`** — 최신 dir 자동 감지 + parquet/JSON 캐시
3. **`services/kpi_progress.py`** — KPI 진행률 + 페이스 + 예상 도달
4. **`services/alert_engine.py`** — 3가지 기준(전일비/3일 MA/페이스) 병행
5. **`services/checklist_engine.py`** — YAML 항목 + 상태 자동 평가
6. **`services/action_recommender.py`** — 운영 룰 기반 큐 생성 (예산 조정/ON·OFF/세팅/보류)
7. **`services/action_tracker.py`** — POST /tracker/log → actions.jsonl
8. **`workers/effect_tracker.py`** — D+1/D+3/D+7 효과 자동 측정
9. **`templates/home.html`** — 4개 영역 통합 렌더링
10. **수동 테스트** — 실제 운영자가 5분 안에 4개 결정 가능한지 검증

---

## 10. Phase 2~3

### Phase 2 — 드릴다운 (2주차)
- `/branch/<지점>`, `/creative/<소재>` 페이지
- 액션 트래커 archive 페이지
- 체크리스트 상세 + 수동 메모

### Phase 3 — 통합 + 확장 (3주차+)
- **`web/` Next.js로 이전** (services는 그대로, UI만 React)
- Slack/이메일 알림
- 클라우드 배포 (Railway/Render/Vercel)
- 운영자 다중 + RBAC

---

## 11. Phase 1 시작 전 추가 확인 (남은 미정)

| # | 미정 항목 | 결정 시점 |
|---|----------|----------|
| 1 | Flask 포트 (5000? 8080?) | 작업 #2 (data_loader) 시작 시 |
| 2 | 운영자 식별 (단일 vs 다중) | YAML 작성 시 |
| 3 | operation_rules.yaml 초기 임계값 (target_cpa/cvr 등) | 작업 #1에서 함께 확정 |
| 4 | 체크리스트 초기 항목 수 (W1~W4 각 몇 개?) | 작업 #1에서 함께 확정 |
| 5 | 첫 실행 시 액션 트래커 history 인입 (기존 로그 없으면 빈 상태) | 작업 #7 시 |

---

## 12. 다음 단계

Phase 1 시작 결정 시:
1. **`config/operation_rules.yaml` + `config/june_checklist.yaml` + `config/alert_rules.yaml` 3개 초안 함께 작성** — 가장 먼저
2. 작업 #2부터 순차 진행
3. 매 services 모듈 완료 시 단위 테스트 + 사용자 피드백
