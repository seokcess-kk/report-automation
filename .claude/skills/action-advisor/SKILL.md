# action-advisor

목표 달성 트래커용 데이터 + 규칙 기반 액션 제안 생성.

## 구조

```
scripts/
├── build_branch_pace.py     ← 지점별 월간 페이스 JSON 생성
└── generate_proposals.py    ← 규칙 엔진 — 액션 제안 JSON 생성
```

## 실행

```bash
# 단독 실행
python .claude/skills/action-advisor/scripts/build_branch_pace.py output/data/20260421
python .claude/skills/action-advisor/scripts/generate_proposals.py output/data/20260421

# 파이프라인 통합
python run_analysis.py   # Phase 3.5 에서 자동 실행
```

## 출력

### `branch_pace.json`
```json
{
  "updated": "2026-04-21",
  "month": "2026-04",
  "days_total": 30,
  "days_elapsed": 21,
  "date_progress": 70.0,
  "overall": { "budget_total", "cost_so_far", "budget_pct", "conv_target",
               "conv_so_far", "conv_pct", "proj_conv", "proj_pct", "status" },
  "branches": [ { "branch", "budget", "cost_so_far", "budget_pct",
                  "conv_target", "conv_so_far", "conv_pct", "proj_conv",
                  "proj_pct", "cpa", "target_cpa", "status", "sparkline" } ]
}
```

상태 신호등:
- `ok`    전환 페이스 ≥ 일자 진행률 AND CPA ≤ TARGET × 1.1
- `warn`  전환 10%p+ 지연 OR CPA TARGET × 1.1~1.5
- `danger` 전환 20%p+ 지연 OR CPA > TARGET × 1.5 OR 예산 오버페이스 20%p+

### `action_proposals.json`
```json
{
  "updated": "...",
  "proposals": [ { "id", "priority", "scope", "target", "action_type",
                    "title", "reason", "recommended_value", "evidence" } ]
}
```

## 규칙 (v1)

| # | 이름 | 조건 | 액션 | Priority |
|---|------|------|------|----------|
| 1 | 예산 오버페이스 | 소진-일자진행 > 15%p AND CPA > TARGET×1.2 | budget_decrease (-20%) | high |
| 2 | 예산 언더페이스 | 소진-일자진행 < -15%p AND CPA < TARGET | budget_increase (+20%) | medium |
| 3 | TIER4 장기 지속 | TIER4 AND 집행일수 ≥ 7일 | pause_creative | high |
| 4 | TIER1 신규 발견 | TIER1 AND 집행일수 ≤ 3일 | scale_creative | high |
| 5 | 나이대 저효율 | 예산효율점수 < 0.6 | exclude_age | medium |
| 6 | 나이대 고효율 | 예산효율점수 > 1.2 AND 비용비중 < 30% | expand_age | medium |

규칙 수정은 `scripts/generate_proposals.py` 상단 상수 블록에서.

## Phase 계획 연계

- **Phase 1** (현재): JSON 생성만 → 웹 대시보드 표시
- **Phase 2**: 제안 클릭 시 Dry-run 미리보기 (실제 TikTok API 호출 없음)
- **Phase 3**: 실 API 실행 + 감사 로그 + 롤백
