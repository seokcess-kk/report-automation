"""규칙 기반 액션 제안 생성 (v3).

입력 (data_dir 아래):
    branch_pace.json                 — 지점 페이스
    creative_tier.parquet            — ON 소재 TIER
    creative_off.parquet             — OFF 소재 (재활성화 판정용)
    age_analysis.parquet             — 나이대 효율
    weekday_analysis.parquet         — 요일 효율 (선택)
    creative_type_analysis.parquet   — 소재 유형 효율 (선택)
    hour_analysis.parquet            — 시간대 효율 (선택)

출력:
    action_proposals.json

사용법:
    python .claude/skills/action-advisor/scripts/generate_proposals.py output/data/20260421
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ─────────────────────── 규칙 임계값 (수정은 여기서만) ──────────────────────
# 규칙 1, 2 — 예산 페이스
BUDGET_OVER_GAP_PCT = 15
BUDGET_UNDER_GAP_PCT = -15
CPA_OVER_MULTIPLIER = 1.2
BUDGET_DECREASE_RATIO = 0.8
BUDGET_INCREASE_RATIO = 1.2

# 규칙 3, 4 — 소재 TIER
TIER4_MIN_DAYS = 7
TIER1_COST_CONV_GAP_PCT = 5         # 비용비중 + 5%p < 전환비중 (활용도 낮은 TIER1)

# 규칙 5, 6 — 나이대
AGE_LOW_EFF = 0.8                    # v2: 완화
AGE_LOW_MIN_COST_SHARE = 15          # v2: 비중 있는 나이대만
AGE_HIGH_EFF = 1.0                   # v2: 완화
AGE_HIGH_MAX_COST_SHARE = 25

# 규칙 7 — 전환 페이스 극단 부진
CONV_LAG_CRITICAL_PCT = -25
CPA_CRITICAL_MULTIPLIER = 1.5

# 규칙 8 — 예산 재분배
REALLOC_RATIO = 0.10                 # 이관량 = ok 지점 예산의 10%

# 규칙 9 — OFF TIER1 재활성화
OFF_REACTIVATE_MIN_CONV = 10
OFF_REACTIVATE_MAX_ITEMS = 5         # 상위 N개만
# CPA는 전역 target_cpa 기준 (branch_pace.json에서 로드)

# 규칙 10, 11, 12 — 세그먼트
HOUR_CPA_BAD_MULTIPLIER = 1.5
HOUR_MIN_COST_SHARE = 5              # 비용비중 기준 (24시간 분포이므로 5% 이상)
WEEKDAY_EFF_VARIANCE = 0.25          # v3: 완화
WEEKDAY_TOP_EFF = 1.1                # v3: 완화
TYPE_TOP_EFF = 1.1                   # v3: 완화
TYPE_MAX_COST_SHARE = 30
# ────────────────────────────────────────────────────────────────────────────


def _new_id(i: int) -> str:
    return f"p{i:03d}"


def _load(data_dir: str, name: str):
    path = os.path.join(data_dir, name)
    if not os.path.exists(path):
        return None
    if name.endswith('.json'):
        return json.load(open(path, encoding='utf-8'))
    if name.endswith('.parquet'):
        return pd.read_parquet(path)
    return None


# ─────────────── 규칙 함수 ───────────────

def rule_budget_pace(pace: dict) -> list:
    """규칙 1, 2: 예산 오버/언더페이스"""
    out = []
    dp = pace['date_progress']
    for b in pace['branches']:
        cpa = b.get('cpa')
        target = b.get('target_cpa') or 0
        gap = b['budget_pct'] - dp
        cpa_over = cpa is not None and target and cpa > target * CPA_OVER_MULTIPLIER
        cpa_under = cpa is not None and target and cpa <= target

        if gap > BUDGET_OVER_GAP_PCT and cpa_over:
            out.append(_make(
                'high', 'branch', b['branch'], 'budget_decrease',
                f"{b['branch']} 예산 -20% 제안",
                f"소진률 {b['budget_pct']}% vs 일자진행 {dp}% (+{round(gap)}%p), "
                f"CPA {cpa:,}원 (목표 대비 {b['cpa_vs_target_pct']}%)",
                {'current': b['budget'], 'proposed': round(b['budget'] * BUDGET_DECREASE_RATIO), 'unit': 'KRW/월'},
                {'budget_pct': b['budget_pct'], 'date_progress': dp, 'cpa': cpa, 'target_cpa': target},
            ))
        elif gap < BUDGET_UNDER_GAP_PCT and cpa_under and b['conv_target']:
            out.append(_make(
                'medium', 'branch', b['branch'], 'budget_increase',
                f"{b['branch']} 예산 +20% 제안",
                f"소진률 {b['budget_pct']}% vs 일자진행 {dp}% ({round(gap)}%p), "
                f"CPA {cpa:,}원은 목표 내 — 여력 있음",
                {'current': b['budget'], 'proposed': round(b['budget'] * BUDGET_INCREASE_RATIO), 'unit': 'KRW/월'},
                {'budget_pct': b['budget_pct'], 'date_progress': dp, 'cpa': cpa, 'target_cpa': target},
            ))
    return out


def rule_tier4_long(creative_df) -> list:
    """규칙 3: TIER4 장기 지속"""
    out = []
    if creative_df is None or '집행일수' not in creative_df.columns:
        return out
    mask = (creative_df['TIER'] == 'TIER4') & (creative_df['집행일수'] >= TIER4_MIN_DAYS)
    for _, r in creative_df[mask].iterrows():
        name = str(r.get('소재구분') or r.get('매칭키', '?'))
        cpa = r.get('CPA')
        out.append(_make(
            'high', 'creative', name, 'pause_creative',
            f"[{name}] 중단 검토 (TIER4 {int(r['집행일수'])}일 지속)",
            f"CPA {int(cpa):,}원, 전환 {int(r.get('총전환', 0))}건, "
            f"비용 {int(r.get('총비용', 0)):,}원",
            {'action': 'disable', 'ad_name': name},
            {'TIER': 'TIER4', '집행일수': int(r['집행일수']),
             'CPA': int(cpa) if pd.notna(cpa) else None},
        ))
    return out


def rule_tier1_underused(creative_df) -> list:
    """규칙 4 (v2): TIER1인데 비중이 전환비중보다 낮은 소재 → 확대"""
    out = []
    if creative_df is None or 'TIER' not in creative_df.columns:
        return out
    df = creative_df[creative_df['TIER'] == 'TIER1'].copy()
    if '총비용' not in df.columns or '총전환' not in df.columns:
        return out
    total_cost = df['총비용'].sum()
    total_conv = df['총전환'].sum()
    if total_cost == 0 or total_conv == 0:
        return out
    df['비용비중'] = df['총비용'] / total_cost * 100
    df['전환비중'] = df['총전환'] / total_conv * 100
    mask = df['전환비중'] - df['비용비중'] > TIER1_COST_CONV_GAP_PCT
    for _, r in df[mask].iterrows():
        name = str(r.get('소재구분') or r.get('매칭키', '?'))
        out.append(_make(
            'high', 'creative', name, 'scale_creative',
            f"[{name}] 예산 확대 검토 (TIER1 활용 부족)",
            f"비용비중 {r['비용비중']:.1f}% < 전환비중 {r['전환비중']:.1f}% "
            f"(CPA {int(r['CPA']):,}원, CVR {r['CVR']:.1f}%)",
            {'action': 'increase_exposure', 'ad_name': name},
            {'TIER': 'TIER1', 'cost_share': round(r['비용비중'], 1),
             'conv_share': round(r['전환비중'], 1)},
        ))
    return out


def rule_age(age_df) -> list:
    """규칙 5, 6 (v2 완화): 나이대 저/고효율"""
    out = []
    if age_df is None or '예산효율점수' not in age_df.columns:
        return out
    for _, r in age_df.iterrows():
        age = r.get('age_group')
        if age in ('Unknown', None) or pd.isna(age):
            continue
        score = r.get('예산효율점수')
        cs = r.get('비용비중', 0)
        if pd.isna(score):
            continue

        if score < AGE_LOW_EFF and cs >= AGE_LOW_MIN_COST_SHARE:
            out.append(_make(
                'medium', 'age', str(age), 'exclude_age',
                f"{age} 나이대 타겟 축소 검토",
                f"예산효율 {score:.2f} (비용 {cs:.1f}% vs 전환 {r.get('전환비중', 0):.1f}%) — "
                f"비중 있음에도 비효율, 축소 또는 맞춤 소재 필요",
                {'action': 'reduce_age_weight', 'age': str(age)},
                {'예산효율점수': round(float(score), 2), '비용비중': float(cs)},
            ))
        elif score > AGE_HIGH_EFF and cs < AGE_HIGH_MAX_COST_SHARE:
            out.append(_make(
                'medium', 'age', str(age), 'expand_age',
                f"{age} 나이대 비중 확대 검토",
                f"예산효율 {score:.2f} (비용 {cs:.1f}% vs 전환 {r.get('전환비중', 0):.1f}%) — "
                f"고효율이나 비중 낮음",
                {'action': 'increase_age_weight', 'age': str(age)},
                {'예산효율점수': round(float(score), 2), '비용비중': float(cs)},
            ))
    return out


def rule_conv_critical(pace: dict) -> list:
    """규칙 7: 전환 극단 부진 + CPA 고공 → 소재 전면 재검토"""
    out = []
    dp = pace['date_progress']
    for b in pace['branches']:
        conv_gap = b['conv_pct'] - dp
        cpa = b.get('cpa')
        target = b.get('target_cpa') or 0
        if conv_gap < CONV_LAG_CRITICAL_PCT and cpa is not None and target and cpa > target * CPA_CRITICAL_MULTIPLIER:
            out.append(_make(
                'high', 'branch', b['branch'], 'creative_review',
                f"{b['branch']} 소재 전면 재검토 권고",
                f"전환 {b['conv_pct']}% vs 일자진행 {dp}% ({round(conv_gap)}%p), "
                f"CPA {cpa:,}원 (목표 {target:,}원 대비 {b['cpa_vs_target_pct']}%) — "
                f"예산/소재 조정만으로 회복 어려움",
                {'action': 'review_all_creatives', 'branch': b['branch']},
                {'conv_pct': b['conv_pct'], 'date_progress': dp,
                 'cpa': cpa, 'target_cpa': target},
            ))
    return out


def rule_budget_realloc(pace: dict) -> list:
    """규칙 8: 예산 재분배 (ok → danger 이관)"""
    out = []
    oks = [b for b in pace['branches'] if b['status'] == 'ok' and b['budget'] > 0]
    dangers = [b for b in pace['branches'] if b['status'] == 'danger' and b['cpa'] and b['target_cpa']
               and b['cpa'] <= b['target_cpa'] * CPA_CRITICAL_MULTIPLIER]  # CPA가 회복 불가 수준은 제외
    if not oks or not dangers:
        return out

    # 가장 여유 있는 ok (소진률 - 일자진행 최소) → 가장 부족한 danger (전환 격차 최대)
    oks.sort(key=lambda b: b['budget_pct'] - pace['date_progress'])
    dangers.sort(key=lambda b: b['conv_pct'] - pace['date_progress'])

    src, dst = oks[0], dangers[0]
    amount = round(src['budget'] * REALLOC_RATIO)
    out.append(_make(
        'medium', 'branch', f"{src['branch']}→{dst['branch']}", 'budget_reallocate',
        f"예산 재분배: {src['branch']} → {dst['branch']} ({amount:,}원)",
        f"{src['branch']} 여유(전환 {src['conv_pct']}%, 예산 {src['budget_pct']}%) → "
        f"{dst['branch']} 부족(전환 {dst['conv_pct']}%, 일자진행 {pace['date_progress']}%)",
        {'from': src['branch'], 'to': dst['branch'],
         'amount': amount, 'unit': 'KRW/월'},
        {'src_status': src['status'], 'dst_status': dst['status'],
         'dst_conv_gap': dst['conv_pct'] - pace['date_progress']},
    ))
    return out


def rule_off_reactivate(off_df, target_cpa_global: int) -> list:
    """규칙 9: 과거 성과 우수한 OFF 소재 재활성화 (전역 TARGET_CPA 기준, 상위 5개)"""
    out = []
    if off_df is None or len(off_df) == 0 or not target_cpa_global:
        return out
    if not all(c in off_df.columns for c in ['CPA', '총전환']):
        return out

    mask = (off_df['총전환'] >= OFF_REACTIVATE_MIN_CONV) & (off_df['CPA'] <= target_cpa_global)
    picks = off_df[mask].sort_values('CPA').head(OFF_REACTIVATE_MAX_ITEMS)

    for _, r in picks.iterrows():
        name = str(r.get('매칭키') or r.get('소재구분', '?'))
        cpa = r.get('CPA')
        conv = r.get('총전환', 0)
        out.append(_make(
            'medium', 'creative', name, 'reactivate_creative',
            f"[{name}] 재활성화 검토",
            f"OFF 상태 · 생존 시 CPA {int(cpa):,}원, 전환 {int(conv)}건 "
            f"(목표 {target_cpa_global:,}원 이내)",
            {'action': 'enable', 'ad_name': name},
            {'off_cpa': int(cpa), 'off_conv': int(conv),
             'target_cpa': target_cpa_global},
        ))
    return out


def rule_hour_bad(hour_df) -> list:
    """규칙 10: 시간대 비효율 — 비용비중 ≥ 5% AND CPA > 평균×1.5"""
    out = []
    if hour_df is None or 'CPA' not in hour_df.columns:
        return out
    total_cost = hour_df['총비용'].sum()
    total_conv = hour_df['총전환'].sum()
    if total_cost == 0 or total_conv == 0:
        return out
    avg_cpa = total_cost / total_conv

    for _, r in hour_df.iterrows():
        cpa = r.get('CPA')
        cost_share = r.get('비용비중', 0)
        if pd.isna(cpa) or cost_share < HOUR_MIN_COST_SHARE:
            continue
        if cpa > avg_cpa * HOUR_CPA_BAD_MULTIPLIER:
            out.append(_make(
                'medium', 'hour', f"{int(r['hour'])}시", 'dayparting',
                f"{int(r['hour']):02d}시 시간대 송출 축소 검토",
                f"CPA {int(cpa):,}원 (평균 {int(avg_cpa):,}원의 "
                f"{cpa/avg_cpa:.1f}배), 비용비중 {cost_share:.1f}%",
                {'action': 'reduce_hour_dayparting', 'hour': int(r['hour'])},
                {'hour_cpa': int(cpa), 'avg_cpa': int(avg_cpa),
                 'cost_share': round(float(cost_share), 1)},
            ))
    return out


def rule_weekday_boost(wk_df) -> list:
    """규칙 11: 요일 효율 편차 → 고효율 요일 가중"""
    out = []
    if wk_df is None or '예산효율점수' not in wk_df.columns or len(wk_df) < 5:
        return out
    scores = wk_df['예산효율점수'].dropna()
    if len(scores) < 5:
        return out
    variance = float(scores.max() - scores.min())
    if variance < WEEKDAY_EFF_VARIANCE:
        return out
    top = wk_df.loc[wk_df['예산효율점수'].idxmax()]
    if top['예산효율점수'] < WEEKDAY_TOP_EFF:
        return out
    out.append(_make(
        'medium', 'weekday', str(top['weekday']), 'weekday_boost',
        f"{top['weekday']}요일 예산 가중 검토",
        f"{top['weekday']}요일 효율점수 {top['예산효율점수']:.2f} (편차 {variance:.2f}) — "
        f"CPA {int(top['CPA']) if pd.notna(top['CPA']) else '-':,}원, "
        f"전환비중 {top['전환비중']:.1f}%",
        {'action': 'weight_weekday_higher', 'weekday': str(top['weekday'])},
        {'weekday': str(top['weekday']), 'eff_score': round(float(top['예산효율점수']), 2),
         'variance': round(variance, 2)},
    ))
    return out


def rule_type_expand(ct_df) -> list:
    """규칙 12: 소재 유형 편중 기회"""
    out = []
    if ct_df is None or '예산효율점수' not in ct_df.columns or len(ct_df) == 0:
        return out
    top = ct_df.iloc[0]  # 정렬되어 있음
    if pd.isna(top['예산효율점수']) or top['예산효율점수'] < TYPE_TOP_EFF:
        return out
    if top['비용비중'] >= TYPE_MAX_COST_SHARE:
        return out
    out.append(_make(
        'medium', 'creative_type', str(top['소재유형']), 'type_scale',
        f"[{top['소재유형']}] 유형 신규 제작/확대",
        f"효율점수 {top['예산효율점수']:.2f}, 비용비중 {top['비용비중']:.1f}% — "
        f"CPA {int(top['CPA']) if pd.notna(top['CPA']) else '-':,}원",
        {'action': 'produce_new_creatives', 'type': str(top['소재유형'])},
        {'eff_score': round(float(top['예산효율점수']), 2),
         'cost_share': float(top['비용비중'])},
    ))
    return out


# ─────────────── 유틸 ───────────────

def _make(priority, scope, target, action_type, title, reason, recommended_value, evidence):
    return {
        'id': None,
        'priority': priority,
        'scope': scope,
        'target': target,
        'action_type': action_type,
        'title': title,
        'reason': reason,
        'recommended_value': recommended_value,
        'evidence': evidence,
    }


# ─────────────── 메인 ───────────────

def generate(data_dir: str) -> dict:
    pace = _load(data_dir, 'branch_pace.json')
    tier_df = _load(data_dir, 'creative_tier.parquet')
    off_df = _load(data_dir, 'creative_off.parquet')
    age_df = _load(data_dir, 'age_analysis.parquet')
    wk_df = _load(data_dir, 'weekday_analysis.parquet')
    ct_df = _load(data_dir, 'creative_type_analysis.parquet')
    hour_df = _load(data_dir, 'hour_analysis.parquet')

    proposals = []
    if pace:
        proposals += rule_budget_pace(pace)
        proposals += rule_conv_critical(pace)
        proposals += rule_budget_realloc(pace)
    proposals += rule_tier4_long(tier_df)
    proposals += rule_tier1_underused(tier_df)
    proposals += rule_age(age_df)
    target_cpa_global = (pace or {}).get('overall', {}).get('target_cpa', 0)
    proposals += rule_off_reactivate(off_df, target_cpa_global)
    proposals += rule_hour_bad(hour_df)
    proposals += rule_weekday_boost(wk_df)
    proposals += rule_type_expand(ct_df)

    order = {'high': 0, 'medium': 1, 'low': 2}
    proposals.sort(key=lambda p: order.get(p.get('priority', 'low'), 99))
    for i, p in enumerate(proposals, 1):
        p['id'] = _new_id(i)

    return {
        'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'rule_version': 'v3',
        'proposals': proposals,
        'summary': {
            'total': len(proposals),
            'high': sum(1 for p in proposals if p['priority'] == 'high'),
            'medium': sum(1 for p in proposals if p['priority'] == 'medium'),
            'low': sum(1 for p in proposals if p['priority'] == 'low'),
        },
    }


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else None
    if not data_dir:
        base = Path('output/data')
        if not base.exists():
            print(f"[ERROR] {base} 없음")
            sys.exit(1)
        data_dir = str(max(base.iterdir()))
        print(f"[INFO] 최신 data_dir: {data_dir}")

    result = generate(data_dir)
    out_path = os.path.join(data_dir, 'action_proposals.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    s = result['summary']
    print(f"[OK] {out_path} - total {s['total']} (high {s['high']} / medium {s['medium']} / low {s['low']})")


if __name__ == '__main__':
    main()
