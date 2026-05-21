"""지점별 액션 테이블 — 목표값 의존 없이 전 기간 운영 결과 기반

매체 운영자가 6월에 즉시 실행할 수 있는 형태로 출력:
  지점 | 전 기간 운영 요약 | 자동 진단 | 확인 지표 | 운영 액션 | 검증 KPI

정렬: 약점 심각도 합산 큰 순 (개선 우선) → 전환 비중 큰 순 (보조)
사전 정의 목표값 없이 전 기간 누적 데이터와 지점간 비교만 사용.
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES

sys.path.insert(0, str(Path(__file__).parent))
from analyze_root_cause import analyze as analyze_root
from analyze_conversion_perspective import analyze as analyze_conv


def _find_latest_creative_tier(parsed_path: str) -> Path | None:
    """parsed_path와 같은 디렉토리에 creative_tier.parquet이 없으면
    output/data/ 하위에서 가장 최신 디렉토리의 것을 찾는다."""
    same_dir = Path(parsed_path).parent / 'creative_tier.parquet'
    if same_dir.exists():
        return same_dir
    data_root = Path(parsed_path).parent.parent
    if not data_root.exists():
        return None
    candidates = sorted(
        [d for d in data_root.iterdir() if d.is_dir() and (d / 'creative_tier.parquet').exists()],
        key=lambda d: d.name,
        reverse=True,
    )
    return (candidates[0] / 'creative_tier.parquet') if candidates else None


def _load_creative_tier(parsed_path: str, top_n: int = 2) -> dict:
    """creative_tier.parquet에서 지점별 TIER1/TIER4 소재명 추출.

    creative_tier.parquet은 소재 단위 집계 — 지점 컬럼이 없고 `집행지점목록`(list)에 분포.
    한 소재가 여러 지점에 ON되어 있을 수 있어, 각 지점에 대해 그 지점이 list에 포함된 소재만 필터.

    Returns: {branch: {'tier1': [{name, cpa, cvr}], 'tier4': [...]}}
    """
    tier_path = _find_latest_creative_tier(parsed_path)
    if tier_path is None:
        return {}
    try:
        df = pd.read_parquet(tier_path)
    except Exception:
        return {}
    if df.empty:
        return {}

    name_col = '매칭키' if '매칭키' in df.columns else ('creative_name' if 'creative_name' in df.columns else None)
    tier_col = 'TIER' if 'TIER' in df.columns else ('tier' if 'tier' in df.columns else None)
    cpa_col = 'CPA' if 'CPA' in df.columns else ('cpa' if 'cpa' in df.columns else None)
    cvr_col = 'CVR' if 'CVR' in df.columns else ('cvr' if 'cvr' in df.columns else None)
    branches_col = '집행지점목록' if '집행지점목록' in df.columns else None
    if not name_col or not tier_col or not branches_col:
        return {}

    result = {}
    for branch in VALID_BRANCHES:
        def has_branch(lst, b=branch):
            try:
                return b in list(lst) if lst is not None else False
            except Exception:
                return False
        bdf = df[df[branches_col].apply(has_branch)].copy()
        if bdf.empty:
            continue
        tier1 = bdf[bdf[tier_col].astype(str).str.upper() == 'TIER1']
        if cpa_col and cpa_col in tier1.columns:
            tier1 = tier1.sort_values(by=cpa_col, na_position='last')
        tier1_items = []
        for _, r in tier1.head(top_n).iterrows():
            cpa_v = r.get(cpa_col) if cpa_col else None
            cvr_v = r.get(cvr_col) if cvr_col else None
            tier1_items.append({
                'name': str(r[name_col]),
                'cpa': None if cpa_v is None or pd.isna(cpa_v) else int(cpa_v),
                'cvr': None if cvr_v is None or pd.isna(cvr_v) else float(cvr_v),
            })
        tier4 = bdf[bdf[tier_col].astype(str).str.upper() == 'TIER4']
        if cpa_col and cpa_col in tier4.columns:
            tier4 = tier4.sort_values(by=cpa_col, ascending=False, na_position='last')
        tier4_items = []
        for _, r in tier4.head(top_n).iterrows():
            cpa_v = r.get(cpa_col) if cpa_col else None
            cvr_v = r.get(cvr_col) if cvr_col else None
            tier4_items.append({
                'name': str(r[name_col]),
                'cpa': None if cpa_v is None or pd.isna(cpa_v) else int(cpa_v),
                'cvr': None if cvr_v is None or pd.isna(cvr_v) else float(cvr_v),
            })
        if tier1_items or tier4_items:
            result[branch] = {'tier1': tier1_items, 'tier4': tier4_items}
    return result


# 지점간 비교 약점 metric → 운영 액션 매핑
# 운영 단위 원칙:
#   · 예산은 캠페인/광고 그룹(지점) 단위로만 조정 가능
#   · 소재(광고)는 ON/OFF만 가능 — 소재별 예산 조정 불가
#   · A/B 테스트는 광고 그룹 복제로 진행
PEER_WEAKNESS_ACTIONS = {
    'cpm': {
        'headline': '지역 풀 과밀 완화 + 시간대·입찰 점검',
        'action': 'CPM 병목은 타겟 풀이 좁거나 특정 시간대 입찰 경쟁이 높은 신호로 해석. (1) 지점 인근 생활권 시·군까지 지역 범위 확장 검토, (2) 시간대·요일 분산으로 피크 경쟁 회피, (3) 입찰 전략 점검(최대 전환 vs 비용 한도), (4) 저CPM·전환 유지 소재 비중 확대',
        'verify_kpi': 'CPM 전 지점 평균 수준 회귀 (지역 캠페인 구조상 개선 폭은 제한적, CTR/CVR로 보완 가능)',
    },
    'ctr': {
        'headline': '베스트 소재 도입 + 신규 후크 테스트',
        'action': '소재 후킹·썸네일 약점 - 우수 지점의 베스트 소재 광고 단위 추가, 저성과 소재 광고 단위 OFF. 신규 후크 메시지·인플루언서 콘텐츠 ON 교체 (예산은 광고 그룹 단위라 별도 조정 불필요)',
        'verify_kpi': 'CTR 전 지점 평균 수준 회귀, 신규 소재 CTR ≥ 베스트 평균',
    },
    'cvr': {
        'headline': '소재 ↔ 랜딩 hero 정합성 → CVR 회복 후 광고 그룹 예산 증액',
        'action': (
            '[1단계 소재] CVR 우수 소재 ON 유지·확대, 저CVR 소재 OFF (광고 단위 ON/OFF만 가능). '
            '[2단계 랜딩] 소재 후킹 메시지와 랜딩 hero("첫 달 9만원") 톤 정합성, 5단계 폼(부위→기대효과→연령→연락처→동의) 이탈률 점검. 랜딩은 전 지점 동일 포맷이므로 지점별 차이는 없음. '
            '[3단계 예산 가드] CPA 비싼 지점은 광고 그룹(지점) 예산 증액 보류, CVR 개선 선행. A/B는 광고 그룹 복제로 진행'
        ),
        'verify_kpi': 'CVR 전 지점 평균 수준 회귀, CPA 동반 개선',
    },
    'cpa': {
        'headline': '광고 그룹 단위 예산 보류 + 우수 소재 ON 집중',
        'action': (
            '광고 그룹(지점) 단위 단순 예산 확대 시 비효율 확대 위험. 효율 우수 소재 광고 단위 유지·확대, 저성과 소재 OFF로 집중. CVR/CTR 개선과 동시 진행'
        ),
        'verify_kpi': 'CPA 전 지점 평균 수준 회귀',
    },
    'lpv_rate': {
        'headline': '랜딩 로딩 속도·UX 점검 (전 지점 공통)',
        'action': '랜딩 페이지 로딩 속도(3초 이내), 모바일 UX, 소재 후킹 메시지와 랜딩 hero 정합성 점검. 전 지점 동일 포맷이므로 지점별 차이는 없음',
        'verify_kpi': 'LPV/클릭 전 지점 평균 수준 회귀',
    },
}

# 그룹별 핵심 액션 fallback (약점 없거나 신규 지점용)
GROUP_FALLBACK_HEADLINE = {
    'B': '현 운영 유지 + 우수 소재 확대로 전환 볼륨 추가 확보',
    'C': '5월 운영 패턴 안정화 모니터링 → 다음 달 정상 진단',
}

# 추세 가드레일 메시지
TREND_ACTIONS = {
    'cpm_consistent_up': '※ CPM 추세 일관 상승 - 매체 경쟁 강도 증가 시그널. 신규 오디언스 확보·시간대 분산 검토',
    'cvr_consistent_down': '※ CVR 추세 일관 하락 - 소재 피로도·소재-랜딩 메시지 불일치 의심',
    'ctr_consistent_down': '※ CTR 추세 일관 하락 - 소재 피로도, 신규 후크 테스트 시급',
}


def _format_period_summary(period: dict | None, share: float | None, grade: dict) -> str:
    if period is None:
        return '신규 지점 - 정상 운영 누적 없음'
    parts = [f"전환 {period['conversions']:,}건 ({share}%)"]
    parts.append(f"CPA {period['cpa']:,}원")
    parts.append(f"일평균 {period['daily_conversions']}건")
    grade_label = grade.get('label', '')
    if grade_label and grade_label != '평가 불가':
        parts.append(f"[{grade_label}]")
    return ' / '.join(parts)


def _trend_warnings(trends: dict) -> list[str]:
    warnings = []
    if trends.get('cpm', {}).get('class') == 'consistent_up':
        warnings.append(TREND_ACTIONS['cpm_consistent_up'])
    if trends.get('cvr', {}).get('class') == 'consistent_down':
        warnings.append(TREND_ACTIONS['cvr_consistent_down'])
    if trends.get('ctr', {}).get('class') == 'consistent_down':
        warnings.append(TREND_ACTIONS['ctr_consistent_down'])
    return warnings


def _weakness_severity_sum(weaknesses: list) -> float:
    """약점 심각도 합 (정렬용)."""
    return sum(abs(w.get('severity', 0)) for w in weaknesses)


def analyze(parsed_path: str) -> dict:
    rc = analyze_root(parsed_path)
    cp = analyze_conv(parsed_path)
    creative_tier_by_branch = _load_creative_tier(parsed_path)

    rows = []
    for branch in VALID_BRANCHES:
        bd = rc['by_branch'][branch]
        cd = cp['by_branch'][branch]
        is_new = cd.get('is_new_branch', False)

        # 신규 지점
        if not bd['is_diagnosable']:
            partial = cd.get('partial_may')
            partial_str = ''
            if partial:
                partial_str = f"5월 부분 운영 - 전환 {partial['conversions']}건 / CPA {partial['cpa']:,}원 / 일평균 {partial['daily_conversions']}건"
            rows.append({
                'branch': branch,
                'is_new_branch': is_new,
                'is_partial_source': True,
                'group': 'C',
                'headline': GROUP_FALLBACK_HEADLINE.get('C', ''),
                'period_summary': '신규 지점 - 정상 운영 누적 없음',
                'partial_may_summary': partial_str,
                'sort_priority': -1,
                'diagnoses': [],
                'diagnosis_evidence': [],
                'verify_metrics': ['CTR', 'CVR', 'CPA', 'LPV/클릭'],
                'actions': [
                    '5월 운영 패턴 안정성 1개월 모니터링 후 다음 달 정상 진단',
                    '유사 광역권 지점(예: 영남 - 대구·창원) 우수 소재 크로스 도입 테스트',
                    '신규 지점 학습 안정화 위해 광고세트 통합 운영 권장'
                ],
                'verify_kpi': '정상 운영 패턴 형성 후 다음 달 진단',
                'trend_warnings': [],
                'conv_share_pct': None,
                'cpa_grade': cd.get('cpa_grade'),
                'creative_tier_inline': creative_tier_by_branch.get(branch, {'tier1': [], 'tier4': []}),
            })
            continue

        # 약점 진단 (상위 2개)
        weaknesses = bd.get('peer_weaknesses', [])[:2]
        diag_labels = [w['label'] for w in weaknesses]
        diag_evidence = [w['evidence'] for w in weaknesses]
        severity_sum = _weakness_severity_sum(bd.get('peer_weaknesses', []))
        is_partial = bd.get('is_partial_source', False)

        actions = []
        verify_kpis = []
        verify_metrics = set()
        headlines = []
        for w in weaknesses:
            mapping = PEER_WEAKNESS_ACTIONS.get(w['metric'])
            if mapping:
                actions.append(mapping['action'])
                verify_kpis.append(mapping['verify_kpi'])
                if mapping.get('headline'):
                    headlines.append(mapping['headline'])
            verify_metrics.add(w['metric'].upper())

        trend_warnings = _trend_warnings(bd.get('trends', {}))

        if not actions:
            actions = ['전 지점 평균 대비 특이 약점 없음 - 현 운영 패턴 유지, 6월에는 우수 소재 확대·신규 콘텐츠 테스트로 전환 볼륨 확대 시도']
            verify_kpis = ['전 기간 KPI 유지']
            verify_metrics = {'전환수', 'CPA'}

        # 신규(5월 부분 데이터 기반) 지점은 안정화 안내 추가
        if is_partial:
            actions.insert(0, '※ 신규 지점 (5월 부분 데이터 기반 진단) - 6월 정상 1개월 운영 후 패턴 재평가. 진단 결과는 참고용으로 활용')
            verify_kpis.insert(0, '1개월 안정화 후 재진단')

        # 그룹 분류: A 개선 우선 / B 예산 확대 후보 / C 신규 모니터링
        if is_partial or is_new:
            group = 'C'
        elif weaknesses:
            group = 'A'
        else:
            group = 'B'

        # 핵심 액션 한 줄 (그룹별)
        if group == 'A' and headlines:
            headline = ' / '.join(headlines[:2])
        else:
            headline = GROUP_FALLBACK_HEADLINE.get(group, '')

        rows.append({
            'branch': branch,
            'is_new_branch': is_new or is_partial,
            'is_partial_source': is_partial,
            'group': group,
            'headline': headline,
            'period_summary': _format_period_summary(cd['period_total'], cd['conv_share_pct'], cd['cpa_grade']),
            'partial_may_summary': '',
            'sort_priority': severity_sum,
            'diagnoses': diag_labels,
            'diagnosis_evidence': diag_evidence,
            'verify_metrics': sorted(verify_metrics),
            'actions': actions,
            'verify_kpi': ' / '.join(verify_kpis) if verify_kpis else '베이스라인 유지',
            'trend_warnings': trend_warnings,
            'conv_share_pct': cd['conv_share_pct'],
            'cpa_grade': cd['cpa_grade'],
            'creative_tier_inline': creative_tier_by_branch.get(branch, {'tier1': [], 'tier4': []}),
        })

    # 정렬: 그룹 (A→B→C) → 약점 심각도 합 큰 순 → 전환 비중 큰 순
    GROUP_ORDER = {'A': 0, 'B': 1, 'C': 2}
    rows.sort(key=lambda r: (
        GROUP_ORDER.get(r.get('group', 'C'), 3),
        -(r.get('sort_priority') or 0),
        -(r.get('conv_share_pct') or 0),
    ))

    # 그룹별 지점 목록 (summary strip 용)
    groups_summary = {'A': [], 'B': [], 'C': []}
    for r in rows:
        groups_summary[r.get('group', 'C')].append(r['branch'])

    return {
        'baseline_period': rc['normal_months'],
        'rows': rows,
        'groups_summary': groups_summary,
        'group_definitions': {
            'A': {'label': 'A. 효율 개선 우선', 'criterion': '약점 심각도 높음 - CVR/CPA/CTR 등에서 전 지점 평균 대비 부진'},
            'B': {'label': 'B. 예산 확대 후보', 'criterion': '성과 효율 양호 - 특이 약점 없음, 확대 시 전환 추가 확보 가능'},
            'C': {'label': 'C. 신규 모니터링', 'criterion': '5월 신규 운영 시작 - 정상 운영 누적 데이터 부족, 안정화 후 재진단'},
        },
        'sort_rationale': '그룹(A→B→C) → 약점 심각도 → 전환 비중 순으로 정렬. 분류 기준: 약점 심각도·전환 기여도·CPA 안정성·데이터 충분성.',
    }


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260518/parsed.parquet'
    r = analyze(path)
    print(f"베이스라인: 전 기간 {r['baseline_period']} 누적\n")
    for row in r['rows']:
        new = ' [신규]' if row['is_new_branch'] else ''
        diag = ', '.join(row['diagnoses']) if row['diagnoses'] else '특이 약점 없음'
        print(f"[{row['branch']}{new}] {row['period_summary']}")
        print(f"  진단: {diag}")
        for tw in row['trend_warnings']:
            print(f"  {tw}")
        for a in row['actions'][:1]:
            print(f"  액션: {a[:120]}")
        print()
