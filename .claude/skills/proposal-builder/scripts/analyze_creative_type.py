"""소재유형·콘텐츠 특성 분석 - 6월 운영 방안 도출

세 가지 차원 분석:
  1. 소재유형별 전체 성과 (인플방문후기/진료셀프캠/의료진정보 등)
  2. 지점 × 소재유형 매트릭스 - 각 지점에 적합한 소재유형
  3. 소재구분 비교 - 신규 vs 재가공

베이스라인: 정상 운영 월(2~4월) 누적
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES, VALID_AD_TYPES

NORMAL_MONTHS = ['2026-02', '2026-03', '2026-04']
MIN_CONVERSIONS = 5  # 신뢰성 위한 최소 전환수
MIN_COST = 200_000   # 신뢰성 위한 최소 비용


def _kpi(df: pd.DataFrame) -> dict | None:
    if len(df) == 0:
        return None
    cost = float(df['cost'].sum())
    impr = float(df['impressions'].sum())
    clk = float(df['clicks'].sum())
    conv = float(df['conversions'].sum())
    return {
        'cost': int(cost),
        'impressions': int(impr),
        'clicks': int(clk),
        'conversions': int(conv),
        'cpm': int(cost / impr * 1000) if impr > 0 else None,
        'ctr': round(clk / impr * 100, 2) if impr > 0 else None,
        'cvr': round(conv / clk * 100, 2) if clk > 0 else None,
        'cpa': int(cost / conv) if conv > 0 else None,
    }


def _grade_cpa(branch_cpa, overall_cpa):
    """전체 평균 대비 CPA 등급."""
    if branch_cpa is None or overall_cpa is None or overall_cpa == 0:
        return {'grade': 'unknown', 'label': '평가 불가', 'ratio_pct': None}
    ratio = branch_cpa / overall_cpa
    delta_pct = round((ratio - 1) * 100, 1)
    if ratio <= 0.85:
        return {'grade': 'efficient', 'label': '효율 우수', 'ratio_pct': delta_pct}
    if ratio >= 1.15:
        return {'grade': 'inefficient', 'label': '효율 부진', 'ratio_pct': delta_pct}
    return {'grade': 'average', 'label': '평균 수준', 'ratio_pct': delta_pct}


def analyze(parsed_path: str) -> dict:
    df = pd.read_parquet(parsed_path)
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.strftime('%Y-%m')
    df = df[df['parse_status'] == 'OK'].copy()
    df = df[df['지점'].isin(VALID_BRANCHES)]
    df = df[df['소재유형'].isin(VALID_AD_TYPES)]
    df_normal = df[df['month'].isin(NORMAL_MONTHS)]

    overall = _kpi(df_normal)
    overall_cpa = overall['cpa'] if overall else None
    total_conv = overall['conversions'] if overall else 0

    # 1. 소재유형별 전체 성과
    by_type = {}
    for at in VALID_AD_TYPES:
        sub = df_normal[df_normal['소재유형'] == at]
        k = _kpi(sub)
        if k is None or k['cost'] < MIN_COST:
            continue
        share = round(k['conversions'] / total_conv * 100, 1) if total_conv > 0 else 0
        grade = _grade_cpa(k['cpa'], overall_cpa)
        by_type[at] = {
            **k,
            'conv_share_pct': share,
            'cpa_grade': grade,
            'ad_count': int(sub['ad_id'].nunique()),
        }
    # 전환수 큰 순 정렬
    by_type = dict(sorted(by_type.items(), key=lambda x: -x[1]['conversions']))

    # 2. 지점 × 소재유형 매트릭스
    matrix = {}
    for b in VALID_BRANCHES:
        bdf = df_normal[df_normal['지점'] == b]
        if len(bdf) == 0:
            matrix[b] = None
            continue
        types = {}
        for at in VALID_AD_TYPES:
            sub = bdf[bdf['소재유형'] == at]
            k = _kpi(sub)
            if k is None or k['conversions'] == 0:
                types[at] = None
                continue
            types[at] = k
        # 해당 지점에서 가장 효율적인 소재유형 (전환 ≥ 3건 + 가장 낮은 CPA)
        eligible = [(at, k) for at, k in types.items() if k and k['conversions'] >= 3 and k['cpa']]
        best_type = min(eligible, key=lambda x: x[1]['cpa']) if eligible else None
        worst_type = max(eligible, key=lambda x: x[1]['cpa']) if eligible else None
        matrix[b] = {
            'by_type': types,
            'best_type': {'name': best_type[0], 'cpa': best_type[1]['cpa'], 'conversions': best_type[1]['conversions']} if best_type else None,
            'worst_type': {'name': worst_type[0], 'cpa': worst_type[1]['cpa'], 'conversions': worst_type[1]['conversions']} if (worst_type and worst_type != best_type) else None,
        }

    # 3. 신규(신) vs 재가공(재) 비교
    kind_compare = {}
    for kind_label in ('신규', '재가공'):
        sub = df_normal[df_normal['소재구분'] == kind_label]
        k = _kpi(sub)
        if k:
            k['ad_count'] = int(sub['ad_id'].nunique())
            k['conv_share_pct'] = round(k['conversions'] / total_conv * 100, 1) if total_conv > 0 else 0
            k['cpa_grade'] = _grade_cpa(k['cpa'], overall_cpa)
            kind_compare[kind_label] = k

    # 4. 핵심 인사이트 자동 추출
    insights = []
    if by_type:
        # 최고 효율 소재유형
        eff_types = [(at, d) for at, d in by_type.items() if d['cpa_grade']['grade'] == 'efficient']
        if eff_types:
            top = eff_types[0]
            insights.append({
                'type': 'efficient_creative',
                'label': '최고 효율 소재유형',
                'detail': f"{top[0]} (전환 {top[1]['conversions']}건, CPA {top[1]['cpa']:,}원, 평균 {top[1]['cpa_grade']['ratio_pct']}%)",
                'action': f'전 지점에서 {top[0]} 소재 확대 검토',
            })
        # 최악 효율 소재유형
        ineff_types = [(at, d) for at, d in by_type.items() if d['cpa_grade']['grade'] == 'inefficient']
        if ineff_types:
            worst = ineff_types[0]
            insights.append({
                'type': 'inefficient_creative',
                'label': '효율 부진 소재유형',
                'detail': f"{worst[0]} (CPA {worst[1]['cpa']:,}원, 평균 {worst[1]['cpa_grade']['ratio_pct']}%)",
                'action': f'{worst[0]} 소재 비중 축소 또는 크리에이티브 개편 검토',
            })
    # 신규 vs 재가공
    if '신규' in kind_compare and '재가공' in kind_compare:
        nv, rv = kind_compare['신규'], kind_compare['재가공']
        if nv['cpa'] and rv['cpa']:
            diff_pct = round((nv['cpa'] - rv['cpa']) / rv['cpa'] * 100, 1)
            better = '신규' if nv['cpa'] < rv['cpa'] else '재가공'
            insights.append({
                'type': 'kind_compare',
                'label': f'{better} 소재가 더 효율적',
                'detail': f"신규 CPA {nv['cpa']:,}원 vs 재가공 CPA {rv['cpa']:,}원 (차이 {abs(diff_pct)}%)",
                'action': f'{better} 소재 제작·집행 비중 확대 검토',
            })

    return {
        'baseline_period': NORMAL_MONTHS,
        'overall': overall,
        'by_type': by_type,
        'branch_type_matrix': matrix,
        'kind_compare': kind_compare,
        'insights': insights,
        'criteria': {
            'min_conversions': MIN_CONVERSIONS,
            'min_cost': MIN_COST,
            'cpa_grade_threshold': '전체 평균 CPA ±15%',
        },
    }


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260518/parsed.parquet'
    r = analyze(path)
    print(f"[전체 평균 - 2~4월 누적]")
    print(f"  전환 {r['overall']['conversions']:,}건 / CPA {r['overall']['cpa']:,}원\n")

    print(f"[1. 소재유형별 성과]")
    for at, d in r['by_type'].items():
        ratio = d['cpa_grade']['ratio_pct']
        print(f"  {at:<10}: 전환 {d['conversions']:>4}건 ({d['conv_share_pct']:>4}%) / CPA {d['cpa']:>8,}원 / CVR {d['cvr']}% / 광고 {d['ad_count']}개 / {d['cpa_grade']['label']} ({ratio:+.0f}%)")

    print(f"\n[2. 지점별 최강 소재유형]")
    for b in VALID_BRANCHES:
        m = r['branch_type_matrix'].get(b)
        if m is None or not m.get('best_type'):
            print(f"  {b:<5}: 데이터 부족")
            continue
        bt = m['best_type']
        wt = m.get('worst_type')
        wt_str = (' / 부진: ' + wt['name'] + ' (CPA ' + format(wt['cpa'], ',') + ')') if wt else ''
        print(f"  {b:<5}: 최강 {bt['name']} (전환 {bt['conversions']}건, CPA {bt['cpa']:,}){wt_str}")

    print(f"\n[3. 신규 vs 재가공]")
    for kind, d in r['kind_compare'].items():
        print(f"  {kind}: 전환 {d['conversions']:,}건 ({d['conv_share_pct']}%) / CPA {d['cpa']:,}원 / 광고 {d['ad_count']}개 / {d['cpa_grade']['label']}")

    print(f"\n[4. 자동 인사이트]")
    for ins in r['insights']:
        print(f"  • [{ins['label']}] {ins['detail']}")
        print(f"    → {ins['action']}")
