# 히트맵 변동 진단 — 최종 합의 명세 (R5~R7 종합)

codex와 3라운드 비평 후 도출된 구현 명세. 사용자(seokcess)가 강조한 **"애매한 추측이 아닌 데이터 기반 정확한 원인 진단 → 운영 정책 분기"**를 deterministic하게 자동 생성하는 로직.

---

## 핵심 한 줄
**월 단위 KPI 변화를 `구성비 효과(mix) · 단위성과 효과(within) · 상호작용항(interaction)` 셋으로 산술 분해하고, 분해 패턴과 보조 시그널에 따라 운영 정책 문장을 deterministic하게 자동 환원한다.**

---

## 1. 분해 정의

```
metric ∈ {CPM, CTR, CVR}
direction ∈ {up, down}
group_by = creative_type (메인) / 보조: ad_name (신규/재개/기존)

CPM_total = Σ_j (impression_share_j × CPM_j)
CTR_total = Σ_j (impression_share_j × CTR_j)
CVR_total = Σ_j (click_share_j × CVR_j)         # CVR = conversions/clicks×100 확정

ΔKPI(month → branch_mean) =
    mix_delta      = Σ_j (Δshare_j × KPI_j_baseline)
  + within_delta   = Σ_j (share_j_current × ΔKPI_j)
  + interaction    = Σ_j (Δshare_j × ΔKPI_j)
```

설명 비중 (= 효과 구성비, 라벨 고정):
```
contribution_pct = abs(effect_delta) / (|mix| + |within| + |interaction|) × 100
```

---

## 2. 카드 생성 필터 (4단 게이트)

셀 = (branch, metric, month) 단위. 게이트를 순서대로 통과해야 카드 생성:

### Gate 1. 최소 샘플 사이즈 (옵션 B 균형)
```
CPM: impressions ≥ 20,000
CTR: impressions ≥ 20,000
CVR: clicks ≥ 100
```
미충족 → 카드 생성 안 함 (조용히 누락).

### Gate 2. 변동 셀 인정 (상대 + 절대 OR)
```
baseline = 해당 지점 자기평균 (history ≥ 3개월) / 또는 first_valid_month·전 지점 동일월 fallback
조건: |Δ vs baseline %| ≥ 임계 OR |Δ vs baseline abs| ≥ 임계
  CPM: 10% OR 1,000원
  CTR: 10% OR 0.2%p
  CVR: 15% OR 0.5%p
```

### Gate 3. 패턴 판정 (contribution_pct 기준)
```
mix_dominant:    mix_contrib ≥ 40
within_dominant: within_contrib ≥ 40
mixed:           mix_contrib ≥ 30 AND within_contrib ≥ 30
weak:            모두 < 20 (또는 abs Δ 너무 작음)
```
**weak는 본문 카드 미생성 — appendix에만 기록.**

### Gate 4. partial-month flag
```
집행일수 < 정상월 평균의 70% OR 비용 < 정상월 평균의 70%
→ flag=true 시 정책 강도 "soft", 카드는 ⚠️ caution badge
```

---

## 3. 운영 정책 매핑 표 (6 × N 패턴)

각 정책 문구는 `policy_rule_id`로 식별, `policy_inputs`에 변수 저장.

### CPM ↑
| 패턴 | rule_id | 운영 함의 |
|---|---|---|
| mix_dominant + 고CPM type 비중↑ | `cpm_up_mix_dominant` | "{X형} 비중을 {target}% 수준으로 낮추면 CPM 약 {est}원까지 완화될 가능성" |
| within_dominant | `cpm_up_within_dominant` | "동일 소재 단가 자체 상승. 입찰 경쟁·타겟 풀 포화·노출 지면 변화 등 광고 외부 요인 점검 필요" |
| mixed | `cpm_up_mixed` | "소재 mix 환원 + 외부 요인 점검 병행" |
| partial-month | `cpm_up_partial` | "5월 부분월 — 6월 정상 집행 구간 재검증 필요" (soft) |

### CPM ↓
| 패턴 | rule_id | 운영 함의 |
|---|---|---|
| mix_dominant + 저CPM type 비중↑ | `cpm_down_mix_dominant` | "저단가 소재유형 비중 증가로 CPM 개선. 노출량·전환 품질 동반 점검" |
| within_dominant | `cpm_down_within_dominant` | "동일 소재 단가 하락. 입찰 경쟁 완화·타겟 확장 영향 가능성 확인" |
| mixed | `cpm_down_mixed` | "mix 개선 + 단가 하락 동시 작용. 현 배분 유지 가능하나 전환 품질 점검" |

### CTR ↑
| 패턴 | rule_id | 운영 함의 |
|---|---|---|
| mix_dominant + 신규광고 비중 ≥25% | `ctr_up_new_learning` | "신규 광고 학습 기간 자연 효과. 4주차까지 추세 모니터링" |
| mix_dominant + 신규광고 <25% | `ctr_up_mix_dominant` | "{X형} 비중 변화가 변동의 {N}% 설명. 의도적 운영 가능. 전환 품질 유지 시 6월 현 배분 유지 가능" |
| within_dominant | `ctr_up_within_dominant` | "동일 소재의 반응률 자체 개선. 6월에도 동일 소재 유지 가능, 단 피로도 확인" |

### CTR ↓
| 패턴 | rule_id | 운영 함의 |
|---|---|---|
| mix_dominant | `ctr_down_mix_dominant` | "저CTR 유형 비중 증가가 주원인. 고반응 유형 비중 회복 또는 저반응 유형 교체 검토" |
| within_dominant | `ctr_down_within_dominant` | "동일 소재 반응률 약화. 소재 피로·후킹 약화·타겟 반복 노출 점검" |
| 신규광고 ≥25% | `ctr_down_new_learning` | "신규 광고 학습 구간 영향 가능성. 4주차까지 추세 확인 후 교체 판단" |

### CVR ↑
| 패턴 | rule_id | 운영 함의 |
|---|---|---|
| mix_dominant | `cvr_up_mix_dominant` | "전환 효율 높은 유입 mix 증가. 해당 배분 유지·확대 검토" |
| within_dominant | `cvr_up_within_dominant` | "동일 소재유형 내 전환 성과 개선. 랜딩·상담·예약 응대 개선 요인 대조" |
| weak (양쪽 약함) | (appendix only) | "자연 변동 가능성. 다음 월 추세 재확인" |

### CVR ↓ (책임 단정 금지, "전환 구간 점검" 톤)
| 패턴 | rule_id | 운영 함의 |
|---|---|---|
| mix_dominant | `cvr_down_mix_dominant` | "유입 mix 변화가 변동의 {N}% 설명. 소재 배분 조정으로 회복 가능" |
| within_dominant | `cvr_down_within_dominant` | "광고 mix 설명 비중 낮음. 클릭 이후 단계(랜딩·5단계 폼·상담 응대) 로그 대조 우선 권장" |

---

## 4. 카드 우선순위·정렬 룰

```
1. 사용자 강조 트렌드 일치도 (CPM↑·CTR↑·CVR 산포) — 최소 6장 보장
2. 운영 가능성
   - mix_dominant + 명확한 driver 우선
   - mixed
   - within_dominant
   - partial-month (soft, 후순위)
   - 예외: CVR ↓ + within_dominant는 within 그룹 내 상위
3. 변화 크기 |Δ%|
4. 지점당 max 2장 (최종 trim 단계)

총 cap: 9장. 9 미만이어도 허용.
```

---

## 5. JSON 스키마 최종

```jsonc
{
  "funnel_variance": {
    "overall_trend": {
      "cpm": {"first_month": "2026-02", "first_value": 8900, "last_month": "2026-05",
              "last_value": 11920, "delta_pct": 33.9, "partial_flag_last": true},
      "ctr": {...}, "cvr": {...}
    },
    "cards": [
      {
        "branch": "서울",
        "metric": "cpm",
        "direction": "up",
        "month": "2026-04",
        "month_value": 11000,
        "baseline": {
          "type": "branch_mean",       // or "first_valid_month" / "peer_same_month"
          "value": 8900,
          "months": ["2026-02","2026-03"],
          "months_count": 2
        },
        "delta_pct": 23.6,
        "delta_abs": 2100,
        "vs_prev_month_pct": 18.2,    // 부가 표기
        "vs_first_month_pct": 23.6,   // 부가 표기
        "partial_month_flag": false,
        "sample_size": {"spend": 1230000, "impressions": 140000, "clicks": 1280, "conversions": 45},
        "thresholds_passed": {"relative": true, "absolute": true, "sample_size": true},
        "pattern": "mix_dominant",     // mix_dominant / within_dominant / mixed / weak
        "decomposition": {
          "mix_delta_abs": 1100,
          "within_delta_abs": 800,
          "interaction_delta_abs": 200,
          "mix_contribution_pct": 52.4,   // |mix| / (|mix|+|within|+|interaction|) × 100
          "within_contribution_pct": 38.1,
          "interaction_contribution_pct": 9.5,
          "interaction_hidden": true       // <10% → 본문 생략
        },
        "mix_drivers": [
          {"type": "의료진형", "current_share_pct": 55.0, "baseline_share_pct": 30.0,
           "share_delta_pp": 25.0, "type_metric_value": 13400, "basket_metric_value": 9200,
           "vs_basket_pct": 46.0}
        ],
        "within_drivers": [
          {"type": "다이어트(여성)", "metric_delta_abs": 1800, "metric_delta_pct": 14.0}
        ],
        "aux_signals": [
          {"key": "new_resumed_share", "value_pct": 31.0, "threshold_pct": 25.0,
           "numerator_impressions": 43000, "denominator_impressions": 138000},
          {"key": "off_impact", "prev_conversion_share_pct": 18.0,
           "prev_spend_share_pct": 22.0, "off_creative_count": 2, "threshold_pct": 15.0}
        ],
        "policy_rule_id": "cpm_up_mix_dominant",
        "policy_inputs": {
          "dominant_driver": "의료진형",
          "current_share_pct": 55.0,
          "target_share_pct": 30.0,
          "estimated_recovered_value": 9300
        },
        "operation_implication": "의료진형 비중을 30% 수준으로 낮추면 CPM이 약 9,300원까지 완화될 가능성이 있습니다. 동일 소재 단가 자체 상승은 입찰 경쟁·타겟 풀 포화·노출 지면 변화 등 광고 데이터 외부 요인 점검이 필요합니다.",
        "implication_strength": "strong"   // partial-month는 "soft"
      }
    ],
    "appendix_weak_cells": [...],         // weak 패턴 셀 (부록만)
    "computed_at": "2026-05-19T..."
  }
}
```

---

## 6. 한국어 톤 가이드

- "회복" → "완화" (CPM/CTR/CVR 모두 적용)
- "유지 권장" → "전환 품질이 유지된다면 ~ 유지 가능"
- "외부 요인" → "입찰 경쟁·타겟 풀 포화·노출 지면 변화 등 광고 데이터 외부 요인"
- "필요" → 강한 강도, "권장" → 부드러운 강도. partial-month는 "권장" 사용
- "기여율" 금지 → **"설명 비중" 또는 "효과 구성비"** 사용 (codex 추가 의견)
- CVR 책임 단정 금지 → "전환 구간 점검 권장"으로 환원

---

## 7. 구현 계획

1. **신규**: `.claude/skills/proposal-builder/scripts/analyze_funnel_variance.py`
   - 입력: `parsed.parquet`
   - 출력: 위 JSON 스키마
   - 함수: `decompose_kpi(df, branch, month, metric)`, `pick_cards(all_cells)`, `build_implication(card)`, `analyze(parsed_path)`
2. **수정**: `build_proposal.py`
   - `from analyze_funnel_variance import analyze as analyze_variance`
   - `data['funnel_variance'] = analyze_variance(parsed_path)`
3. **수정**: `html_template.py`
   - 2.3 evidence-card 아래에 새 sub-section (number 재조정 없이 2.3 내부 추가 div)
   - `.fv-card` 스타일 + 사용자 합의된 `aligned-N` CSS subgrid 활용
4. **수정**: `js_body.py`
   - `renderFunnelVariance()` 추가 — 트렌드 라인 + 카드 리스트 렌더
   - 카드 자식 구조: 헤더 / 분해 라인×3 / 보조 시그널 / 운영 함의 (총 5~6개 자식 → `aligned-6`)

---

## 검증 가능성

- `policy_rule_id`로 규칙 매핑 회귀 테스트 가능
- `decomposition` 값들이 산술적이므로 단위 테스트로 검증
- weak 셀이 부록에 기록되어 transparency 확보
- `thresholds_passed`로 셀 누락 사유 추적 가능

---

**비평 합의 완료. 사용자 OK 받으면 즉시 `analyze_funnel_variance.py` 작성 진입.**
