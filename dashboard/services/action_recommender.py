"""추천 액션 엔진 — operation_rules.yaml 기반 오늘의 실행 큐 생성

홈 3.2 "오늘 해야 할 일" 영역. 4개 카테고리:
  - 💰 예산 조정 (증액·감액 후보)
  - 🎬 소재 ON/OFF (광고 단위)
  - ⚙️  세팅 확인
  - ⏸  보류·관찰
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from dashboard.services.data_loader import DataBundle


@dataclass
class Recommendation:
    category: str           # budget / ad / setting / hold
    icon: str
    title: str              # "부평 +10% 증액"
    rationale: str          # 한 줄 근거
    target_type: str        # branch | ad | adgroup
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    priority: str = 'medium'   # high | medium | low
    expected_metric: Optional[str] = None
    linked_rule: Optional[str] = None
    linked_checklist: Optional[str] = None


def generate(bundle: DataBundle) -> dict:
    """카테고리별 추천 액션 묶음."""
    rules = bundle.operation_rules or {}
    meta = rules.get('meta', {})

    return {
        'budget_increase': _budget_increase(bundle, rules, meta),
        'budget_decrease': _budget_decrease(bundle, rules, meta),
        'ad_off': _ad_off_candidates(bundle, rules, meta),
        'ad_on': _ad_on_candidates(bundle, rules, meta),
        'setting': _setting_alerts(bundle, rules, meta),
        'hold': _hold_observations(bundle, rules, meta),
    }


def _branch_3day_kpi(bundle: DataBundle, branch: str) -> dict:
    """지점별 직전 3일 KPI 집계."""
    parsed = bundle.parsed
    if parsed.empty:
        return {}
    parsed = parsed.copy()
    parsed['date'] = pd.to_datetime(parsed['date'])
    max_date = parsed['date'].max()
    cutoff = max_date - pd.Timedelta(days=2)
    recent = parsed[(parsed['date'] >= cutoff) & (parsed['지점'] == branch)]
    if recent.empty:
        return {}
    cost = int(recent['cost'].sum())
    impr = int(recent['impressions'].sum())
    clicks = int(recent['clicks'].sum())
    conv = int(recent['conversions'].sum())
    return {
        'cost': cost,
        'impressions': impr,
        'clicks': clicks,
        'conversions': conv,
        'cpa': round(cost / conv) if conv else None,
        'cvr': round(conv / clicks * 100, 2) if clicks else None,
        'ctr': round(clicks / impr * 100, 2) if impr else None,
    }


def _budget_increase(bundle: DataBundle, rules: dict, meta: dict) -> list[Recommendation]:
    """효율 우수 + 노출 여유 지점."""
    target_cpa = meta.get('proposal_target_cpa', 27278)
    out = []
    common_mod = __import__('common', fromlist=['VALID_BRANCHES'])
    for b in common_mod.VALID_BRANCHES:
        kpi = _branch_3day_kpi(bundle, b)
        if not kpi or not kpi.get('cpa'):
            continue
        cpa = kpi['cpa']
        if cpa <= target_cpa * 0.85:
            out.append(Recommendation(
                category='budget',
                icon='💰',
                title=f'{b} 광고 그룹 예산 +10% 증액',
                rationale=f'3일 평균 CPA {cpa:,}원 (가드레일 {target_cpa:,}원의 85% 이하)',
                target_type='branch', target_name=b,
                priority='high' if cpa <= target_cpa * 0.70 else 'medium',
                expected_metric='conversions',
                linked_rule='efficient_branch_expand',
            ))
    return out


def _budget_decrease(bundle: DataBundle, rules: dict, meta: dict) -> list[Recommendation]:
    """가드레일 초과 지점."""
    target_cpa = meta.get('proposal_target_cpa', 27278)
    out = []
    common_mod = __import__('common', fromlist=['VALID_BRANCHES'])
    for b in common_mod.VALID_BRANCHES:
        kpi = _branch_3day_kpi(bundle, b)
        if not kpi or not kpi.get('cpa'):
            continue
        cpa = kpi['cpa']
        if cpa > target_cpa * 1.20:
            out.append(Recommendation(
                category='budget',
                icon='💰',
                title=f'{b} 광고 그룹 예산 -10% (가드레일 +20% 초과)',
                rationale=f'3일 평균 CPA {cpa:,}원 (가드레일 {target_cpa:,}원의 +20% 초과)',
                target_type='branch', target_name=b,
                priority='high',
                expected_metric='cpa',
                linked_rule='cpa_guardrail_breach',
            ))
    return out


def _ad_off_candidates(bundle: DataBundle, rules: dict, meta: dict) -> list[Recommendation]:
    """TIER4 + 7일+ + CPA *1.5 초과 광고 단위."""
    ct = bundle.creative_tier
    if ct.empty:
        return []
    target_cpa = meta.get('proposal_target_cpa', 27278)
    out = []
    for _, r in ct.iterrows():
        tier = str(r.get('TIER', '')).upper()
        days = r.get('집행일수', 0)
        cpa = r.get('CPA')
        cvr = r.get('CVR')
        clicks = r.get('총클릭', 0)
        cost = r.get('총비용', 0)
        name = r.get('소재명', '') or r.get('매칭키', '')
        if pd.isna(cpa) or pd.isna(days):
            continue
        if tier == 'TIER4' and days >= 7 and cpa > target_cpa * 1.5:
            out.append(Recommendation(
                category='ad', icon='🎬',
                title=f'OFF 후보: {name}',
                rationale=f'TIER4 · 집행 {int(days)}일 · CPA {int(cpa):,}원 (가드 +50% 초과)',
                target_type='ad', target_name=name,
                priority='high',
                linked_rule='tier4_long_run',
            ))
        elif cvr is not None and not pd.isna(cvr) and cvr < 1.0 and clicks >= 100 and cost >= 100000:
            out.append(Recommendation(
                category='ad', icon='🎬',
                title=f'OFF 후보: {name}',
                rationale=f'CVR {float(cvr):.2f}% · 클릭 {int(clicks)} · 비용 {int(cost):,}원',
                target_type='ad', target_name=name,
                priority='high',
                linked_rule='low_cvr_with_volume',
            ))
    return out[:10]   # 상위 10개


def _ad_on_candidates(bundle: DataBundle, rules: dict, meta: dict) -> list[Recommendation]:
    """TIER1 + 운영 여유 광고 단위 (확장)."""
    ct = bundle.creative_tier
    if ct.empty:
        return []
    out = []
    for _, r in ct.iterrows():
        tier = str(r.get('TIER', '')).upper()
        cost = r.get('총비용', 0)
        cvr = r.get('CVR')
        name = r.get('소재명', '') or r.get('매칭키', '')
        if pd.isna(cost):
            continue
        if tier == 'TIER1' and cost < 200000:   # 노출 적은 TIER1
            out.append(Recommendation(
                category='ad', icon='🎬',
                title=f'확대 후보: {name}',
                rationale=f'TIER1 · 누적 비용 {int(cost):,}원 (확장 여지)',
                target_type='ad', target_name=name,
                priority='medium',
                linked_rule='tier1_expand_room',
            ))
        elif tier == 'UNCLASSIFIED' and cvr is not None and not pd.isna(cvr) and float(cvr) >= 5.0:
            out.append(Recommendation(
                category='ad', icon='🎬',
                title=f'신규 추적: {name}',
                rationale=f'UNCLASSIFIED · CVR {float(cvr):.2f}% (집행일수 충족 시 TIER 평가)',
                target_type='ad', target_name=name,
                priority='low',
                linked_rule='new_creative_promising',
            ))
    return out[:10]


def _setting_alerts(bundle: DataBundle, rules: dict, meta: dict) -> list[Recommendation]:
    """제안서 부록에서 추출한 세팅 점검 항목."""
    out = []
    # 천안 지역 누수
    geo = (bundle.proposal or {}).get('geo_leakage') or {}
    if geo.get('available'):
        cheonan = (geo.get('by_branch') or {}).get('천안') or {}
        leak = cheonan.get('leakage_pct')
        if leak and leak >= 15:
            out.append(Recommendation(
                category='setting', icon='⚙️',
                title='천안 광고 그룹 지역 타겟팅 점검',
                rationale=f'경기 노출 {leak}% (15% 초과)',
                target_type='branch', target_name='천안',
                priority='high',
                linked_rule='cheonan_geo_leakage',
                linked_checklist='w1_cheonan_geo_setting_check',
            ))
    # 성별 누수
    th = (bundle.proposal or {}).get('targeting_health') or {}
    if th.get('available'):
        male_pct = (th.get('gender_summary') or {}).get('male_impr_pct') or 0
        if male_pct > 0.5:
            out.append(Recommendation(
                category='setting', icon='⚙️',
                title='성별 타겟팅 여성 고정 설정 확인',
                rationale=f'남성 노출 {male_pct}% 감지',
                target_type='global', target_name='성별 타겟팅',
                priority='high',
                linked_rule='gender_leak',
            ))
        # 25-34 비효율
        ageSig = th.get('age_signal') or {}
        if ageSig.get('verdict') == 'inefficient':
            out.append(Recommendation(
                category='setting', icon='⚙️',
                title='25-34 연령대 광고 그룹 제외 확인',
                rationale=ageSig.get('rationale', ''),
                target_type='global', target_name='연령 타겟팅',
                priority='medium',
                linked_rule='age_inefficient_zone',
            ))
    return out


def _hold_observations(bundle: DataBundle, rules: dict, meta: dict) -> list[Recommendation]:
    """보류·관찰 — 표본 부족 신규 소재 + 진행 중 테스트."""
    out = []
    # 25-34 수원 한정 테스트 진행 중
    th = (bundle.proposal or {}).get('targeting_health') or {}
    if th.get('available'):
        ah = th.get('age_history') or {}
        post = (ah.get('post_exclusion_branches') or {}).get('수원')
        if post:
            out.append(Recommendation(
                category='hold', icon='⏸',
                title='25-34 수원 한정 테스트 결과 대기',
                rationale=f'수원 25-34 CVR {post.get("cvr")}% · 회복 기준 3% 대기',
                target_type='branch', target_name='수원',
                priority='low',
                linked_checklist='w2_25_34_suwon_tracking',
            ))
    # UNCLASSIFIED 소재 (집행 5일 이하)
    ct = bundle.creative_tier
    if not ct.empty:
        unc = ct[ct['TIER'] == 'UNCLASSIFIED']
        cnt = len(unc)
        if cnt > 0:
            out.append(Recommendation(
                category='hold', icon='⏸',
                title=f'UNCLASSIFIED 소재 {cnt}개 — 집행 7일 도달 시 TIER 재평가',
                rationale='신규 도입 소재 — 학습 기간 중',
                target_type='global', target_name='UNCLASSIFIED',
                priority='low',
                linked_rule='learning_period',
            ))
    return out


def total_action_count(recs: dict) -> int:
    return sum(len(v) for v in recs.values())


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    from dashboard.services.data_loader import load_bundle
    bundle = load_bundle()
    recs = generate(bundle)
    print(f'[총 추천 액션] {total_action_count(recs)}개')
    for cat, items in recs.items():
        if not items:
            continue
        print(f'\n=== {cat} ({len(items)}) ===')
        for r in items[:8]:
            print(f'  {r.icon} [{r.priority}] {r.title}')
            print(f'        근거: {r.rationale}')
