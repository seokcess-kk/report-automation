"""히트맵 월별 변동 원인 진단 (R5~R7 codex 합의 명세)

월 단위 KPI 변화를 산술 분해(mix · within · interaction) + 4단 게이트 통과한 셀만 카드화.
정책 매핑은 deterministic rule table 기반.

입력: parsed.parquet (build_proposal.py가 호출)
출력: DATA.funnel_variance JSON (overall_trend / cards / appendix_weak_cells / computed_at)

명세: output/proposal/202606/_codex_final_spec_heatmap_variance.md
"""
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES

# ================================ 임계값 상수 ================================
# 최소 샘플 사이즈 (Gate 1, R7 옵션 B)
MIN_SAMPLE = {'cpm': {'impressions': 20_000},
              'ctr': {'impressions': 20_000},
              'cvr': {'clicks': 100}}

# 변동 셀 인정 (Gate 2)
DELTA_THRESHOLD = {
    'cpm': {'rel': 10.0, 'abs': 1_000},      # 10% OR 1,000원
    'ctr': {'rel': 10.0, 'abs': 0.2},        # 10% OR 0.2%p
    'cvr': {'rel': 15.0, 'abs': 0.5},        # 15% OR 0.5%p
}

# 패턴 판정 (Gate 3)
PATTERN_MIX_DOM = 40.0
PATTERN_WITHIN_DOM = 40.0
PATTERN_MIXED_MIN = 30.0
PATTERN_WEAK_MAX = 20.0

# Partial-month flag (Gate 4)
PARTIAL_THRESHOLD = 0.70  # 70% 미만

# 보조 시그널 임계
AUX_THRESHOLD = {
    'new_resumed_share': 25.0,
    'off_impact': 15.0,
    'mix_max_share_delta': 10.0,
    'avg_daily_cost': 20.0,
    'active_ad_count': 30.0,
}

# 카드 정렬
CARD_TOTAL_CAP = 9
CARD_TREND_MIN = 6
CARD_PER_BRANCH_MAX = 2
INTERACTION_HIDE_THRESHOLD = 10.0  # contribution_pct <10% → 본문 숨김

# 사용자 강조 트렌드 (R7)
USER_TREND_FOCUS = [
    ('cpm', 'up'),
    ('ctr', 'up'),
    ('cvr', 'up'),    # 산포 = 양방향
    ('cvr', 'down'),
]


# ================================ 유틸 ================================

def _safe_div(num, den, scale=1.0):
    if den is None or den == 0 or pd.isna(den):
        return None
    return num / den * scale


def _kpi(group_df: pd.DataFrame) -> dict:
    """원시 sum → KPI 재계산 (행단위 _calc 평균 금지 규칙 준수)."""
    cost = float(group_df['cost'].sum())
    impr = float(group_df['impressions'].sum())
    clk = float(group_df['clicks'].sum())
    conv = float(group_df['conversions'].sum())
    return {
        'cost': cost,
        'impressions': impr,
        'clicks': clk,
        'conversions': conv,
        'cpm': _safe_div(cost, impr, 1000),
        'ctr': _safe_div(clk, impr, 100),
        'cvr': _safe_div(conv, clk, 100),
    }


def _format_won(v):
    if v is None:
        return '-'
    return f"{round(v):,}원"


def _format_pct(v, digits=2):
    if v is None:
        return '-'
    return f"{round(v, digits)}%"


def _format_delta(v, digits=1):
    if v is None:
        return '-'
    sign = '+' if v > 0 else ''
    return f"{sign}{round(v, digits)}%"


def _fmt_metric_value(metric: str, v) -> str:
    if v is None:
        return '-'
    if metric == 'cpm':
        return _format_won(v)
    return _format_pct(v)


# ============================ 데이터 준비 ============================

def _prepare(parsed_path: str) -> pd.DataFrame:
    df = pd.read_parquet(parsed_path)
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.strftime('%Y-%m')
    df = df[df['지점'].isin(VALID_BRANCHES)].copy()
    # 소재유형이 None인 행은 분해 제외 (parse_status FAIL 등)
    df['소재유형'] = df['소재유형'].fillna('미분류')
    return df


def _partial_flags(df: pd.DataFrame) -> dict:
    """월별 partial-month flag 판정. 정상월(2~4) 평균의 70% 미만이면 True.

    정상월: 부분월 자체 판정 전이라 첫 패스에서는 5월을 제외한 월을 정상으로 가정.
    """
    months = sorted(df['month'].unique())
    by_month = df.groupby('month').agg(
        active_days=('date', 'nunique'),
        cost=('cost', 'sum'),
    )
    # 정상월 후보 = 5월 제외한 월 (실제 마지막 월이 보통 부분)
    # 더 일반화: cost가 다른 월의 50% 이상이면 정상으로
    cost_median = by_month['cost'].median()
    days_median = by_month['active_days'].median()
    flags = {}
    for m in months:
        c = by_month.loc[m, 'cost']
        d = by_month.loc[m, 'active_days']
        is_partial = (c < cost_median * PARTIAL_THRESHOLD) or (d < days_median * PARTIAL_THRESHOLD)
        flags[m] = bool(is_partial)
    return flags


# ============================ 분해 계산 ============================

def _decompose(df_current: pd.DataFrame, df_baseline: pd.DataFrame, metric: str) -> dict:
    """creative_type 기준 mix · within · interaction 분해.

    metric weight:
      cpm/ctr: impressions
      cvr:     clicks
    """
    weight_col = 'clicks' if metric == 'cvr' else 'impressions'

    def _by_type(df):
        g = df.groupby('소재유형').agg(
            cost=('cost', 'sum'),
            impressions=('impressions', 'sum'),
            clicks=('clicks', 'sum'),
            conversions=('conversions', 'sum'),
        )
        if metric == 'cpm':
            g['kpi'] = g['cost'] / g['impressions'].replace(0, pd.NA) * 1000
        elif metric == 'ctr':
            g['kpi'] = g['clicks'] / g['impressions'].replace(0, pd.NA) * 100
        else:
            g['kpi'] = g['conversions'] / g['clicks'].replace(0, pd.NA) * 100
        g['weight'] = g[weight_col]
        total_w = g['weight'].sum()
        g['share'] = g['weight'] / total_w if total_w > 0 else 0.0
        return g

    g_cur = _by_type(df_current)
    g_base = _by_type(df_baseline)

    all_types = sorted(set(g_cur.index) | set(g_base.index))
    rows = []
    mix_total = within_total = inter_total = 0.0
    for t in all_types:
        share_cur = float(g_cur.loc[t, 'share']) if t in g_cur.index else 0.0
        share_base = float(g_base.loc[t, 'share']) if t in g_base.index else 0.0
        kpi_cur = g_cur.loc[t, 'kpi'] if t in g_cur.index else None
        kpi_base = g_base.loc[t, 'kpi'] if t in g_base.index else None
        kpi_cur = float(kpi_cur) if pd.notna(kpi_cur) else None
        kpi_base = float(kpi_base) if pd.notna(kpi_base) else None
        # 결손 처리: kpi가 한쪽만 있으면 within/interaction 계산 불가
        kc = kpi_cur if kpi_cur is not None else (kpi_base if kpi_base is not None else 0.0)
        kb = kpi_base if kpi_base is not None else (kpi_cur if kpi_cur is not None else 0.0)
        d_share = share_cur - share_base
        d_kpi = kc - kb
        # Shapley 분해 (forward·backward 대칭 평균):
        #   mix    = Δshare × (KPI_base + KPI_cur) / 2
        #   within = (share_base + share_cur) / 2 × ΔKPI
        # 정의상 mix + within = ΔKPI_total, interaction = 0
        mix_t = d_share * (kb + kc) / 2.0
        within_t = (share_base + share_cur) / 2.0 * d_kpi
        mix_total += mix_t
        within_total += within_t
        rows.append({
            'type': t,
            'share_cur': share_cur,
            'share_base': share_base,
            'share_delta_pp': (share_cur - share_base) * 100.0,
            'kpi_cur': kpi_cur,
            'kpi_base': kpi_base,
            'mix_t': mix_t,
            'within_t': within_t,
        })

    # 전체 변화 ΔKPI_total
    total_cur_kpi = _kpi(df_current)[metric]
    total_base_kpi = _kpi(df_baseline)[metric]
    total_delta = (total_cur_kpi or 0) - (total_base_kpi or 0)
    interaction_total = total_delta - mix_total - within_total

    sum_abs = abs(mix_total) + abs(within_total) + abs(interaction_total)
    contrib = {
        'mix': abs(mix_total) / sum_abs * 100 if sum_abs > 0 else 0.0,
        'within': abs(within_total) / sum_abs * 100 if sum_abs > 0 else 0.0,
        'interaction': abs(interaction_total) / sum_abs * 100 if sum_abs > 0 else 0.0,
    }
    return {
        'mix_delta_abs': mix_total,
        'within_delta_abs': within_total,
        'interaction_delta_abs': interaction_total,
        'total_delta': total_delta,
        'mix_contribution_pct': round(contrib['mix'], 1),
        'within_contribution_pct': round(contrib['within'], 1),
        'interaction_contribution_pct': round(contrib['interaction'], 1),
        'interaction_hidden': contrib['interaction'] < INTERACTION_HIDE_THRESHOLD,
        'per_type': rows,
    }


# ============================ 보조 시그널 ============================

def _aux_signals(df_branch_all: pd.DataFrame, df_current: pd.DataFrame, df_baseline: pd.DataFrame,
                 current_month: str, baseline_months: list) -> list:
    """4가지 보조 시그널 — 임계 통과한 것만 반환."""
    signals = []

    # 1. 신규/재개 ad_name 비중 (R6 합의: 3분류 — 신규/재개/기존)
    ads_current = set(df_current['ad_name'].dropna())
    ads_prev_month = set()
    for bm in baseline_months:
        sub = df_branch_all[df_branch_all['month'] == bm]
        ads_prev_month |= set(sub['ad_name'].dropna())
    ads_all_history = set(df_branch_all[df_branch_all['month'] < current_month]['ad_name'].dropna())

    new_ads = ads_current - ads_all_history  # 전체 기간 신규
    resumed_ads = (ads_current - new_ads) - ads_prev_month  # 재개 (직전월 미운영)
    new_resumed_ads = new_ads | resumed_ads

    impr_total = df_current['impressions'].sum()
    impr_new_resumed = df_current[df_current['ad_name'].isin(new_resumed_ads)]['impressions'].sum()
    nr_share = float(impr_new_resumed / impr_total * 100) if impr_total > 0 else 0.0
    if nr_share >= AUX_THRESHOLD['new_resumed_share']:
        signals.append({
            'key': 'new_resumed_share',
            'value_pct': round(nr_share, 1),
            'threshold_pct': AUX_THRESHOLD['new_resumed_share'],
            'numerator_impressions': int(impr_new_resumed),
            'denominator_impressions': int(impr_total),
            'new_ad_count': len(new_ads),
            'resumed_ad_count': len(resumed_ads),
        })

    # 2. OFF 영향 — 직전월 우수 광고가 현재월에 OFF된 비중
    df_prev = df_branch_all[df_branch_all['month'].isin(baseline_months)]
    if len(df_prev) > 0 and df_prev['conversions'].sum() > 0:
        prev_per_ad = df_prev.groupby('ad_name').agg(
            conv=('conversions', 'sum'),
            cost=('cost', 'sum'),
        )
        prev_per_ad = prev_per_ad[prev_per_ad['conv'] > 0]
        prev_per_ad['prev_cpa'] = prev_per_ad['cost'] / prev_per_ad['conv']
        # 우수 광고 = 직전월 평균 CPA 이하
        avg_cpa = float(df_prev['cost'].sum() / df_prev['conversions'].sum())
        good_ads = prev_per_ad[prev_per_ad['prev_cpa'] <= avg_cpa].index
        # 현재월에 OFF된 ad_name = current month에 없는 prev_good_ads
        off_ads = [a for a in good_ads if a not in ads_current]
        if off_ads:
            off_prev = df_prev[df_prev['ad_name'].isin(off_ads)]
            off_conv_share = float(off_prev['conversions'].sum() / df_prev['conversions'].sum() * 100)
            off_cost_share = float(off_prev['cost'].sum() / df_prev['cost'].sum() * 100)
            if off_conv_share >= AUX_THRESHOLD['off_impact']:
                signals.append({
                    'key': 'off_impact',
                    'prev_conversion_share_pct': round(off_conv_share, 1),
                    'prev_spend_share_pct': round(off_cost_share, 1),
                    'off_creative_count': len(off_ads),
                    'threshold_pct': AUX_THRESHOLD['off_impact'],
                })

    # 3. 일평균 cost 변화
    days_cur = df_current['date'].nunique()
    days_base = sum(df_branch_all[df_branch_all['month'] == m]['date'].nunique() for m in baseline_months)
    daily_cur = float(df_current['cost'].sum() / days_cur) if days_cur > 0 else 0.0
    daily_base = float(df_branch_all[df_branch_all['month'].isin(baseline_months)]['cost'].sum() / days_base) if days_base > 0 else 0.0
    if daily_base > 0:
        daily_delta = (daily_cur - daily_base) / daily_base * 100
        if abs(daily_delta) >= AUX_THRESHOLD['avg_daily_cost']:
            signals.append({
                'key': 'avg_daily_cost',
                'value_pct': round(daily_delta, 1),
                'threshold_pct': AUX_THRESHOLD['avg_daily_cost'],
                'current_daily_cost': round(daily_cur),
                'baseline_daily_cost': round(daily_base),
            })

    # 4. 활성 ad_name 수 변화
    active_cur = len(ads_current)
    active_base = len(ads_prev_month) if ads_prev_month else 0
    if active_base > 0:
        active_delta = (active_cur - active_base) / active_base * 100
        if abs(active_delta) >= AUX_THRESHOLD['active_ad_count']:
            signals.append({
                'key': 'active_ad_count',
                'value_pct': round(active_delta, 1),
                'threshold_pct': AUX_THRESHOLD['active_ad_count'],
                'current_count': active_cur,
                'baseline_count': active_base,
            })

    return signals


# ============================ 패턴 판정 ============================

def _pattern_of(decomposition: dict) -> str:
    m = decomposition['mix_contribution_pct']
    w = decomposition['within_contribution_pct']
    if m >= PATTERN_MIX_DOM:
        return 'mix_dominant'
    if w >= PATTERN_WITHIN_DOM:
        return 'within_dominant'
    if m >= PATTERN_MIXED_MIN and w >= PATTERN_MIXED_MIN:
        return 'mixed'
    if m < PATTERN_WEAK_MAX and w < PATTERN_WEAK_MAX:
        return 'weak'
    return 'mixed'  # 부분 강함 fallback


# ============================ 정책 매핑 ============================

def _build_policy(metric: str, direction: str, pattern: str, decomp: dict, drivers: dict,
                  aux: list, partial: bool) -> dict:
    """policy_rule_id + operation_implication 한국어 문장 생성."""
    mix_top = drivers.get('mix_top')
    within_top = drivers.get('within_top')
    has_new_resumed = any(s['key'] == 'new_resumed_share' for s in aux)
    mix_pct = round(decomp['mix_contribution_pct'])
    within_pct = round(decomp['within_contribution_pct'])

    # ---------- CPM ----------
    if metric == 'cpm' and direction == 'up':
        if pattern == 'mix_dominant' and mix_top:
            tname = mix_top['type']
            cur_share = round(mix_top['current_share_pct'])
            target_share = max(20, cur_share - int(round(mix_top['share_delta_pp'])))
            # 예상 완화 추정 = basket KPI(=baseline 평균)
            est_value = mix_top.get('basket_metric_value')
            est_str = f"약 {round(est_value):,}원까지" if est_value else "정상 수준으로"
            return {
                'rule_id': 'cpm_up_mix_dominant',
                'inputs': {'dominant_driver': tname, 'current_share_pct': cur_share,
                           'target_share_pct': target_share, 'estimated_value': est_value},
                'text': (f"{tname} 비중을 {target_share}% 수준으로 낮추면 CPM이 "
                         f"{est_str} 완화될 가능성이 있습니다. "
                         f"동일 소재 단가 자체 상승은 입찰 경쟁·타겟 풀 포화·노출 지면 변화 등 "
                         f"광고 데이터 외부 요인 점검이 필요합니다."),
            }
        if pattern == 'within_dominant':
            return {
                'rule_id': 'cpm_up_within_dominant',
                'inputs': {'within_top': within_top['type'] if within_top else None},
                'text': ("동일 소재 단가가 자체적으로 상승했습니다. 입찰 경쟁·타겟 풀 포화·노출 지면 변화 등 "
                         "광고 데이터 외부 요인 점검이 필요합니다."),
            }
        if pattern == 'mixed':
            return {
                'rule_id': 'cpm_up_mixed',
                'inputs': {},
                'text': ("소재 mix 변화와 동일 소재 단가 상승이 함께 작용했습니다. "
                         "소재 비중 환원과 외부 요인 점검을 병행해 주십시오."),
            }

    if metric == 'cpm' and direction == 'down':
        if pattern == 'mix_dominant':
            return {
                'rule_id': 'cpm_down_mix_dominant',
                'inputs': {'mix_top': mix_top['type'] if mix_top else None},
                'text': ("저단가 소재유형 비중 증가로 CPM이 개선되었습니다. "
                         "노출량·전환 품질 동반 점검을 권장합니다."),
            }
        if pattern == 'within_dominant':
            return {
                'rule_id': 'cpm_down_within_dominant',
                'inputs': {},
                'text': ("동일 소재 단가가 자체적으로 낮아진 구간입니다. "
                         "입찰 경쟁 완화 또는 타겟 확장 영향 가능성을 확인해 주십시오."),
            }
        if pattern == 'mixed':
            return {
                'rule_id': 'cpm_down_mixed',
                'inputs': {},
                'text': ("소재 mix 개선과 단가 하락이 함께 작용했습니다. 현 배분 유지 가능하나 "
                         "전환 품질 동반 점검이 필요합니다."),
            }

    # ---------- CTR ----------
    if metric == 'ctr' and direction == 'up':
        if has_new_resumed and pattern == 'mix_dominant':
            return {
                'rule_id': 'ctr_up_new_learning',
                'inputs': {'new_resumed_share_pct': next(s['value_pct'] for s in aux if s['key'] == 'new_resumed_share')},
                'text': ("신규·재개 광고 학습 기간의 자연 효과가 일부 포함되어 있습니다. "
                         "6월 4주차까지 추세 모니터링이 필요합니다."),
            }
        if pattern == 'mix_dominant' and mix_top:
            tname = mix_top['type']
            return {
                'rule_id': 'ctr_up_mix_dominant',
                'inputs': {'mix_top': tname, 'mix_contribution_pct': mix_pct},
                'text': (f"{tname} 비중 변화가 CTR 변동의 {mix_pct}%를 설명합니다. "
                         f"전환 품질이 유지된다면 6월에도 현 배분을 유지할 수 있습니다. "
                         f"신규 광고 학습 효과가 일부 포함되어 6월 4주차까지 추세 재확인을 권장합니다."),
            }
        if pattern == 'within_dominant':
            return {
                'rule_id': 'ctr_up_within_dominant',
                'inputs': {},
                'text': ("동일 소재의 반응률 자체 개선이 주원인입니다. 6월에도 동일 소재 유지 가능하나, "
                         "소재 피로도 점검을 함께 권장합니다."),
            }

    if metric == 'ctr' and direction == 'down':
        if pattern == 'mix_dominant' and mix_top:
            return {
                'rule_id': 'ctr_down_mix_dominant',
                'inputs': {'mix_top': mix_top['type']},
                'text': (f"저CTR 소재유형 비중 증가가 주원인입니다. "
                         f"고반응 유형 비중 회복 또는 저반응 유형 교체를 검토해 주십시오."),
            }
        if pattern == 'within_dominant':
            return {
                'rule_id': 'ctr_down_within_dominant',
                'inputs': {},
                'text': ("동일 소재의 반응률이 약화되었습니다. 소재 피로·후킹 약화·타겟 반복 노출을 점검해 주십시오."),
            }
        if has_new_resumed:
            return {
                'rule_id': 'ctr_down_new_learning',
                'inputs': {},
                'text': ("신규·재개 광고 학습 구간 영향 가능성이 있습니다. "
                         "6월 4주차까지 추세 확인 후 교체 판단을 권장합니다."),
            }

    # ---------- CVR ----------
    if metric == 'cvr' and direction == 'up':
        if pattern == 'mix_dominant':
            return {
                'rule_id': 'cvr_up_mix_dominant',
                'inputs': {'mix_top': mix_top['type'] if mix_top else None, 'mix_contribution_pct': mix_pct},
                'text': (f"전환 효율이 높은 유입 mix 증가가 변동의 {mix_pct}%를 설명합니다. "
                         f"해당 배분 유지 또는 확대를 검토해 주십시오."),
            }
        if pattern == 'within_dominant':
            return {
                'rule_id': 'cvr_up_within_dominant',
                'inputs': {},
                'text': ("동일 소재유형 내 전환 성과가 개선되었습니다. "
                         "랜딩·상담·예약 응대 개선 요인과의 대조를 권장합니다."),
            }

    if metric == 'cvr' and direction == 'down':
        if pattern == 'mix_dominant':
            return {
                'rule_id': 'cvr_down_mix_dominant',
                'inputs': {'mix_top': mix_top['type'] if mix_top else None, 'mix_contribution_pct': mix_pct},
                'text': (f"유입 mix 변화로 설명되는 비중은 {mix_pct}% 수준입니다. "
                         f"소재 배분 조정으로 회복 가능성이 있습니다."),
            }
        if pattern == 'within_dominant':
            return {
                'rule_id': 'cvr_down_within_dominant',
                'inputs': {'within_contribution_pct': within_pct},
                'text': (f"광고 mix 변화로 설명되는 비중은 {100 - within_pct}% 수준입니다. "
                         f"클릭 이후 단계(랜딩·5단계 폼·상담 응대) 로그 대조를 우선 권장합니다."),
            }

    # ---------- partial / mixed fallback ----------
    return {
        'rule_id': f'{metric}_{direction}_generic',
        'inputs': {},
        'text': ("변동 폭이 임계를 넘었으나 단일 우세 요인은 확인되지 않았습니다. "
                 "다음 월 추세를 함께 확인해 주십시오."),
    }


# ============================ 카드 빌더 ============================

def _build_card(branch: str, metric: str, current_month: str,
                df_branch_all: pd.DataFrame, baseline_months: list,
                partial_flags: dict) -> dict | None:
    """단일 (branch, metric, month) 셀에 대한 카드 후보 생성. None이면 게이트 탈락."""
    df_current = df_branch_all[df_branch_all['month'] == current_month]
    df_baseline = df_branch_all[df_branch_all['month'].isin(baseline_months)]

    if len(df_current) == 0 or len(df_baseline) == 0:
        return None

    cur_kpi = _kpi(df_current)
    base_kpi = _kpi(df_baseline)
    cur_val = cur_kpi[metric]
    base_val = base_kpi[metric]
    if cur_val is None or base_val is None:
        return None

    # Gate 1: 샘플 사이즈
    sample = {
        'spend': int(cur_kpi['cost']),
        'impressions': int(cur_kpi['impressions']),
        'clicks': int(cur_kpi['clicks']),
        'conversions': int(cur_kpi['conversions']),
    }
    sample_ok = True
    for key, thresh in MIN_SAMPLE[metric].items():
        if sample[key] < thresh:
            sample_ok = False
            break
    if not sample_ok:
        return None

    # Gate 2: 변동 인정
    delta_abs = cur_val - base_val
    delta_pct = (delta_abs / base_val * 100) if base_val != 0 else 0.0
    th = DELTA_THRESHOLD[metric]
    rel_ok = abs(delta_pct) >= th['rel']
    abs_ok = abs(delta_abs) >= th['abs']
    if not (rel_ok or abs_ok):
        return None

    direction = 'up' if delta_abs > 0 else 'down'

    # 분해
    decomp = _decompose(df_current, df_baseline, metric)
    pattern = _pattern_of(decomp)

    # 보조 시그널
    aux = _aux_signals(df_branch_all, df_current, df_baseline, current_month, baseline_months)

    # vs 전월
    months_sorted = sorted(df_branch_all['month'].unique())
    cur_idx = months_sorted.index(current_month)
    vs_prev = None
    if cur_idx > 0:
        prev_m = months_sorted[cur_idx - 1]
        prev_df = df_branch_all[df_branch_all['month'] == prev_m]
        prev_val = _kpi(prev_df)[metric]
        if prev_val:
            vs_prev = (cur_val - prev_val) / prev_val * 100

    # vs first month
    first_m = months_sorted[0]
    first_df = df_branch_all[df_branch_all['month'] == first_m]
    first_val = _kpi(first_df)[metric]
    vs_first = (cur_val - first_val) / first_val * 100 if first_val else None

    # 분해 드라이버 상위
    per_type = decomp['per_type']
    mix_sorted = sorted(per_type, key=lambda r: abs(r['mix_t']), reverse=True)
    within_sorted = sorted(per_type, key=lambda r: abs(r['within_t']), reverse=True)
    mix_top = mix_sorted[0] if mix_sorted else None
    within_top = within_sorted[0] if within_sorted else None

    # basket 평균 KPI (baseline 전체)
    basket_kpi = base_val

    mix_drivers = []
    for r in mix_sorted[:2]:
        if abs(r['mix_t']) < 0.001:
            break
        kpi_t = r['kpi_cur'] if r['kpi_cur'] is not None else r['kpi_base']
        vs_basket = ((kpi_t - basket_kpi) / basket_kpi * 100) if (kpi_t is not None and basket_kpi) else None
        mix_drivers.append({
            'type': r['type'],
            'current_share_pct': round(r['share_cur'] * 100, 1),
            'baseline_share_pct': round(r['share_base'] * 100, 1),
            'share_delta_pp': round(r['share_delta_pp'], 1),
            'type_metric_value': round(kpi_t, 2) if kpi_t else None,
            'basket_metric_value': round(basket_kpi, 2) if basket_kpi else None,
            'vs_basket_pct': round(vs_basket, 1) if vs_basket is not None else None,
        })

    within_drivers = []
    for r in within_sorted[:2]:
        if abs(r['within_t']) < 0.001 or r['kpi_cur'] is None or r['kpi_base'] is None:
            continue
        d_abs = r['kpi_cur'] - r['kpi_base']
        d_pct = (d_abs / r['kpi_base'] * 100) if r['kpi_base'] else None
        within_drivers.append({
            'type': r['type'],
            'metric_delta_abs': round(d_abs, 2),
            'metric_delta_pct': round(d_pct, 1) if d_pct is not None else None,
        })

    # 정책 매핑
    partial = partial_flags.get(current_month, False)
    policy = _build_policy(metric, direction, pattern, decomp,
                           {'mix_top': mix_drivers[0] if mix_drivers else None,
                            'within_top': within_drivers[0] if within_drivers else None},
                           aux, partial)

    implication_text = policy['text']
    if partial:
        implication_text = ("5월은 부분월입니다 — 집행일수·비용이 정상월의 70% 미만으로 정책 적용 강도를 낮춥니다. "
                            + implication_text)

    return {
        'branch': branch,
        'metric': metric,
        'direction': direction,
        'month': current_month,
        'month_value': round(cur_val, 2),
        'baseline': {
            'type': 'branch_mean',
            'value': round(base_val, 2),
            'months': baseline_months,
            'months_count': len(baseline_months),
        },
        'delta_pct': round(delta_pct, 1),
        'delta_abs': round(delta_abs, 2),
        'vs_prev_month_pct': round(vs_prev, 1) if vs_prev is not None else None,
        'vs_first_month_pct': round(vs_first, 1) if vs_first is not None else None,
        'partial_month_flag': partial,
        'sample_size': sample,
        'thresholds_passed': {'relative': rel_ok, 'absolute': abs_ok, 'sample_size': sample_ok},
        'pattern': pattern,
        'decomposition': {
            'mix_delta_abs': round(decomp['mix_delta_abs'], 2),
            'within_delta_abs': round(decomp['within_delta_abs'], 2),
            'interaction_delta_abs': round(decomp['interaction_delta_abs'], 2),
            'mix_contribution_pct': decomp['mix_contribution_pct'],
            'within_contribution_pct': decomp['within_contribution_pct'],
            'interaction_contribution_pct': decomp['interaction_contribution_pct'],
            'interaction_hidden': decomp['interaction_hidden'],
        },
        'mix_drivers': mix_drivers,
        'within_drivers': within_drivers,
        'aux_signals': aux,
        'policy_rule_id': policy['rule_id'],
        'policy_inputs': policy['inputs'],
        'operation_implication': implication_text,
        'implication_strength': 'soft' if partial else 'strong',
    }


# ============================ 카드 정렬·trim ============================

def _sort_and_trim(cards: list) -> list:
    """R7 정렬 룰: 트렌드 일치도 → 운영 가능성 → 변화 크기 → 지점당 max 2장 → cap 9장."""
    def trend_match(c):
        return (c['metric'], c['direction']) in [(m, d) for m, d in USER_TREND_FOCUS]

    def pattern_rank(c):
        # 낮을수록 우선
        if c['partial_month_flag']:
            base = 4
        elif c['pattern'] == 'mix_dominant':
            base = 0
        elif c['pattern'] == 'mixed':
            base = 1
        elif c['pattern'] == 'within_dominant':
            base = 2
        else:
            base = 3
        # CVR ↓ + within_dominant 예외 우선 상승 (R6)
        if c['metric'] == 'cvr' and c['direction'] == 'down' and c['pattern'] == 'within_dominant':
            base = 0
        return base

    # 1차 정렬: (트렌드일치 desc, pattern_rank asc, |delta_pct| desc)
    cards.sort(key=lambda c: (-int(trend_match(c)), pattern_rank(c), -abs(c['delta_pct'])))

    # 트렌드 일치 최소 보장 + cap
    trend_cards = [c for c in cards if trend_match(c)]
    other_cards = [c for c in cards if not trend_match(c)]
    selected = trend_cards[:CARD_TREND_MIN]
    remaining_slots = CARD_TOTAL_CAP - len(selected)
    pool = trend_cards[CARD_TREND_MIN:] + other_cards
    pool.sort(key=lambda c: (pattern_rank(c), -abs(c['delta_pct'])))
    selected += pool[:remaining_slots]

    # 지점당 max 2장 trim
    branch_count = {}
    final = []
    for c in selected:
        b = c['branch']
        if branch_count.get(b, 0) >= CARD_PER_BRANCH_MAX:
            continue
        final.append(c)
        branch_count[b] = branch_count.get(b, 0) + 1
    # cap 다시
    return final[:CARD_TOTAL_CAP]


# ============================ 메인 ============================

def analyze(parsed_path: str) -> dict:
    df = _prepare(parsed_path)
    partial_flags = _partial_flags(df)
    months = sorted(df['month'].unique())

    # overall_trend (전 지점 합계 기준)
    overall_trend = {}
    overall_by_month = {m: _kpi(df[df['month'] == m]) for m in months}
    for metric in ['cpm', 'ctr', 'cvr']:
        vals = [(m, overall_by_month[m][metric]) for m in months if overall_by_month[m][metric] is not None]
        if len(vals) < 2:
            continue
        first_m, first_v = vals[0]
        last_m, last_v = vals[-1]
        overall_trend[metric] = {
            'first_month': first_m,
            'first_value': round(first_v, 2),
            'last_month': last_m,
            'last_value': round(last_v, 2),
            'delta_pct': round((last_v - first_v) / first_v * 100, 1) if first_v else None,
            'delta_abs': round(last_v - first_v, 2),
            'partial_flag_last': partial_flags.get(last_m, False),
            'by_month': {m: round(overall_by_month[m][metric], 2) if overall_by_month[m][metric] else None
                         for m in months},
        }

    # 셀별 카드 후보 생성
    all_cards = []
    weak_cells = []
    for branch in VALID_BRANCHES:
        df_b = df[df['지점'] == branch]
        if len(df_b) == 0:
            continue
        b_months = sorted(df_b['month'].unique())
        for current_month in b_months:
            # baseline = 현재월 이전의 정상월 (시간 순서 강제 — 사용자의 "지날수록 변화" 트렌드)
            normal_months = [m for m in b_months if m < current_month and not partial_flags.get(m, False)]
            if len(normal_months) == 0:
                # fallback: 그 지점의 이전 월 (partial 포함). 첫 월은 baseline 없음 → 카드 제외
                normal_months = [m for m in b_months if m < current_month]
            if len(normal_months) == 0:
                continue  # 첫 월은 baseline 없음
            for metric in ['cpm', 'ctr', 'cvr']:
                card = _build_card(branch, metric, current_month, df_b, normal_months, partial_flags)
                if card is None:
                    continue
                if card['pattern'] == 'weak':
                    weak_cells.append({
                        'branch': card['branch'], 'metric': metric, 'month': current_month,
                        'delta_pct': card['delta_pct'], 'reason': 'weak — mix·within 모두 설명력 <20%',
                    })
                    continue
                all_cards.append(card)

    final_cards = _sort_and_trim(all_cards)

    return {
        'overall_trend': overall_trend,
        'cards': final_cards,
        'appendix_weak_cells': weak_cells,
        'partial_flags_by_month': partial_flags,
        'computed_at': datetime.now().isoformat(timespec='seconds'),
    }


if __name__ == '__main__':
    import json
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260506/parsed.parquet'
    result = analyze(path)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
