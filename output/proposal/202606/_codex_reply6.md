Reading prompt from stdin...
OpenAI Codex v0.130.0
--------
workdir: C:\Users\assag\solution\report-automation
model: gpt-5.5
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, C:\Users\assag\.codex\memories]
reasoning effort: medium
reasoning summaries: none
session id: 019e403e-8f47-7290-b281-79915f27eebc
--------
user
# 6차 — 히트맵 변동 진단: 운영 정책 매핑 + 최종 명세 합의

R5에서 핵심 골격(creative_type 분해 메인 + 신규/재개/OFF 보조 + interaction 별도 + 5월 partial flag)에 합의했습니다. 이번 R6은 **운영 정책 매핑 규칙** 확정과 **카드 한국어 톤 표준화**, **JSON 스키마 1차안 검증**입니다. 사용자가 강조한 "원인에 따라 운영 정책이 바뀐다"를 자동 생성 가능하도록 deterministic rule을 세우는 게 목표입니다.

## R5에서 확정된 사항 (재논의 불요)

```text
- 분해 명명: "구성비 효과(mix) · 단위성과 효과(within) · 상호작용항(interaction)"
- 분해 단위 메인: creative_type
- 보조 단위: ad_name (신규 / 재개 / 기존 3분류)
- CVR 가중치: click share (정의가 conversions/clicks이므로 — 확정)
- interaction <10%면 본문 생략, footnote 표기
- 5월 partial-month flag: 집행일수 또는 비용이 정상월 평균의 70% 미만
- CVR 톤: "전환 구간 점검 필요"로 부드럽게, 책임 단정 금지
- effect contribution: ≥40% 주요, 20~40% 보조, <20% 무시
- 최소 절대 변화: CPM ±10% 또는 ±1,000원 / CTR ±10% 또는 ±0.2%p / CVR ±15% 또는 ±0.5%p
- OFF 영향: 전월 우수 광고의 "전월 전환/비용 비중"으로 측정 (개수 아님)
```

## R6 검토 요청 — 1. 운영 정책 매핑 규칙 (핵심)

분해 결과를 정책 문장으로 자동 환원하는 규칙. 이게 사용자가 가장 중시하는 부분입니다 ("원인에 따라 정책이 바뀐다"). 카드 마지막 줄 "운영 함의"를 deterministic rule로 생성.

### CPM 상승(↑) 케이스

| 분해 패턴 | 정책 문장 (자동 생성) |
|----|----|
| mix 우세 (≥40%) + 특정 type 비중 증가 | "**{X형} 비중을 {현재}% → {목표}%로 환원** 시 CPM 약 {예상}원 회복 추정" |
| within 우세 (≥40%) + 정상월 | "동일 소재 단가 자체 상승. 입찰가·타겟 풀 포화 등 **광고 데이터 외부 요인** 확인 필요" |
| mix + within 동시 ≥30% | "소재 mix 환원 + 외부 요인 점검 병행" |
| partial-month flag | "5월 부분월 — 6월 정상 집행 후 재검증 필요" |

### CTR 변동 케이스

| 패턴 | 정책 |
|----|----|
| mix 우세 + 신규 광고 비중 ≥25% | "**신규 광고 학습 기간**의 자연 효과. 4주차까지 추세 모니터링" |
| mix 우세 + 신규 광고 비중 <25% | "{X형} 비중 변화가 CTR 변동의 {N}%를 설명. 비중 조정으로 의도적 운영 가능" |
| within 우세 | "동일 소재의 hooking 약화 또는 타겟 피로. **소재 갱신 또는 타겟 확장** 검토" |

### CVR 변동 케이스 (특수)

| 패턴 | 정책 |
|----|----|
| mix 우세 (≥40%) | "유입 mix 변화가 {N}%를 설명. 소재 배분 조정으로 회복 가능" |
| within 우세 (≥40%) | "광고 mix로는 {≤30}%만 설명. **클릭 이후 전환 구간**(랜딩·상담·예약 응대) 로그 대조 필요" |
| 양쪽 모두 약함 | "통계적 의미 변동이 아닌 자연 변동 범위로 추정. 다음 월 추세 재확인" |

**codex 검토**: 위 규칙이 deterministic하게 작동할 수 있는지, **추가해야 할 케이스나 누락된 분기**가 있는지. 특히 CPM/CTR/CVR의 **하락(↓) 방향**은 별도 표를 만들어야 하는지 (예: CPM 하락 시 정책 — "효율 개선이지만 노출 부족 가능성 점검") 또는 상승/하락 대칭 처리로 충분한지.

## R6 검토 요청 — 2. 카드 우선순위 정렬

±15% 이상 변동 셀이 30~50개 나올 수 있어 카드 6~9개로 선별 필요. 정렬 기준 옵션:

**A. 변화 크기 절대값 순** — |Δ%| 큰 순
**B. 운영 정책 시급도** — mix 우세(즉시 조치 가능) > within 우세(외부 점검) > partial-month
**C. 사용자 강조 트렌드 일치도** — 사용자가 짚은 "CPM 상승·CTR 상승·CVR 산포"와 일치하는 셀 우선
**D. 지점별 균형** — 한 지점이 카드 절반을 차지하지 않도록 지점당 max 2장

추천 조합 (검토 요청): **C → B → A** 순 정렬, 지점당 max 2장 cap.

## R6 검토 요청 — 3. 임계값 조건 결합 (AND/OR)

R5에서 변동 셀 인정 조건이 2개 제시되었는데 AND인지 OR인지 모호함:

```text
조건 A: 지점 자기평균 대비 ±15%
조건 B: 전월 또는 시작월 대비 ±15~20%
```

옵션:
- **A AND B 둘 다 만족** — 엄격, 카드 수 적어짐, 노이즈 강함
- **A OR B 중 하나** — 관대, 카드 수 많아짐
- **A 필수 + B는 카드 헤더 부가표기**(예: "vs 전월 +18%" 부기)

추천 (검토 요청): **A 필수 + B 부가표기**. A로 셀 선정, B는 카드에 trend 정보로 표시.

## R6 검토 요청 — 4. 최소 절대 변화 적용 — 모든 지표 동시 만족?

R5에서 제시된 최소 절대 변화:
```text
CPM: ±10% 또는 ±1,000원 이상
CTR: ±10% 또는 ±0.2%p 이상
CVR: ±15% 또는 ±0.5%p 이상
```

해석 옵션:
- **OR 결합**(현재 명시)** — ±10% 또는 ±1,000원: 둘 중 하나
- **AND 결합** — 둘 다 만족해야 변동 인정

작은 baseline일 때 비율이 과장되는 문제를 막으려면 절대값 기준이 의미 있고, 큰 baseline에서는 비율이 더 의미 있음. OR 결합이 맞아 보임 — 검증 요청.

## R6 검토 요청 — 5. JSON 스키마 1차안

`analyze_funnel_variance.py`가 출력할 JSON 구조 (build_proposal.py가 `DATA.funnel_variance`로 소비):

```jsonc
{
  "funnel_variance": {
    "overall_trend": {
      "cpm": {"first_month": "2026-02", "first_value": 8900, "last_month": "2026-05", "last_value": 11920, "delta_pct": 33.9, "partial_flag_last": true},
      "ctr": {...},
      "cvr": {...}
    },
    "cards": [
      {
        "branch": "서울",
        "metric": "cpm",
        "direction": "up",
        "month": "2026-04",
        "month_value": 11000,
        "baseline_value": 8900,         // 지점 자기평균
        "baseline_label": "지점 평균",
        "delta_pct": 23.6,
        "vs_prev_month_pct": 18.2,      // B 부가표기
        "partial_month_flag": false,
        "decomposition": {
          "mix_effect_pct": 18.0,        // 전체 변화 중 mix가 차지하는 %
          "within_effect_pct": 13.0,
          "interaction_pct": 3.0,
          "interaction_hidden": true     // <10% — 본문 생략
        },
        "mix_drivers": [                  // 상위 2개 type
          {"type": "의료진형", "share_delta_pp": 25.0, "type_metric_value": 13400, "vs_basket_pct": 46.0},
          {"type": "후기형",   "share_delta_pp": -22.0, "type_metric_value": 9200}
        ],
        "within_drivers": [               // 상위 2개 type
          {"type": "다이어트(여성)", "metric_delta_abs": 1800, "metric_delta_pct": 14.0}
        ],
        "aux_signals": [                  // 임계 통과한 보조 시그널만
          {"key": "new_resumed_share", "value_pct": 31.0, "threshold_pct": 25.0},
          {"key": "off_impact",         "value_pct": 18.0, "threshold_pct": 15.0, "off_creative_count": 2}
        ],
        "operation_implication": "의료진형 비중 30% 이하로 환원 시 CPM 약 9,300원 회복 추정. 동일 소재 단가 자체 상승은 외부 요인 점검 필요.",
        "implication_strength": "strong"  // partial-month면 "soft"
      },
      ...
    ],
    "computed_at": "2026-05-19T..."
  }
}
```

**검토**: 위 스키마가 카드 렌더링에 충분한지, 누락된 필드(예: type별 share 분포 전체, 보조 시그널의 원본 수치)가 있는지.

## R6 검토 요청 — 6. 본문 카드 한국어 톤 표준화

3개 샘플 (codex가 톤 검수해주세요):

### CPM 카드 (mix 우세)
```
[서울 · CPM ↑24%]  지점 평균 8,900원 → 4월 11,000원  (vs 전월 +18%)
─────────────────────────────────────────────────
구성비 효과 +18%p · 의료진형 비중 25%p 증가
                    (의료진형 CPM 13,400원 vs 평균 9,200원, +46%)
단위성과 효과 +13%p · 다이어트(여성)형 CPM 자체적으로 +1,800원 상승
보조 시그널 · 신규/재개 광고 노출 비중 31% (임계 25% 초과)

운영 함의 · 의료진형 비중을 30% 이하로 환원하면 CPM 약 9,300원 회복 추정.
            동일 소재 단가 상승은 외부 요인(입찰·타겟 풀) 점검 필요.
```

### CVR 카드 (within 우세)
```
[수원 · CVR ↓28%]  지점 평균 4.8% → 5월 3.5%  (vs 전월 -18%)  ⚠️ 5월 부분월
─────────────────────────────────────────────────
구성비 효과 -3%p  · 유입 mix 변화 설명력 낮음
단위성과 효과 -25%p · 동일 소재유형 내 CVR 자체 하락

운영 함의 · 광고 mix 조정으로는 변동의 12%만 설명됨.
            클릭 이후 단계(랜딩·5단계 폼·상담 응대) 로그 대조 우선 필요.
            5월 부분월 — 6월 정상 집행 구간에서 재검증 권장.
```

### CTR 카드 (mix 우세 + 신규 광고)
```
[일산 · CTR ↑22%]  지점 평균 0.92% → 4월 1.12%  (vs 전월 +24%)
─────────────────────────────────────────────────
구성비 효과 +0.13%p · 후기형 비중 18%p 증가 (후기형 CTR 1.35%)
단위성과 효과 +0.07%p · 의료진형 CTR 자체 +0.15%p 개선
보조 시그널 · 신규/재개 광고 노출 비중 28% (학습 기간 자연 효과)

운영 함의 · 후기형 비중 증가가 변동의 65%를 설명. 6월에도 유지 권장.
            신규 광고 학습 기간 효과가 일부 포함 — 6월 4주차까지 추세 재확인.
```

**검토**: 위 카드들이 (a) 데이터 기반 정확성 (b) 운영 정책 명확성 (c) 한국어 가독성 측면에서 적절한지. 어법·표현·과잉 단정·부족 단정 모두 코멘트 요청.

---

## 응답 가이드
- 결론 먼저, 6개 항목 순서대로
- 추가로 R5에서 놓친 issue가 있으면 마지막에 한두 가지만
- 한국어, 결정적으로

codex
결론: R6 방향은 거의 맞습니다. 다만 **운영 정책 매핑은 상승/하락을 완전 대칭 처리하면 안 됩니다.** 특히 CPM 하락, CTR 하락, CVR 상승은 운영 함의가 달라지므로 `metric × direction × decomposition_pattern`으로 분기하는 게 안전합니다.

## 1. 운영 정책 매핑 규칙

현재 규칙은 deterministic하게 구현 가능합니다. 단, 우선순위와 예외 순서를 명시해야 합니다.

추천 실행 순서:

1. `partial_month_flag = true`이면 정책 강도는 항상 `soft`
2. 최소 변동 조건 미충족이면 카드 생성 제외
3. decomposition contribution 기준으로 패턴 판정
4. metric + direction + pattern으로 정책 문장 생성
5. aux signal이 있으면 보조 문장 추가
6. interaction ≥10%이면 footnote 또는 별도 보조 설명 추가

패턴 판정은 이렇게 고정하는 것이 좋습니다.

```text
mix_dominant: abs(mix_effect_pct) >= 40
within_dominant: abs(within_effect_pct) >= 40
mixed: abs(mix_effect_pct) >= 30 and abs(within_effect_pct) >= 30
weak: 모두 20 미만 또는 절대 변화 미미
```

단, `effect_pct`는 부호가 아니라 **전체 변화 설명 비중** 기준이어야 합니다. 현재 JSON 예시는 `mix_effect_pct: 18.0`, `within_effect_pct: 13.0`처럼 보이는데, 이것이 “전체 변화 중 설명 비중”인지 “지표 변화량 기여도”인지 혼재될 위험이 있습니다. 둘을 분리하는 편이 안전합니다.

추천:

```jsonc
"decomposition": {
  "mix_delta_abs": 1800,
  "within_delta_abs": 1300,
  "interaction_delta_abs": 300,
  "mix_contribution_pct": 52.9,
  "within_contribution_pct": 38.2,
  "interaction_contribution_pct": 8.9
}
```

### 하락 방향 별도 표 필요 여부

필요합니다. 대칭 처리하면 운영 문장이 틀릴 수 있습니다.

### CPM ↓

| 패턴 | 정책 |
|---|---|
| mix 우세 + 저CPM type 비중 증가 | “저단가 소재유형 비중 증가로 CPM이 개선됨. 단, 노출량·전환 품질 저하 여부를 함께 확인” |
| within 우세 | “동일 소재 단가가 낮아진 구간. 입찰 경쟁 완화 또는 타겟 확장 영향 가능성 확인” |
| mix + within 동시 | “소재 mix 개선과 단가 하락이 함께 작용. 현재 배분 유지 가능하나 전환 품질 동반 점검” |
| partial-month | “부분월 영향 가능성이 있어 정상월 재검증 필요” |

### CTR ↓

| 패턴 | 정책 |
|---|---|
| mix 우세 | “저CTR 소재유형 비중 증가가 주요 원인. 고반응 유형 비중 회복 또는 저반응 유형 교체 검토” |
| within 우세 | “동일 소재의 반응률 약화. 소재 피로, 후킹 약화, 타겟 반복 노출 점검” |
| 신규 광고 비중 높음 | “신규 광고 학습 구간 영향 가능성. 4주차까지 추세 확인 후 교체 판단” |

### CVR ↑

| 패턴 | 정책 |
|---|---|
| mix 우세 | “전환 효율이 높은 유입 mix 증가가 개선을 설명. 해당 배분 유지 또는 확대 검토” |
| within 우세 | “동일 소재유형 내 전환 성과 개선. 랜딩·상담·예약 응대 개선 요인과 대조 필요” |
| 양쪽 약함 | “자연 변동 가능성. 다음 월 추세 확인” |

### CVR ↓

현재 제안 적절합니다. 특히 “책임 단정”을 피하고 “클릭 이후 전환 구간 로그 대조”로 표현한 점이 좋습니다.

추가로 CVR은 `new/resumed_share`를 과도하게 원인화하지 않는 게 좋습니다. 신규 광고는 CTR에는 직접 해석 가능하지만 CVR에서는 “유입 품질 변화 가능성” 정도의 보조 신호로만 두는 편이 안전합니다.

## 2. 카드 우선순위 정렬

추천안 **C → B → A + 지점당 max 2장 cap**에 동의합니다.

다만 B의 내부 우선순위는 약간 조정하는 게 좋습니다.

```text
1. 사용자가 강조한 트렌드 일치도
2. 운영 가능성
   - mix 우세 + 명확한 driver 있음
   - mixed
   - within 우세
   - partial-month only
3. 변화 크기
4. 지점당 max 2장
```

이유는 `within 우세`도 운영상 중요할 수 있지만, 자동 제안 가능한 액션은 `mix 우세`가 더 명확합니다. 단, CVR 하락 within 우세는 예외적으로 중요도를 높여야 합니다. 상담·랜딩 이슈 가능성이 있어 운영 영향이 큽니다.

추천 예외:

```text
CVR ↓ + within_dominant는 B에서 상위권
partial_month_flag=true는 기본적으로 후순위, 단 변화폭이 매우 크면 soft 카드로 유지
```

## 3. 임계값 조건 결합

추천안인 **A 필수 + B 부가표기**가 가장 적절합니다.

정리하면:

```text
카드 생성 조건:
- 지점 자기평균 대비 변동률 A가 임계값 이상
- 최소 절대 변화 조건 통과

카드 보조 표기:
- vs 전월
- vs 시작월 또는 first_month
```

이 방식이 좋은 이유는 “지점의 평소 수준 대비 이상치”를 기준으로 카드가 생성되고, 전월 대비 변화는 맥락 정보로 쓰이기 때문입니다.

다만 신규 지점이나 데이터가 짧은 지점은 예외가 필요합니다.

추천 fallback:

```text
if branch_history_months >= 3:
  baseline = branch_mean_excluding_current_partial
else:
  baseline = first_valid_month 또는 전체 지점 동일월 평균
```

그리고 `baseline_months_count`를 JSON에 넣는 것이 좋습니다.

## 4. 최소 절대 변화 적용

**OR 결합이 맞습니다.**

```text
CPM: abs(delta_pct) >= 10 OR abs(delta_abs) >= 1000
CTR: abs(delta_pct) >= 10 OR abs(delta_abs_pp) >= 0.2
CVR: abs(delta_pct) >= 15 OR abs(delta_abs_pp) >= 0.5
```

다만 이것만으로는 작은 baseline 문제를 완전히 막지 못합니다. 예를 들어 CTR 0.05% → 0.08%는 +60%지만 운영적으로는 작을 수 있습니다.

그래서 추천은:

```text
1차: 상대 변화 조건
2차: 절대 변화 조건
둘 중 하나 통과
단, baseline 자체가 너무 작은 경우는 min_sample_size 조건 필요
```

추가해야 할 조건:

```text
CPM: spend 또는 impressions 최소 기준
CTR: impressions 최소 기준
CVR: clicks 최소 기준
```

특히 CVR은 클릭 수가 작으면 변동이 쉽게 과장됩니다. 최소 클릭 수 기준 없이는 CVR 카드 품질이 흔들릴 가능성이 큽니다.

## 5. JSON 스키마 검토

현재 스키마는 카드 렌더링에는 거의 충분합니다. 다만 자동 정책 생성과 검증 가능성을 위해 몇 개 필드는 추가하는 게 좋습니다.

필수 추가 추천:

```jsonc
{
  "baseline": {
    "type": "branch_mean",
    "value": 8900,
    "months": ["2026-02", "2026-03", "2026-04"],
    "months_count": 3
  },
  "sample_size": {
    "spend": 1230000,
    "impressions": 140000,
    "clicks": 1280,
    "conversions": 45
  },
  "thresholds_passed": {
    "relative": true,
    "absolute": true,
    "sample_size": true
  },
  "policy_rule_id": "cpm_up_mix_dominant",
  "policy_inputs": {
    "dominant_driver": "의료진형",
    "current_share_pct": 55.0,
    "target_share_pct": 30.0,
    "estimated_recovered_value": 9300
  }
}
```

`operation_implication`만 저장하면 나중에 왜 그 문장이 나왔는지 추적하기 어렵습니다. `policy_rule_id`와 `policy_inputs`가 있으면 QA와 회귀 테스트가 쉬워집니다.

`mix_drivers`에는 현재 비중도 필요합니다.

```jsonc
{
  "type": "의료진형",
  "current_share_pct": 55.0,
  "baseline_share_pct": 30.0,
  "share_delta_pp": 25.0,
  "type_metric_value": 13400,
  "basket_metric_value": 9200,
  "vs_basket_pct": 46.0
}
```

`aux_signals`도 원본 분모를 넣는 게 좋습니다.

```jsonc
{
  "key": "new_resumed_share",
  "value_pct": 31.0,
  "threshold_pct": 25.0,
  "numerator_impressions": 43000,
  "denominator_impressions": 138000
}
```

OFF 영향은 개수보다 비중이 중요하다고 확정했으므로 `off_creative_count`는 보조로만 두고, 아래를 추가하는 게 좋습니다.

```jsonc
{
  "key": "off_impact",
  "prev_conversion_share_pct": 18.0,
  "prev_spend_share_pct": 22.0,
  "off_creative_count": 2
}
```

## 6. 카드 한국어 톤 표준화

전체 톤은 적절합니다. 데이터 기반, 운영 함의, 한국어 가독성 모두 괜찮습니다. 다만 몇 표현은 조금 더 안정적으로 바꾸는 것이 좋습니다.

### CPM 카드

현재 문장:

```text
의료진형 비중을 30% 이하로 환원하면 CPM 약 9,300원 회복 추정.
```

추천:

```text
의료진형 비중을 30% 수준으로 낮추면 CPM이 약 9,300원까지 완화될 가능성이 있습니다.
```

이유: “회복”은 좋은 상태로 돌아간다는 뉘앙스가 있어 CPM 상승/하락 맥락에서는 약간 애매합니다. “완화”가 더 정확합니다.

또 “외부 요인”은 좋지만 너무 넓으므로:

```text
입찰 경쟁, 타겟 풀 포화, 노출 지면 변화 등 광고 데이터 외부 요인 점검 필요
```

정도가 좋습니다.

### CVR 카드

현재 톤 좋습니다. 다만 “광고 mix 조정으로는 변동의 12%만 설명됨”은 강한 문장인데, 앞의 decomposition과 일치해야 합니다.

추천:

```text
광고 mix 변화로 설명되는 비중은 12% 수준입니다.
클릭 이후 단계(랜딩·5단계 폼·상담 응대) 로그 대조를 우선 권장합니다.
```

“우선 필요”보다 “우선 권장”이 덜 단정적입니다.

### CTR 카드

현재 문장:

```text
6월에도 유지 권장.
```

이건 다소 강합니다. CTR 상승이 전환 품질 저하를 동반할 수 있으므로 보완하는 게 좋습니다.

추천:

```text
후기형 비중 증가가 변동의 65%를 설명합니다. 전환 품질이 유지된다면 6월에도 현 배분을 유지할 수 있습니다.
신규 광고 학습 기간 효과가 일부 포함되어 6월 4주차까지 추세 재확인을 권장합니다.
```

CTR은 CVR이나 CPA와 같이 봐야 하므로 “유지 권장”보다 조건부 유지가 안전합니다.

## 추가로 R5/R6에서 놓치기 쉬운 이슈

1. **분해 contribution의 부호와 설명 비중을 분리해야 합니다.**  
   `+18%p`와 `변동의 65% 설명`은 다른 값입니다. JSON과 카드에서 혼용되면 정책 문장이 틀어질 수 있습니다.

2. **CVR에는 최소 클릭 수 기준이 필요합니다.**  
   CVR은 분모가 작으면 카드가 과생성됩니다. `clicks >= N` 또는 `conversions >= N` 기준을 반드시 두는 편이 좋습니다.
tokens used
13,839
결론: R6 방향은 거의 맞습니다. 다만 **운영 정책 매핑은 상승/하락을 완전 대칭 처리하면 안 됩니다.** 특히 CPM 하락, CTR 하락, CVR 상승은 운영 함의가 달라지므로 `metric × direction × decomposition_pattern`으로 분기하는 게 안전합니다.

## 1. 운영 정책 매핑 규칙

현재 규칙은 deterministic하게 구현 가능합니다. 단, 우선순위와 예외 순서를 명시해야 합니다.

추천 실행 순서:

1. `partial_month_flag = true`이면 정책 강도는 항상 `soft`
2. 최소 변동 조건 미충족이면 카드 생성 제외
3. decomposition contribution 기준으로 패턴 판정
4. metric + direction + pattern으로 정책 문장 생성
5. aux signal이 있으면 보조 문장 추가
6. interaction ≥10%이면 footnote 또는 별도 보조 설명 추가

패턴 판정은 이렇게 고정하는 것이 좋습니다.

```text
mix_dominant: abs(mix_effect_pct) >= 40
within_dominant: abs(within_effect_pct) >= 40
mixed: abs(mix_effect_pct) >= 30 and abs(within_effect_pct) >= 30
weak: 모두 20 미만 또는 절대 변화 미미
```

단, `effect_pct`는 부호가 아니라 **전체 변화 설명 비중** 기준이어야 합니다. 현재 JSON 예시는 `mix_effect_pct: 18.0`, `within_effect_pct: 13.0`처럼 보이는데, 이것이 “전체 변화 중 설명 비중”인지 “지표 변화량 기여도”인지 혼재될 위험이 있습니다. 둘을 분리하는 편이 안전합니다.

추천:

```jsonc
"decomposition": {
  "mix_delta_abs": 1800,
  "within_delta_abs": 1300,
  "interaction_delta_abs": 300,
  "mix_contribution_pct": 52.9,
  "within_contribution_pct": 38.2,
  "interaction_contribution_pct": 8.9
}
```

### 하락 방향 별도 표 필요 여부

필요합니다. 대칭 처리하면 운영 문장이 틀릴 수 있습니다.

### CPM ↓

| 패턴 | 정책 |
|---|---|
| mix 우세 + 저CPM type 비중 증가 | “저단가 소재유형 비중 증가로 CPM이 개선됨. 단, 노출량·전환 품질 저하 여부를 함께 확인” |
| within 우세 | “동일 소재 단가가 낮아진 구간. 입찰 경쟁 완화 또는 타겟 확장 영향 가능성 확인” |
| mix + within 동시 | “소재 mix 개선과 단가 하락이 함께 작용. 현재 배분 유지 가능하나 전환 품질 동반 점검” |
| partial-month | “부분월 영향 가능성이 있어 정상월 재검증 필요” |

### CTR ↓

| 패턴 | 정책 |
|---|---|
| mix 우세 | “저CTR 소재유형 비중 증가가 주요 원인. 고반응 유형 비중 회복 또는 저반응 유형 교체 검토” |
| within 우세 | “동일 소재의 반응률 약화. 소재 피로, 후킹 약화, 타겟 반복 노출 점검” |
| 신규 광고 비중 높음 | “신규 광고 학습 구간 영향 가능성. 4주차까지 추세 확인 후 교체 판단” |

### CVR ↑

| 패턴 | 정책 |
|---|---|
| mix 우세 | “전환 효율이 높은 유입 mix 증가가 개선을 설명. 해당 배분 유지 또는 확대 검토” |
| within 우세 | “동일 소재유형 내 전환 성과 개선. 랜딩·상담·예약 응대 개선 요인과 대조 필요” |
| 양쪽 약함 | “자연 변동 가능성. 다음 월 추세 확인” |

### CVR ↓

현재 제안 적절합니다. 특히 “책임 단정”을 피하고 “클릭 이후 전환 구간 로그 대조”로 표현한 점이 좋습니다.

추가로 CVR은 `new/resumed_share`를 과도하게 원인화하지 않는 게 좋습니다. 신규 광고는 CTR에는 직접 해석 가능하지만 CVR에서는 “유입 품질 변화 가능성” 정도의 보조 신호로만 두는 편이 안전합니다.

## 2. 카드 우선순위 정렬

추천안 **C → B → A + 지점당 max 2장 cap**에 동의합니다.

다만 B의 내부 우선순위는 약간 조정하는 게 좋습니다.

```text
1. 사용자가 강조한 트렌드 일치도
2. 운영 가능성
   - mix 우세 + 명확한 driver 있음
   - mixed
   - within 우세
   - partial-month only
3. 변화 크기
4. 지점당 max 2장
```

이유는 `within 우세`도 운영상 중요할 수 있지만, 자동 제안 가능한 액션은 `mix 우세`가 더 명확합니다. 단, CVR 하락 within 우세는 예외적으로 중요도를 높여야 합니다. 상담·랜딩 이슈 가능성이 있어 운영 영향이 큽니다.

추천 예외:

```text
CVR ↓ + within_dominant는 B에서 상위권
partial_month_flag=true는 기본적으로 후순위, 단 변화폭이 매우 크면 soft 카드로 유지
```

## 3. 임계값 조건 결합

추천안인 **A 필수 + B 부가표기**가 가장 적절합니다.

정리하면:

```text
카드 생성 조건:
- 지점 자기평균 대비 변동률 A가 임계값 이상
- 최소 절대 변화 조건 통과

카드 보조 표기:
- vs 전월
- vs 시작월 또는 first_month
```

이 방식이 좋은 이유는 “지점의 평소 수준 대비 이상치”를 기준으로 카드가 생성되고, 전월 대비 변화는 맥락 정보로 쓰이기 때문입니다.

다만 신규 지점이나 데이터가 짧은 지점은 예외가 필요합니다.

추천 fallback:

```text
if branch_history_months >= 3:
  baseline = branch_mean_excluding_current_partial
else:
  baseline = first_valid_month 또는 전체 지점 동일월 평균
```

그리고 `baseline_months_count`를 JSON에 넣는 것이 좋습니다.

## 4. 최소 절대 변화 적용

**OR 결합이 맞습니다.**

```text
CPM: abs(delta_pct) >= 10 OR abs(delta_abs) >= 1000
CTR: abs(delta_pct) >= 10 OR abs(delta_abs_pp) >= 0.2
CVR: abs(delta_pct) >= 15 OR abs(delta_abs_pp) >= 0.5
```

다만 이것만으로는 작은 baseline 문제를 완전히 막지 못합니다. 예를 들어 CTR 0.05% → 0.08%는 +60%지만 운영적으로는 작을 수 있습니다.

그래서 추천은:

```text
1차: 상대 변화 조건
2차: 절대 변화 조건
둘 중 하나 통과
단, baseline 자체가 너무 작은 경우는 min_sample_size 조건 필요
```

추가해야 할 조건:

```text
CPM: spend 또는 impressions 최소 기준
CTR: impressions 최소 기준
CVR: clicks 최소 기준
```

특히 CVR은 클릭 수가 작으면 변동이 쉽게 과장됩니다. 최소 클릭 수 기준 없이는 CVR 카드 품질이 흔들릴 가능성이 큽니다.

## 5. JSON 스키마 검토

현재 스키마는 카드 렌더링에는 거의 충분합니다. 다만 자동 정책 생성과 검증 가능성을 위해 몇 개 필드는 추가하는 게 좋습니다.

필수 추가 추천:

```jsonc
{
  "baseline": {
    "type": "branch_mean",
    "value": 8900,
    "months": ["2026-02", "2026-03", "2026-04"],
    "months_count": 3
  },
  "sample_size": {
    "spend": 1230000,
    "impressions": 140000,
    "clicks": 1280,
    "conversions": 45
  },
  "thresholds_passed": {
    "relative": true,
    "absolute": true,
    "sample_size": true
  },
  "policy_rule_id": "cpm_up_mix_dominant",
  "policy_inputs": {
    "dominant_driver": "의료진형",
    "current_share_pct": 55.0,
    "target_share_pct": 30.0,
    "estimated_recovered_value": 9300
  }
}
```

`operation_implication`만 저장하면 나중에 왜 그 문장이 나왔는지 추적하기 어렵습니다. `policy_rule_id`와 `policy_inputs`가 있으면 QA와 회귀 테스트가 쉬워집니다.

`mix_drivers`에는 현재 비중도 필요합니다.

```jsonc
{
  "type": "의료진형",
  "current_share_pct": 55.0,
  "baseline_share_pct": 30.0,
  "share_delta_pp": 25.0,
  "type_metric_value": 13400,
  "basket_metric_value": 9200,
  "vs_basket_pct": 46.0
}
```

`aux_signals`도 원본 분모를 넣는 게 좋습니다.

```jsonc
{
  "key": "new_resumed_share",
  "value_pct": 31.0,
  "threshold_pct": 25.0,
  "numerator_impressions": 43000,
  "denominator_impressions": 138000
}
```

OFF 영향은 개수보다 비중이 중요하다고 확정했으므로 `off_creative_count`는 보조로만 두고, 아래를 추가하는 게 좋습니다.

```jsonc
{
  "key": "off_impact",
  "prev_conversion_share_pct": 18.0,
  "prev_spend_share_pct": 22.0,
  "off_creative_count": 2
}
```

## 6. 카드 한국어 톤 표준화

전체 톤은 적절합니다. 데이터 기반, 운영 함의, 한국어 가독성 모두 괜찮습니다. 다만 몇 표현은 조금 더 안정적으로 바꾸는 것이 좋습니다.

### CPM 카드

현재 문장:

```text
의료진형 비중을 30% 이하로 환원하면 CPM 약 9,300원 회복 추정.
```

추천:

```text
의료진형 비중을 30% 수준으로 낮추면 CPM이 약 9,300원까지 완화될 가능성이 있습니다.
```

이유: “회복”은 좋은 상태로 돌아간다는 뉘앙스가 있어 CPM 상승/하락 맥락에서는 약간 애매합니다. “완화”가 더 정확합니다.

또 “외부 요인”은 좋지만 너무 넓으므로:

```text
입찰 경쟁, 타겟 풀 포화, 노출 지면 변화 등 광고 데이터 외부 요인 점검 필요
```

정도가 좋습니다.

### CVR 카드

현재 톤 좋습니다. 다만 “광고 mix 조정으로는 변동의 12%만 설명됨”은 강한 문장인데, 앞의 decomposition과 일치해야 합니다.

추천:

```text
광고 mix 변화로 설명되는 비중은 12% 수준입니다.
클릭 이후 단계(랜딩·5단계 폼·상담 응대) 로그 대조를 우선 권장합니다.
```

“우선 필요”보다 “우선 권장”이 덜 단정적입니다.

### CTR 카드

현재 문장:

```text
6월에도 유지 권장.
```

이건 다소 강합니다. CTR 상승이 전환 품질 저하를 동반할 수 있으므로 보완하는 게 좋습니다.

추천:

```text
후기형 비중 증가가 변동의 65%를 설명합니다. 전환 품질이 유지된다면 6월에도 현 배분을 유지할 수 있습니다.
신규 광고 학습 기간 효과가 일부 포함되어 6월 4주차까지 추세 재확인을 권장합니다.
```

CTR은 CVR이나 CPA와 같이 봐야 하므로 “유지 권장”보다 조건부 유지가 안전합니다.

## 추가로 R5/R6에서 놓치기 쉬운 이슈

1. **분해 contribution의 부호와 설명 비중을 분리해야 합니다.**  
   `+18%p`와 `변동의 65% 설명`은 다른 값입니다. JSON과 카드에서 혼용되면 정책 문장이 틀어질 수 있습니다.

2. **CVR에는 최소 클릭 수 기준이 필요합니다.**  
   CVR은 분모가 작으면 카드가 과생성됩니다. `clicks >= N` 또는 `conversions >= N` 기준을 반드시 두는 편이 좋습니다.
