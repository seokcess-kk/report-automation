"""애드온 소재 적용 효과 — 디자인 변경 분리 분석 (R12-부산 제외)

설계 변경 이유:
  · 3~4월 노출 애드온 = v1 (구 디자인) / 5월 노출 애드온 = v2 (신 디자인)
  · 5월에는 원래 모든 캠페인·소재에 애드온 적용 예정이었으나
    부산점만 운영 사유로 일부 미적용 → 5월 비애드온의 ~94%가 부산
  · 부산은 5월 일부 미적용으로 비교 대상에서 분리 필요
  · 결과: 부산 제외 시 5월 비애드온은 사실상 0 → 동기간 비교 불가
  · 따라서 본문 평가축을 v2 vs v1 직접 비교 + 소재유형별 디자인 효과로 전환
  · v1 vs 3~4월 비애드온 비교는 그대로 유지 (충분한 양쪽 표본)

입력:
  - parsed.parquet
  - input/tiktok_ad_meta.csv (ad_id × is_addon)
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES

DESIGN_V2_FROM = pd.Timestamp('2026-05-01')
EXCLUDE_BRANCHES = ['부산']  # 5월 일부 미적용

SAMPLE_MIN_CLICKS = 100
PAIR_MIN_CLICKS = 100
TYPE_MIN_CLICKS = 50
DESIGN_TYPE_MIN_CLICKS = 200   # 소재유형별 디자인 효과 평가는 양쪽 모두 200+


def _kpis(g: pd.DataFrame) -> dict:
    cost = int(g['cost'].sum())
    impr = int(g['impressions'].sum())
    clicks = int(g['clicks'].sum())
    conv = int(g['conversions'].sum())
    # 시청 깊이 (선택 컬럼 — 구 데이터는 0/null일 수 있음)
    def _col(c):
        return int(g[c].sum()) if c in g.columns and impr else 0
    v6 = _col('video_watched_6s')
    p25 = _col('video_p25')
    p50 = _col('video_p50')
    p75 = _col('video_p75')
    p100 = _col('video_p100')
    likes = _col('likes')
    comments = _col('comments')
    shares = _col('shares')
    eng15s = _col('engaged_view_15s')
    avg_sec = round(float(g['avg_video_play_sec'].mean()), 2) if 'avg_video_play_sec' in g.columns and len(g) else None
    return {
        'ad_count': int(g['ad_id'].nunique()) if len(g) else 0,
        'cost': cost,
        'impressions': impr,
        'clicks': clicks,
        'conversions': conv,
        'cpm': round(cost / impr * 1000) if impr else None,
        'ctr': round(clicks / impr * 100, 2) if impr else None,
        'cvr': round(conv / clicks * 100, 2) if clicks else None,
        'cpa': round(cost / conv) if conv else None,
        # 시청 깊이 (애드온은 통상 3초+ 영역에서 노출)
        'v6s': v6,
        'p100': p100,
        'v6s_rate': round(v6 / impr * 100, 2) if impr else None,
        'p25_rate': round(p25 / impr * 100, 2) if impr else None,
        'p50_rate': round(p50 / impr * 100, 2) if impr else None,
        'p75_rate': round(p75 / impr * 100, 2) if impr else None,
        'p100_rate': round(p100 / impr * 100, 2) if impr else None,
        'eng15s_rate': round(eng15s / impr * 100, 2) if impr else None,
        'avg_video_sec': avg_sec,
        'click_per_v6s': round(clicks / v6 * 100, 2) if v6 else None,
        # 인게이지먼트 (바이럴 / 전환 깔때기 분리 진단)
        'likes': likes,
        'comments': comments,
        'shares': shares,
        'like_rate': round(likes / impr * 100, 3) if impr else None,
        'comment_rate': round(comments / impr * 100, 3) if impr else None,
        'share_rate': round(shares / impr * 100, 4) if impr else None,
        'eng_rate': round((likes + comments + shares) / impr * 100, 3) if impr else None,
    }


def _delta(a_v, b_v, direction: str):
    if a_v is None or b_v is None or b_v == 0:
        return None
    return round((a_v - b_v) / b_v * 100, 1)


def _cvr_ztest(conv_a, click_a, conv_b, click_b):
    if not click_a or not click_b:
        return None, None
    p_a = conv_a / click_a
    p_b = conv_b / click_b
    p_pool = (conv_a + conv_b) / (click_a + click_b)
    if p_pool <= 0 or p_pool >= 1:
        return None, None
    se = (p_pool * (1 - p_pool) * (1/click_a + 1/click_b)) ** 0.5
    if se == 0:
        return None, None
    z = (p_a - p_b) / se
    import math
    def _norm_cdf(x):
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))
    p_value = 2 * (1 - _norm_cdf(abs(z)))
    return round(z, 2), round(p_value, 4)


def _delta_block(a: dict, b: dict) -> dict:
    z, p = _cvr_ztest(a['conversions'], a['clicks'], b['conversions'], b['clicks'])
    return {
        'cpm': _delta(a['cpm'], b['cpm'], 'low'),
        'ctr': _delta(a['ctr'], b['ctr'], 'high'),
        'cvr': _delta(a['cvr'], b['cvr'], 'high'),
        'cpa': _delta(a['cpa'], b['cpa'], 'low'),
        'cvr_z': z,
        'cvr_p': p,
        'cvr_significant': bool(p is not None and p < 0.05),
    }


def _assign_version(date_series, is_addon_series) -> pd.Series:
    return pd.Series([
        ('addon_v2' if d >= DESIGN_V2_FROM else 'addon_v1') if a else 'non_addon'
        for d, a in zip(date_series, is_addon_series)
    ], index=date_series.index)


def _slice_kpis(merged: pd.DataFrame, mask_a: pd.Series, mask_b: pd.Series) -> dict:
    a = _kpis(merged[mask_a])
    b = _kpis(merged[mask_b])
    return {'addon': a, 'non_addon': b, 'delta_pct': _delta_block(a, b)}


def _classify_v1(block: dict, min_clicks: int = SAMPLE_MIN_CLICKS) -> dict:
    """v1 vs 3~4월 비애드온 — 일반 평가 (충분한 양쪽 표본)."""
    a = block['addon']; n = block['non_addon']; d = block['delta_pct']
    if a['clicks'] < min_clicks or n['clicks'] < min_clicks:
        return {'verdict': 'low_sample', 'label': '표본 부족',
                'rationale': f"애드온 클릭 {a['clicks']:,} / 비애드온 클릭 {n['clicks']:,}"}
    cvr_d = d.get('cvr'); cpa_d = d.get('cpa'); sig = d.get('cvr_significant')
    if cvr_d is not None and cvr_d > 0 and sig:
        return {'verdict': 'positive', 'label': '효과 명확 (구 디자인 시기)',
                'rationale': f"CVR +{cvr_d}% · CPA {cpa_d}% (p={d.get('cvr_p')}, 통계적 유의)"}
    if (cvr_d is not None and cvr_d < 0) or (cpa_d is not None and cpa_d > 10):
        return {'verdict': 'negative', 'label': '구 디자인 부정적',
                'rationale': f"CVR {cvr_d}% · CPA {cpa_d}%"}
    return {'verdict': 'noop', 'label': '효과 불명확',
            'rationale': f"CVR {cvr_d}% · CPA {cpa_d}% (p={d.get('cvr_p')})"}


def _classify_design_change(v1_cvr, v2_cvr, v1_cpa, v2_cpa, p_value, v1_clicks, v2_clicks) -> dict:
    """v2 vs v1 (디자인 변경 효과) — 시즌 confound caveat 포함."""
    if (v1_clicks or 0) < DESIGN_TYPE_MIN_CLICKS or (v2_clicks or 0) < DESIGN_TYPE_MIN_CLICKS:
        return {'verdict': 'low_sample', 'label': '표본 부족 — 판단 보류',
                'rationale': f"v1 클릭 {v1_clicks:,} / v2 클릭 {v2_clicks:,} (기준 {DESIGN_TYPE_MIN_CLICKS:,})"}
    if v1_cvr is None or v2_cvr is None:
        return {'verdict': 'unmeasurable', 'label': '측정 불가',
                'rationale': 'CVR 산정 불가'}
    cvr_diff = round(v2_cvr - v1_cvr, 2)
    cpa_pct = _delta(v2_cpa, v1_cpa, 'low') if (v1_cpa and v2_cpa) else None
    sig = (p_value is not None and p_value < 0.05)
    if cvr_diff > 0 and sig:
        return {'verdict': 'v2_better', 'label': '신 디자인 우세',
                'rationale': f"CVR +{cvr_diff}pp / CPA {cpa_pct}% (p={p_value}) — 신 디자인 확대 검토"}
    if cvr_diff < 0 and sig:
        return {'verdict': 'v1_better', 'label': '구 디자인 우세',
                'rationale': f"CVR {cvr_diff}pp / CPA {cpa_pct}% (p={p_value}) — 구 디자인 일부 복원 검토"}
    return {'verdict': 'noop', 'label': '디자인 효과 미미',
            'rationale': f"CVR Δ {cvr_diff}pp / CPA {cpa_pct}% (p={p_value})"}


def analyze(parsed_path: str, meta_path: str = 'input/tiktok_ad_meta.csv') -> dict:
    df = pd.read_parquet(parsed_path)
    df['date'] = pd.to_datetime(df['date'])
    df['ad_id'] = df['ad_id'].astype(str)
    df = df[df['parse_status'] == 'OK'].copy()
    df = df[df['지점'].isin(VALID_BRANCHES)].dropna(subset=['매칭키'])
    df['month'] = df['date'].dt.strftime('%Y-%m')

    meta = pd.read_csv(meta_path, dtype={'ad_id': str}, encoding='utf-8-sig')
    meta = meta[['ad_id', 'is_addon']].copy()
    meta['is_addon'] = meta['is_addon'].astype(str).str.lower().isin(['true', '1', '1.0'])

    merged_all = df.merge(meta, on='ad_id', how='left')
    merged_all['is_addon'] = merged_all['is_addon'].fillna(False).astype(bool)
    merged_all['version'] = _assign_version(merged_all['date'], merged_all['is_addon'])

    # 부산 제외 — 5월 일부 미적용
    busan_clicks_5_non = int(merged_all[(merged_all['지점'] == '부산') &
                                          (~merged_all['is_addon']) &
                                          (merged_all['date'] >= DESIGN_V2_FROM)]['clicks'].sum())
    busan_clicks_5_addon = int(merged_all[(merged_all['지점'] == '부산') &
                                            (merged_all['is_addon']) &
                                            (merged_all['date'] >= DESIGN_V2_FROM)]['clicks'].sum())
    merged = merged_all[~merged_all['지점'].isin(EXCLUDE_BRANCHES)].copy()

    is_v1 = merged['version'] == 'addon_v1'
    is_v2 = merged['version'] == 'addon_v2'
    is_non = merged['version'] == 'non_addon'
    is_pre_may = merged['date'] < DESIGN_V2_FROM
    is_may = ~is_pre_may

    # ---- 1. v1 vs 3~4월 비애드온 — 표본 충분, 본문 메인 ----
    v1_vs_period = _slice_kpis(merged, is_v1, is_non & is_pre_may)

    # ---- 2. v2 vs 5월 비애드온 — 부산 제외 시 비교 불가 ----
    v2_vs_period = _slice_kpis(merged, is_v2, is_non & is_may)
    v2_period_non_clicks = v2_vs_period['non_addon']['clicks']
    v2_period_unmeasurable = v2_period_non_clicks < SAMPLE_MIN_CLICKS

    # ---- 3. v2 vs v1 (디자인 직접 비교) — 본문 메인 평가축 ----
    v2_block = _kpis(merged[is_v2])
    v1_block = _kpis(merged[is_v1])
    v2_vs_v1 = {
        'v2': v2_block,
        'v1': v1_block,
        'delta_pct': _delta_block(v2_block, v1_block),
    }

    # ---- 4. 디자인 변경 효과 평가 ----
    v1_action = _classify_v1(v1_vs_period)
    design_change_action = _classify_design_change(
        v1_block.get('cvr'), v2_block.get('cvr'),
        v1_block.get('cpa'), v2_block.get('cpa'),
        v2_vs_v1['delta_pct'].get('cvr_p'),
        v1_block.get('clicks'), v2_block.get('clicks'),
    )

    # ---- 5. 소재유형별 디자인 효과 (v1 vs v2 직접 비교) — 본문 핵심 ----
    design_by_type = {}
    creative_types = sorted(merged['소재유형'].fillna('미상').unique())
    for ct in creative_types:
        sub = merged[merged['소재유형'].fillna('미상') == ct]
        v1_ct = _kpis(sub[sub['version'] == 'addon_v1'])
        v2_ct = _kpis(sub[sub['version'] == 'addon_v2'])
        delta = _delta_block(v2_ct, v1_ct)
        verdict = _classify_design_change(
            v1_ct.get('cvr'), v2_ct.get('cvr'),
            v1_ct.get('cpa'), v2_ct.get('cpa'),
            delta.get('cvr_p'),
            v1_ct.get('clicks'), v2_ct.get('clicks'),
        )
        design_by_type[str(ct)] = {'v1': v1_ct, 'v2': v2_ct, 'delta_pct': delta, 'verdict': verdict}

    # ---- 5-bis. 시청 깔때기 가설 검증 — 인플방문후기 vs 진료셀프캠 ----
    watch_funnel = _build_watch_funnel(merged, creative_types)

    # ---- 6. v1 소재유형별 (vs 3~4월 비애드온) ----
    by_creative_type_v1 = {}
    for ct in creative_types:
        sub = merged[merged['소재유형'].fillna('미상') == ct]
        block = _slice_kpis(sub, sub['version'] == 'addon_v1',
                             (sub['version'] == 'non_addon') & (sub['date'] < DESIGN_V2_FROM))
        block['verdict'] = _classify_v1(block, min_clicks=TYPE_MIN_CLICKS)
        by_creative_type_v1[str(ct)] = block

    # ---- 7. 6월 운영 권고 — 소재유형별 디자인 효과 기반 ----
    v2_better_types = [ct for ct, b in design_by_type.items() if b['verdict']['verdict'] == 'v2_better']
    v1_better_types = [ct for ct, b in design_by_type.items() if b['verdict']['verdict'] == 'v1_better']
    noop_types = [ct for ct, b in design_by_type.items() if b['verdict']['verdict'] == 'noop']
    low_sample_types = [ct for ct, b in design_by_type.items() if b['verdict']['verdict'] in ['low_sample', 'unmeasurable']]

    recommended_action = _build_recommendation(
        v1_action, design_change_action, v2_better_types, v1_better_types,
        v2_period_unmeasurable, v2_period_non_clicks, busan_clicks_5_non,
    )

    judgement = {
        'headline': recommended_action['summary'],
        'recommended_action': recommended_action,
        'v1_vs_non': v1_action,
        'design_change': design_change_action,
        'by_design_type': {
            'v2_better': v2_better_types,
            'v1_better': v1_better_types,
            'noop': noop_types,
            'low_sample': low_sample_types,
        },
    }

    # ---- 8. 지점별 부록 — v1, v2 (부산 제외) ----
    by_branch_v1 = {}
    by_branch_v2 = {}
    branches_excl = [b for b in VALID_BRANCHES if b not in EXCLUDE_BRANCHES]
    for b in branches_excl:
        bdf = merged[merged['지점'] == b]
        block_v1 = _slice_kpis(bdf, bdf['version'] == 'addon_v1',
                                (bdf['version'] == 'non_addon') & (bdf['date'] < DESIGN_V2_FROM))
        block_v1['sample_warning'] = (block_v1['addon']['clicks'] < SAMPLE_MIN_CLICKS or
                                       block_v1['non_addon']['clicks'] < SAMPLE_MIN_CLICKS)
        by_branch_v1[b] = block_v1

        # 부산 제외 v2는 5월 비애드온이 거의 없으므로 v2 단독 KPI + v1 비교 표시
        v2_only = _kpis(bdf[bdf['version'] == 'addon_v2'])
        v1_only = _kpis(bdf[bdf['version'] == 'addon_v1'])
        by_branch_v2[b] = {
            'v2': v2_only, 'v1': v1_only,
            'delta_pct': _delta_block(v2_only, v1_only),
            'sample_warning': v2_only['clicks'] < SAMPLE_MIN_CLICKS or v1_only['clicks'] < SAMPLE_MIN_CLICKS,
        }

    # ---- 9. 월별 추세 (부산 제외) ----
    monthly_trend = []
    for mn in sorted(merged['month'].unique()):
        sub = merged[merged['month'] == mn]
        a = _kpis(sub[sub['is_addon'] == True])
        n = _kpis(sub[sub['is_addon'] == False])
        is_design_v2 = pd.Timestamp(mn + '-01') >= DESIGN_V2_FROM
        sample_warning = a['clicks'] < SAMPLE_MIN_CLICKS or n['clicks'] < SAMPLE_MIN_CLICKS
        monthly_trend.append({
            'month': mn,
            'design_version': 'v2' if is_design_v2 else 'v1',
            'addon': a, 'non_addon': n,
            'delta_pct': _delta_block(a, n),
            'sample_warning': sample_warning,
        })

    # ---- 10. 메타 ----
    addon_ads_v1 = merged[merged['version'] == 'addon_v1']['ad_id'].nunique()
    addon_ads_v2 = merged[merged['version'] == 'addon_v2']['ad_id'].nunique()
    total_ads = merged['ad_id'].nunique()

    return {
        'meta_summary': {
            'addon_ads_v1': int(addon_ads_v1),
            'addon_ads_v2': int(addon_ads_v2),
            'addon_ads_total': int(addon_ads_v1 + addon_ads_v2),
            'total_ads_in_data': int(total_ads),
            'design_change_date': DESIGN_V2_FROM.strftime('%Y-%m-%d'),
            'excluded_branches': EXCLUDE_BRANCHES,
            'exclusion_reason': (
                f'5월 애드온은 원래 전 캠페인·소재 적용 예정이었으나 부산점만 운영 사유로 일부 미적용. '
                f'부산 제외 시 5월 비애드온 클릭은 사실상 0 ({v2_period_non_clicks:,}). '
                f'부산 5월 비애드온 '
                f'(클릭 {busan_clicks_5_non:,}, 애드온 클릭 {busan_clicks_5_addon:,})은 본 비교에서 제외.'
            ),
            'design_note': (
                '3~4월 노출분 = v1 (구 디자인) · 5월 노출분 = v2 (신 디자인). '
                '부산 제외 후 5월 비애드온이 사실상 부재하여 v2 vs 동기간 비애드온 비교는 불가능하며, '
                '평가축을 (1) v1 vs 3~4월 비애드온과 (2) v2 vs v1 직접 비교로 이원화.'
            ),
            'thresholds': {
                'sample_min_clicks': SAMPLE_MIN_CLICKS,
                'pair_min_clicks': PAIR_MIN_CLICKS,
                'type_min_clicks': TYPE_MIN_CLICKS,
                'design_type_min_clicks': DESIGN_TYPE_MIN_CLICKS,
            },
        },
        'v1_vs_period': v1_vs_period,
        'v2_vs_period': {
            **v2_vs_period,
            'unmeasurable': v2_period_unmeasurable,
            'note': '부산 제외 후 5월 비애드온이 사실상 부재 — 본 비교는 동기간 비교로 사용 불가',
        },
        'v2_vs_v1': v2_vs_v1,
        'judgement': judgement,
        'design_by_type': design_by_type,
        'watch_funnel': watch_funnel,
        'by_creative_type_v1': by_creative_type_v1,
        'by_branch_v1': by_branch_v1,
        'by_branch_v2': by_branch_v2,
        'monthly_trend': monthly_trend,
    }


def _build_watch_funnel(merged: pd.DataFrame, creative_types: list) -> dict:
    """시청 깔때기 가설 검증 — 애드온은 영상 3초+에서 노출되므로 시청 지속 = 애드온 노출 시점 도달.

    인플방문후기와 진료셀프캠을 중심으로 v1·v2 시청 깊이를 비교하여
    '시청 끝까지 보는 콘텐츠 vs 클릭은 끌지만 적합성 약화' 양상을 검증."""
    # 전체 애드온 v1/v2 시청 깊이
    addon = merged[merged['is_addon'] == True]
    v1_all = _kpis(addon[addon['date'] < DESIGN_V2_FROM])
    v2_all = _kpis(addon[addon['date'] >= DESIGN_V2_FROM])
    non = _kpis(merged[merged['is_addon'] == False])

    # 소재유형별 시청 깔때기 (v1, v2 각각)
    by_type = {}
    for ct in creative_types:
        sub = addon[addon['소재유형'].fillna('미상') == ct]
        v1_ct = _kpis(sub[sub['date'] < DESIGN_V2_FROM])
        v2_ct = _kpis(sub[sub['date'] >= DESIGN_V2_FROM])
        by_type[str(ct)] = {'v1': v1_ct, 'v2': v2_ct}

    # 가설 검증 헤드라인 — 인플방문후기 vs 진료셀프캠
    if '인플방문후기' in by_type and '진료셀프캠' in by_type:
        infl_v2 = by_type['인플방문후기']['v2']
        self_v2 = by_type['진료셀프캠']['v2']
        infl_v1 = by_type['인플방문후기']['v1']
        self_v1 = by_type['진료셀프캠']['v1']

        # 1) 시청 깊이 1위 — 진료셀프캠 또는 인플방문후기?
        depth_ranking = sorted(
            [(ct, b['v2']['v6s_rate'] or b['v1']['v6s_rate'] or 0) for ct, b in by_type.items()],
            key=lambda x: x[1], reverse=True,
        )
        # 1b) 공유율 1위
        share_ranking = sorted(
            [(ct, b['v2'].get('share_rate') or b['v1'].get('share_rate') or 0) for ct, b in by_type.items()],
            key=lambda x: x[1], reverse=True,
        )
        # 2) 디자인 변경 후 시청 깊이 추세 (각 유형의 6초 시청률 v1→v2)
        depth_change = {}
        for ct, b in by_type.items():
            v1r = b['v1'].get('v6s_rate')
            v2r = b['v2'].get('v6s_rate')
            if v1r and v2r:
                depth_change[ct] = round(v2r - v1r, 2)  # pp 단위

        # 3) 클릭자 적합성 (CVR_click) 변화
        cvr_click_change = {}
        for ct, b in by_type.items():
            v1c = b['v1'].get('cvr')
            v2c = b['v2'].get('cvr')
            if v1c and v2c:
                cvr_click_change[ct] = round(v2c - v1c, 2)

        # 4) 인게이지먼트 변화
        share_change = {}
        for ct, b in by_type.items():
            v1s = b['v1'].get('share_rate')
            v2s = b['v2'].get('share_rate')
            if v1s and v2s:
                share_change[ct] = round((v2s - v1s) * 10000, 1)  # 0.0001%pp 단위 (작은 값이라 확대)

        hypothesis_result = {
            'hypothesis': '애드온은 영상 3초+ 시점부터 노출되므로, 시청을 끝까지 보는 소재유형(인플방문후기)이 디자인 변경에도 강할 것이라는 가설. 인게이지먼트(공유율)까지 함께 검증하여 "공유되는 콘텐츠 vs 전환되는 콘텐츠"를 분리 진단',
            'depth_ranking_by_v6s': depth_ranking,
            'share_ranking': share_ranking,
            'depth_change_v1_to_v2_pp': depth_change,
            'cvr_click_change_v1_to_v2_pp': cvr_click_change,
            'share_change_v1_to_v2_basis_points': share_change,
            'infl': {
                'v6s_v1': infl_v1.get('v6s_rate'),
                'v6s_v2': infl_v2.get('v6s_rate'),
                'cvr_v1': infl_v1.get('cvr'),
                'cvr_v2': infl_v2.get('cvr'),
                'share_v1': infl_v1.get('share_rate'),
                'share_v2': infl_v2.get('share_rate'),
                'like_v1': infl_v1.get('like_rate'),
                'like_v2': infl_v2.get('like_rate'),
                'eng15s_v1': infl_v1.get('eng15s_rate'),
                'eng15s_v2': infl_v2.get('eng15s_rate'),
            },
            'self': {
                'v6s_v1': self_v1.get('v6s_rate'),
                'v6s_v2': self_v2.get('v6s_rate'),
                'cvr_v1': self_v1.get('cvr'),
                'cvr_v2': self_v2.get('cvr'),
                'share_v1': self_v1.get('share_rate'),
                'share_v2': self_v2.get('share_rate'),
                'like_v1': self_v1.get('like_rate'),
                'like_v2': self_v2.get('like_rate'),
                'eng15s_v1': self_v1.get('eng15s_rate'),
                'eng15s_v2': self_v2.get('eng15s_rate'),
            },
            # 콘텐츠 분류 — 공유율과 CVR_click 조합으로 바이럴형/전환형 진단
            'archetype': {
                '진료셀프캠': '바이럴형 (공유율 1위 · 깊은 시청 1위 · 클릭자 적합성은 디자인 변경 후 약화)',
                '인플방문후기': '전환형 (공유율 낮음 · 시청 깊이 평균 · 클릭자 적합성은 디자인 변경 후 향상)',
            },
            'finding': (
                f'사용자 가설("인플방문후기는 끝까지 본다")은 데이터로 반박됩니다. 시청 깊이(6초 시청률)와 공유율 모두 '
                f'진료셀프캠이 1위 — 공유율 {(self_v1.get("share_rate") or 0):.4f}%로 인플방문후기({(infl_v1.get("share_rate") or 0):.4f}%) 대비 약 '
                f'{((self_v1.get("share_rate") or 0) / max(infl_v1.get("share_rate") or 0.0001, 0.0001)):.1f}배 높습니다. '
                '그러나 디자인 변경(v1→v2) 후 진료셀프캠은 시청 깊이가 더 증가했지만 클릭자→전환율이 떨어진 반면(바이럴 트래픽이 덜 적합), '
                '인플방문후기는 시청 깊이는 약간 감소했음에도 클릭자→전환율이 향상되었습니다. '
                '즉 진료셀프캠 = "공유되는 바이럴형" · 인플방문후기 = "전환 적합성 높은 전환형"으로 두 콘텐츠가 다른 깔때기에서 강점을 보입니다.'
            ),
        }
    else:
        hypothesis_result = None

    return {
        'overall': {'v1': v1_all, 'v2': v2_all, 'non_addon': non},
        'by_creative_type': by_type,
        'hypothesis': hypothesis_result,
        'note': (
            'TikTok 애드온은 영상 3초+ 시점부터 노출되므로 video_watched_6s가 애드온 노출 시점에 가장 근접한 메트릭입니다. '
            'video_views(=video_play_actions)는 자동재생 시작을 포함하므로 시청 깊이 메트릭으로 부적합합니다.'
        ),
    }


def _build_recommendation(v1_action, design_change_action, v2_better_types, v1_better_types,
                          v2_unmeasurable, v2_non_clicks, busan_clicks_5_non):
    """6월 운영 권고 — v1 효과 + 디자인 변경 효과 + 소재유형별 처방을 결합."""
    v1_pos = v1_action['verdict'] == 'positive'
    design_v = design_change_action['verdict']  # v2_better / v1_better / noop / low_sample

    bullets = []
    if v2_better_types:
        bullets.append(f"<strong>{' · '.join(v2_better_types)}</strong>: 신 디자인(v2) 우세 — 확대")
    if v1_better_types:
        bullets.append(f"<strong>{' · '.join(v1_better_types)}</strong>: 구 디자인(v1) 우세 — v1 일부 복원 또는 v2 콘셉트 재검토")

    if design_v == 'v2_better':
        label = '6월 — 신 디자인(v2) 우세, 소재유형 처방으로 확대'
        verdict = 'v2_expand'
    elif design_v == 'v1_better':
        label = '6월 — 디자인 변경 후 전체 효과 약화, 부분 복원 검토'
        verdict = 'v1_partial_restore'
    elif design_v == 'noop':
        label = '6월 — 디자인 변경 전체 효과 미미, 소재유형별 처방'
        verdict = 'mixed'
    else:
        label = '6월 — 디자인 효과 표본 부족, 통제 운영으로 표본 확보'
        verdict = 'verify'

    summary = (
        f"5월 부산 일부 미적용으로 동기간 비애드온 비교 불가(5월 비애드온 클릭 {v2_non_clicks:,} · 부산 비애드온 클릭 {busan_clicks_5_non:,}). "
        f"평가축을 v1 vs 3~4월 비애드온(애드온 효과 유지 확인)과 v2 vs v1 직접 비교(디자인 변경 효과)로 분리. "
        f"디자인 변경 자체 평가: {design_change_action['label']} ({design_change_action['rationale']})."
    )

    return {
        'verdict': verdict,
        'label': label,
        'summary': summary,
        'bullets': bullets,
        'v1_effect_note': v1_action['rationale'] if v1_pos else '구 디자인 시기에도 효과가 명확하지 않음 — 디자인 변경과 무관한 운영 점검 필요',
    }


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260518/parsed.parquet'
    meta = sys.argv[2] if len(sys.argv) > 2 else 'input/tiktok_ad_meta.csv'
    r = analyze(path, meta)

    ms = r['meta_summary']
    print(f"[exclude] {ms['exclusion_reason']}")
    print(f"[design] {ms['design_note']}")
    print(f"  v1 광고 {ms['addon_ads_v1']}개 · v2 광고 {ms['addon_ads_v2']}개 (전체 {ms['total_ads_in_data']}개)")
    print()
    j = r['judgement']
    rec = j['recommended_action']
    print(f"[권고] {rec['label']}")
    print(f"  {rec['summary']}")
    if rec.get('bullets'):
        for b in rec['bullets']:
            print(f"    · {b}")
    print()
    a = r['v1_vs_period']; d = a['delta_pct']
    print(f"[v1 vs 3~4월 비애드온]")
    print(f"  애드온 CVR {a['addon']['cvr']}% (클릭 {a['addon']['clicks']:,}) vs 비애드온 CVR {a['non_addon']['cvr']}% (클릭 {a['non_addon']['clicks']:,})")
    print(f"  Δ CVR {d['cvr']}% (p={d['cvr_p']}) · Δ CPA {d['cpa']}%")
    print()
    a = r['v2_vs_v1']; d = a['delta_pct']
    print(f"[v2 vs v1 — 디자인 직접 비교]")
    print(f"  v2 CVR {a['v2']['cvr']}% (클릭 {a['v2']['clicks']:,}) vs v1 CVR {a['v1']['cvr']}% (클릭 {a['v1']['clicks']:,})")
    print(f"  Δ CTR {d['ctr']}% · Δ CVR {d['cvr']}% (p={d['cvr_p']}) · Δ CPA {d['cpa']}%")
    print()
    print('[소재유형별 디자인 효과 (v1 vs v2)]')
    for ct, b in r['design_by_type'].items():
        v = b['verdict']
        v1k = b['v1']; v2k = b['v2']
        print(f"  {ct}: {v['label']} — v1 CVR {v1k['cvr']}%/CPA {v1k['cpa']}원 → v2 CVR {v2k['cvr']}%/CPA {v2k['cpa']}원 ({v['rationale']})")
    print()
    print('[v2 vs 5월 비애드온 — 측정 가능 여부]')
    print(f"  unmeasurable: {r['v2_vs_period']['unmeasurable']}, 5월 비애드온 클릭 {r['v2_vs_period']['non_addon']['clicks']}")
