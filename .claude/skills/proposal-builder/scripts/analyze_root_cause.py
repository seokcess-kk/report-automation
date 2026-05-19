"""지점별 운영 진단 - 전 기간 누적 데이터 기반

설계 원칙:
  · 누적 KPI 비교 (peer_avg, period_total)는 전 기간(2~5월) 사용
  · 5월은 부분 데이터(15일까지)지만 비율 지표 영향 제한적
  · 월간 추세 분석은 NORMAL_MONTHS(2~4월)만 사용 (5월 부분 데이터로 추세 왜곡 방지)

진단 차원 2가지:
  (A) 지점간 비교: 각 지점의 KPI vs 전 지점 평균
      - 어떤 지점이 어떤 퍼널에서 평균 대비 약한가
      - "수원 CVR이 전 지점 평균 대비 -32% 낮음" 식

  (B) 전 기간 추세 안정성: 2월 → 4월 변화 패턴 (NORMAL_MONTHS만)
      - 일관 개선 / 일관 악화 / 불안정 분류

진단 결과는 build_action_table.py 에서 운영 액션으로 매핑됨.
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES

# 추세/베스트월 비교 전용 (5월 부분 데이터 제외)
NORMAL_MONTHS = ['2026-02', '2026-03', '2026-04']

# 지점간 비교 임계값 (전 지점 평균 대비)
PEER_THRESHOLDS = {
    'cpm_weak': 1.15,    # 평균 대비 +15% 이상 비쌈 → CPM 약점
    'ctr_weak': 0.85,    # 평균 대비 -15% 이하 낮음 → CTR 약점
    'cvr_weak': 0.85,    # 평균 대비 -15% 이하 낮음 → CVR 약점
    'cpa_weak': 1.20,    # 평균 대비 +20% 이상 비쌈 → CPA 약점
    'lpv_weak': 0.85,    # 평균 대비 -15% 이하 낮음 → 랜딩 도달 약점
}

# 추세 안정성 판정 임계값 (월간 변화율)
TREND_THRESHOLDS = {
    'consistent_change': 0.10,  # 월간 +-10% 이상 연속 변화
    'volatile_swing': 0.25,     # 월간 +-25% 이상 단일 변동
}


def _kpi_for_branch_month(df: pd.DataFrame, branch: str | None, month: str | None) -> dict | None:
    sub = df
    if branch is not None:
        sub = sub[sub['지점'] == branch]
    if month is not None:
        sub = sub[sub['month'] == month]
    if len(sub) == 0:
        return None
    cost = float(sub['cost'].sum())
    impr = float(sub['impressions'].sum())
    clk = float(sub['clicks'].sum())
    conv = float(sub['conversions'].sum())
    lpv = float(sub['landing_views'].sum())
    return {
        'cost': cost, 'impressions': impr, 'clicks': clk, 'conversions': conv,
        'landing_views': lpv,
        'cpm': cost / impr * 1000 if impr > 0 else None,
        'ctr': clk / impr * 100 if impr > 0 else None,
        'cvr': conv / clk * 100 if clk > 0 else None,
        'cpa': cost / conv if conv > 0 else None,
        'lpv_rate': lpv / clk * 100 if clk > 0 else None,
    }


def _trend_classify(values: list[float | None]) -> str:
    """월별 시계열 안정성 분류.
    'consistent_up'  : 일관 상승 (2~4월 모두 단조 증가)
    'consistent_down': 일관 하락
    'volatile'       : 큰 변동
    'stable'         : 변화 작음
    """
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return 'insufficient'
    # 월간 변화율 시퀀스
    changes = []
    for i in range(1, len(vals)):
        if vals[i-1] == 0:
            continue
        changes.append((vals[i] - vals[i-1]) / vals[i-1])
    if not changes:
        return 'stable'
    th_c = TREND_THRESHOLDS['consistent_change']
    th_v = TREND_THRESHOLDS['volatile_swing']
    if all(c >= th_c for c in changes):
        return 'consistent_up'
    if all(c <= -th_c for c in changes):
        return 'consistent_down'
    if any(abs(c) >= th_v for c in changes):
        return 'volatile'
    return 'stable'


TREND_LABEL = {
    'consistent_up': '일관 상승',
    'consistent_down': '일관 하락',
    'volatile': '불안정 (큰 변동)',
    'stable': '안정',
    'insufficient': '데이터 부족',
}


def _diagnose_peer_weakness(branch_kpi: dict, peer_avg: dict) -> list[dict]:
    """전 지점 평균 대비 지점 약점 진단."""
    findings = []

    def _check(metric: str, direction: str, label: str, action_hint: str):
        bv = branch_kpi.get(metric)
        pv = peer_avg.get(metric)
        if bv is None or pv is None or pv == 0:
            return
        ratio = bv / pv
        if direction == 'low_is_weak':
            # 낮을수록 약점 (CTR/CVR/LPV)
            if ratio <= PEER_THRESHOLDS[f'{metric}_weak'] if f'{metric}_weak' in PEER_THRESHOLDS else False:
                gap_pct = round((ratio - 1) * 100, 1)
                findings.append({
                    'metric': metric,
                    'direction': 'low_is_weak',
                    'label': label,
                    'evidence': f'{metric.upper()} {bv:.2f} (전 지점 평균 {pv:.2f} 대비 {gap_pct}%)',
                    'severity': abs(gap_pct),
                    'action_hint': action_hint,
                })
        else:
            # 높을수록 약점 (CPM/CPA)
            if ratio >= PEER_THRESHOLDS[f'{metric}_weak'] if f'{metric}_weak' in PEER_THRESHOLDS else False:
                gap_pct = round((ratio - 1) * 100, 1)
                findings.append({
                    'metric': metric,
                    'direction': 'high_is_weak',
                    'label': label,
                    'evidence': f'{metric.upper()} {int(bv):,} (전 지점 평균 {int(pv):,} 대비 +{gap_pct}%)',
                    'severity': gap_pct,
                    'action_hint': action_hint,
                })

    _check('cpm', 'high_is_weak', '노출 단가 비싼 편', '경쟁 강한 타겟 풀 의심. 오디언스 폭/시간대 재조정 검토')
    _check('ctr', 'low_is_weak', '클릭률 저조', '소재 후킹·썸네일 약함. 우수 소재 도입 + 신규 후크 테스트')
    _check('cvr', 'low_is_weak', '전환율 저조', '소재-랜딩 메시지 일치도·CTA·폼 흐름 점검. 내부 상담/예약 이슈는 병원 확인 요청으로 분리')
    _check('lpv_rate', 'low_is_weak', '랜딩 도달률 저조', '랜딩 로딩 속도·리다이렉트·모바일 UX 점검')
    _check('cpa', 'high_is_weak', '전환 단가 비싼 편', '예산 증액 전 CVR 개선 선행 필수. 효율 우수 소재로 예산 재배치')

    # 강도 순 정렬
    findings.sort(key=lambda d: d['severity'], reverse=True)
    return findings


def _diagnose_trend(monthly_kpis: dict) -> dict:
    """전 기간 추세 안정성 분류."""
    months_sorted = sorted(monthly_kpis.keys())
    series = {
        'cpm': [monthly_kpis[m]['cpm'] if monthly_kpis[m] else None for m in months_sorted],
        'ctr': [monthly_kpis[m]['ctr'] if monthly_kpis[m] else None for m in months_sorted],
        'cvr': [monthly_kpis[m]['cvr'] if monthly_kpis[m] else None for m in months_sorted],
        'cpa': [monthly_kpis[m]['cpa'] if monthly_kpis[m] else None for m in months_sorted],
    }
    trends = {}
    for m, vals in series.items():
        cls = _trend_classify(vals)
        first = next((v for v in vals if v is not None), None)
        last = next((v for v in reversed(vals) if v is not None), None)
        trends[m] = {
            'class': cls,
            'label': TREND_LABEL[cls],
            'first': first,
            'last': last,
            'series': vals,
        }
    return trends


def analyze(parsed_path: str) -> dict:
    df = pd.read_parquet(parsed_path)
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.strftime('%Y-%m')
    df = df[df['지점'].isin(VALID_BRANCHES)].copy()
    # 추세 분석 전용 (5월 부분 데이터 제외)
    df_normal = df[df['month'].isin(NORMAL_MONTHS)]

    # 전 지점 평균 KPI (전 기간 2~5월 누적 기준)
    peer_total = _kpi_for_branch_month(df, None, None)

    # 지점별 분석
    by_branch = {}
    for branch in VALID_BRANCHES:
        # 누적값은 전 기간 (2~5월)
        branch_total = _kpi_for_branch_month(df, branch, None)
        # 정상월 데이터 보유 여부 (추세 분석 가능 여부 판단)
        has_normal = any(_kpi_for_branch_month(df_normal, branch, m) is not None for m in NORMAL_MONTHS)
        # 신규 지점 = 정상월 데이터 없고 5월만 있음
        is_partial_source = (not has_normal) and branch_total is not None

        if branch_total is None:
            by_branch[branch] = {
                'is_diagnosable': False,
                'is_partial_source': False,
                'reason': '전 기간 데이터 없음',
                'monthly_history': {},
                'peer_weaknesses': [],
                'trends': {},
                'period_total': None,
            }
            continue

        # 월별 KPI (정상월만 - 추세 비교용)
        monthly = {m: _kpi_for_branch_month(df_normal, branch, m) for m in NORMAL_MONTHS}

        # (A) 지점간 비교 - 전 기간 누적 vs 전 지점 평균
        peer_weaknesses = _diagnose_peer_weakness(branch_total, peer_total)

        # (B) 추세 안정성 - 정상월(3개월) 기준. 5월 부분 데이터는 추세 왜곡 방지를 위해 제외
        trends = _diagnose_trend(monthly) if has_normal else {}

        by_branch[branch] = {
            'is_diagnosable': True,
            'is_partial_source': is_partial_source,
            'period_total': branch_total,
            'monthly_history': monthly,
            'peer_weaknesses': peer_weaknesses,
            'trends': trends,
        }

    return {
        'branches': VALID_BRANCHES,
        'normal_months': NORMAL_MONTHS,
        'peer_avg': peer_total,
        'by_branch': by_branch,
        'methodology': {
            'comparison_basis': '전 지점 평균 (전 기간 누적)',
            'trend_basis': '2~4월 정상 운영 월간 변화',
            'note': '5월은 운영 중단으로 시점 비교에서 제외',
        },
    }


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260518/parsed.parquet'
    r = analyze(path)
    p = r['peer_avg']
    print(f"전 지점 평균 (전 기간 2~4월 누적): CPM={int(p['cpm']):,} CTR={p['ctr']:.2f}% CVR={p['cvr']:.2f}% CPA={int(p['cpa']):,}\n")
    for b in r['branches']:
        bd = r['by_branch'][b]
        if not bd['is_diagnosable']:
            print(f"[{b}] {bd['reason']}")
            continue
        pt = bd['period_total']
        print(f"[{b}] 전 기간 누적: CPM={int(pt['cpm']):,} CTR={pt['ctr']:.2f}% CVR={pt['cvr']:.2f}% CPA={int(pt['cpa']):,}")
        if not bd['peer_weaknesses']:
            print(f"  → 전 지점 평균 대비 특이 약점 없음")
        for f in bd['peer_weaknesses']:
            print(f"  ▶ [{f['label']}] {f['evidence']}")
            print(f"     액션 힌트: {f['action_hint']}")
        # 추세
        for m, t in bd['trends'].items():
            if t['class'] in ('consistent_up', 'consistent_down', 'volatile'):
                print(f"  ▶ {m.upper()} 추세: {t['label']} ({t['first']:.2f} → {t['last']:.2f})")
        print()
