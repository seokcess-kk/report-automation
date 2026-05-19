"""컨설팅 보고서 보조 지표 산출 (codex Round 2 권장)

기존 분석 결과를 종합해 보고서 표/카드에 직접 노출할 8개 보조 지표를 만든다.

산출물 키:
  - primary_gap          : 지점별 전환/CPA 갭 (목표 대비)
  - funnel_status        : 지점×퍼널 good/warn/bad
  - bottleneck_type      : 지점별 핵심 병목 (CPM/CTR/CVR/none/new)
  - priority_score       : 지점별 6월 우선순위 점수 + High/Mid/Low
  - expected_impact_range: 그룹별 기대 효과 범위 (전환수)
  - guardrail            : 지점별 증액/실험 중단 조건
  - creative_role        : 지점×퍼널 추천 소재 역할
  - confidence_level     : 지점별 데이터 충분도
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES

# 소재 역할 분류 (codex 권장 7가지)
CREATIVE_ROLES = {
    'CPM': '지역명확형',       # 노출 효율 - 지역 좁히기로 단가 ↓
    'CTR': '후킹강화형',       # 클릭 반응 - 첫 3초 후킹
    'CVR': '상담전환형',       # 전환 - CTA/랜딩 정합성
}

# 보조 분류 (랜딩 hero "첫 달 9만원" 정합성 고려)
CREATIVE_ROLE_LIBRARY = [
    '할인혜택형',       # 랜딩 hero 직접 호응 ("9만원" 강조). 클릭 의도 명확
    '후기형',           # 실 환자 후기, 변화. 신뢰 형성 후 할인 hero로 자연 연결
    '상담전환형',       # 직접 CTA, 5단계 폼 진입 유도
    '의료진정보형',     # 의료진 소개, 진료 방식 (랜딩에 의료진 정보 약함 - 정합성 검증 필요)
    '신뢰형',           # 의료기관 신뢰, 원장 인터뷰
    '지역명확형',       # 지점/지역 강조 (랜딩 지점명이 하단이라 소재에서 보완)
    '재방문리마인드형', # 재내원, 리마인드
]


def _grade_vs_peer(value: float | None, peer: float | None, direction: str, thresh_warn: float = 0.10, thresh_bad: float = 0.20) -> str:
    """전 지점 평균 대비 good/warn/bad/na.

    direction='low' (CPM/CPA): peer 대비 낮으면 good
    direction='high' (CTR/CVR/전환): peer 대비 높으면 good
    thresh_warn/bad: 평균 대비 이탈 비율 임계값
    """
    if value is None or peer is None or peer == 0:
        return 'na'
    ratio = value / peer
    if direction == 'low':
        if ratio <= 1 - thresh_warn:
            return 'good'
        if ratio >= 1 + thresh_bad:
            return 'bad'
        if ratio >= 1 + thresh_warn:
            return 'warn'
        return 'good' if ratio <= 1 else 'mid'
    # high
    if ratio >= 1 + thresh_warn:
        return 'good'
    if ratio <= 1 - thresh_bad:
        return 'bad'
    if ratio <= 1 - thresh_warn:
        return 'warn'
    return 'good' if ratio >= 1 else 'mid'


def _gap_pct(current: float | None, target: float | None, direction: str) -> float | None:
    """현재 → 목표까지 거리 (양수=달성, 음수=개선 필요)."""
    if current is None or target is None or current == 0 or target == 0:
        return None
    if direction == 'low':
        # CPA/CPM: 현재가 목표보다 낮으면 좋음. (target - current) / target
        return round((target - current) / target * 100, 1)
    # 전환/CTR/CVR: 현재가 목표보다 높으면 좋음. (current - target) / target
    return round((current - target) / target * 100, 1)


def _gap_status(gap: float | None, direction: str = 'high') -> str:
    """갭% → good/warn/bad.

    gap이 양수 = 달성, 음수 = 개선 필요. (지표별 방향성은 _gap_pct에서 이미 처리됨)
    """
    if gap is None:
        return 'na'
    if gap >= 0:
        return 'good'
    if gap >= -10:
        return 'warn'
    return 'bad'


def derive(june_targets: dict, root_cause: dict, conversion_perspective: dict,
           action_table: dict, recommendations: dict, top_creatives: dict,
           creative_type: dict, keyword_analysis: dict | None = None) -> dict:
    """모든 보조 지표를 한 번에 산출."""

    peer = root_cause.get('peer_avg', {}) or {}
    cp_by = conversion_perspective.get('by_branch', {}) or {}
    targets_by = june_targets.get('by_branch', {}) or {}
    action_rows = {r['branch']: r for r in (action_table.get('rows') or [])}
    rec_by = recommendations.get('by_branch', {}) or {}

    by_branch = {}
    for branch in VALID_BRANCHES:
        bd = cp_by.get(branch, {}) or {}
        pt = bd.get('period_total') or {}  # 정상 운영 누적 (실제값)
        target = (targets_by.get(branch, {}) or {}).get('targets') or {}
        ar = action_rows.get(branch, {}) or {}

        # 1. primary_gap (전환/CPA)
        conv_actual = pt.get('conversions')
        conv_target = (target.get('conversions') or {}).get('value')
        cpa_actual = pt.get('cpa')
        cpa_target = (target.get('cpa') or {}).get('value')

        primary_gap = {
            'conversions': {
                'actual': conv_actual,
                'target': conv_target,
                'gap_pct': _gap_pct(conv_actual, conv_target, 'high'),
                'status': _gap_status(_gap_pct(conv_actual, conv_target, 'high')),
            },
            'cpa': {
                'actual': cpa_actual,
                'target': cpa_target,
                'gap_pct': _gap_pct(cpa_actual, cpa_target, 'low'),
                'status': _gap_status(_gap_pct(cpa_actual, cpa_target, 'low')),
            },
        }

        # 2. funnel_status (3퍼널 good/warn/bad)
        funnel_status = {
            'cpm': {
                'value': pt.get('cpm'),
                'peer': peer.get('cpm'),
                'status': _grade_vs_peer(pt.get('cpm'), peer.get('cpm'), 'low'),
                'target': (target.get('cpm') or {}).get('value'),
                'gap_pct': _gap_pct(pt.get('cpm'), (target.get('cpm') or {}).get('value'), 'low'),
            },
            'ctr': {
                'value': pt.get('ctr'),
                'peer': peer.get('ctr'),
                'status': _grade_vs_peer(pt.get('ctr'), peer.get('ctr'), 'high'),
                'target': (target.get('ctr') or {}).get('value'),
                'gap_pct': _gap_pct(pt.get('ctr'), (target.get('ctr') or {}).get('value'), 'high'),
            },
            'cvr': {
                'value': pt.get('cvr'),
                'peer': peer.get('cvr'),
                'status': _grade_vs_peer(pt.get('cvr'), peer.get('cvr'), 'high'),
                'target': (target.get('cvr') or {}).get('value'),
                'gap_pct': _gap_pct(pt.get('cvr'), (target.get('cvr') or {}).get('value'), 'high'),
            },
        }

        # 3. bottleneck_type (CPM/CTR/CVR 중 가장 약한 것)
        is_new = bd.get('is_new_branch') or not pt
        if is_new:
            bottleneck_type = 'new'
        else:
            # 약한 순으로 정렬 (bad > warn > mid > good)
            order = {'bad': 0, 'warn': 1, 'mid': 2, 'good': 3, 'na': 4}
            ranks = sorted(
                [(k, order[v['status']]) for k, v in funnel_status.items() if v['status'] != 'na'],
                key=lambda x: x[1],
            )
            worst = ranks[0] if ranks else None
            bottleneck_type = worst[0].upper() if worst and worst[1] <= 1 else 'none'  # bad/warn만 병목으로

        # 4. priority_score (High/Mid/Low)
        score = 0
        # 전환 갭 점수
        cg = primary_gap['conversions']['gap_pct']
        if cg is not None and cg < -10:
            score += 3
        elif cg is not None and cg < 0:
            score += 1
        # CPA 갭 점수
        pag = primary_gap['cpa']['gap_pct']
        if pag is not None and pag < -10:
            score += 3
        elif pag is not None and pag < 0:
            score += 1
        # CVR 우려 점수
        if funnel_status['cvr']['status'] == 'bad':
            score += 2
        elif funnel_status['cvr']['status'] == 'warn':
            score += 1
        # 전환 기여도 보정 (상위 지점은 영향 큼)
        share = bd.get('conv_share_pct') or 0
        if share >= 15:
            score += 1
        if is_new:
            priority = 'New'
        elif score >= 5:
            priority = 'High'
        elif score >= 2:
            priority = 'Mid'
        else:
            priority = 'Low'

        # 5. expected_impact_range (기대 전환 증가)
        # 보수 추정: gap의 30%~70%만큼 회복 시 추가 전환
        impact_min, impact_max = None, None
        if cg is not None and cg < 0 and conv_target:
            gap_abs = abs(cg) / 100  # 0.10 = 10%
            recovery_min, recovery_max = 0.3, 0.7
            base = conv_actual or 0
            additional_min = int(base * gap_abs * recovery_min)
            additional_max = int(base * gap_abs * recovery_max)
            impact_min, impact_max = additional_min, additional_max
        expected_impact = {
            'conversion_gain_min': impact_min,
            'conversion_gain_max': impact_max,
            'basis': '갭 회복률 30~70% 가정',
        } if impact_min is not None else None

        # 6. guardrail (증액/실험 중단 조건)
        ar_group = ar.get('group', 'B')
        if is_new:
            guardrail = 'CPA가 전 지점 평균 +15% 초과 시 학습 보류, CTR/CVR 안정화 후 광고 그룹 예산 확대 검토'
        elif ar_group == 'A':
            guardrail = 'CVR이 회복(목표 갭 -5% 이내) 전까지 광고 그룹(지점) 예산 증액 보류, CPA 추가 악화 +10% 시 즉시 중단. 저성과 소재는 광고 단위 OFF로 조정 (소재별 예산 조정 불가)'
        elif ar_group == 'B':
            guardrail = '광고 그룹 예산 +5~10% 점진 증액, CPA 목표 대비 +10% 초과 또는 CPM +15% 상승 시 증액 중단'
        else:
            guardrail = '신규 패턴 모니터링, 데이터 14일 누적 후 그룹 재평가'

        # 7. creative_role (병목별 추천 역할) - 랜딩 hero "9만원 할인" + 5단계 폼 정합성 고려
        if bottleneck_type == 'CPM':
            role = '할인혜택형'
            role_reason = '랜딩 hero "첫 달 9만원"과 정합. 명확한 혜택으로 클릭 유도해 단가 압축. CPM 자체보다 클릭당 비용으로 회복'
        elif bottleneck_type == 'CTR':
            role = '후기형'
            role_reason = '첫 3초 후킹 약화 가능성. 실 환자 후기·변화 결과 수치로 반응 회복. 동일 광고 그룹에서 신규 ON / 저성과 OFF 교체'
        elif bottleneck_type == 'CVR':
            role = '상담전환형'
            role_reason = '클릭은 들어오지만 5단계 폼·상담 전환 약함. 직접 CTA·필요성 명확한 메시지로 폼 진입 유도. 광고 그룹 단위 예산 증액 보류'
        elif bottleneck_type == 'new':
            role = '신뢰형'
            role_reason = '신규 지점 학습기. 의료기관 신뢰·원장 정보로 안정 학습. 단 랜딩에 의료진 정보가 약하므로 소재에서 보완'
        else:
            role = '유지/확대'
            role_reason = '현재 우수 소재 ON 유지하며 광고 그룹 예산 단계적 확대'

        # 8. confidence_level (데이터 충분도)
        days_active = pt.get('days_active') or 0
        total_conv = conv_actual or 0
        if is_new or days_active < 30:
            confidence = 'limited'
        elif total_conv < 100:
            confidence = 'moderate'
        else:
            confidence = 'high'

        by_branch[branch] = {
            'primary_gap': primary_gap,
            'funnel_status': funnel_status,
            'bottleneck_type': bottleneck_type,
            'priority_score': score,
            'priority_level': priority,
            'expected_impact': expected_impact,
            'guardrail': guardrail,
            'creative_role': {
                'role': role,
                'reason': role_reason,
            },
            'confidence_level': confidence,
        }

    # 그룹별 기대 효과 합계
    group_impact = {'A': [0, 0], 'B': [0, 0], 'C': [0, 0]}
    for branch in VALID_BRANCHES:
        ar = action_rows.get(branch, {}) or {}
        grp = ar.get('group', 'B')
        imp = by_branch[branch].get('expected_impact')
        if imp:
            group_impact[grp][0] += imp['conversion_gain_min'] or 0
            group_impact[grp][1] += imp['conversion_gain_max'] or 0

    return {
        'by_branch': by_branch,
        'group_impact': {
            'A': {'min': group_impact['A'][0], 'max': group_impact['A'][1], 'label': '효율 개선 그룹'},
            'B': {'min': group_impact['B'][0], 'max': group_impact['B'][1], 'label': '예산 확대 그룹'},
            'C': {'min': group_impact['C'][0], 'max': group_impact['C'][1], 'label': '신규 안정화 그룹'},
        },
        'creative_role_library': CREATIVE_ROLE_LIBRARY,
        'note': '갭% 양수=목표 초과달성, 음수=개선 필요. status는 평균/목표 대비 ±10%/±20% 임계값.',
    }
