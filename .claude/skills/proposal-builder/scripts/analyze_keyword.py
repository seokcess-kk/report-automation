"""키워드·콘텐츠 메시지 분석 - 6월 소재 제작 방향 도출

광고 소재명에서 키워드(메시지 요소)를 매칭하여 어떤 메시지·소구점이
실제 전환에 더 효과적이었는지 분석.

키워드 8개 카테고리 (수동 정의):
  1. 약·주사 관련: 비만주사·주사형·비만치료제
  2. 식이·식욕 관련: 밥빵면·맘껏·먹으면서·식욕억제·급찐·끊고
  3. 요요·실패 후킹: 요요·실패·끝·마지막
  4. 인플루언서 캐스팅: (부산잇츠)·(창원언니쓰)·(대읽남)·(쭈링)·(박고경) 등 괄호 패턴
  5. 연령대 타겟팅: 40대·50대·20대·30대
  6. 결과 수치 강조: -32kg·-20kg·체지방·뱃살·하체
  7. 의료/한의원 권위: 한의원·원장·한의사·10년·의료진
  8. 직장인·일상 톤: 직장인·주부·부부·여성·뱃살·고생

각 광고는 여러 키워드에 동시 매칭될 수 있음 (의도된 동작).
베이스라인: 2~4월 정상 운영 누적.
"""
import sys
import re
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES

NORMAL_MONTHS = ['2026-02', '2026-03', '2026-04']

# 키워드 사전 (카테고리 → 매칭 패턴 리스트)
KEYWORD_DICT = {
    '약·주사': ['비만주사', '주사형', '비만치료제', '주사'],
    '식이·식욕': ['밥빵면', '밥,빵,면', '맘껏', '먹으면서', '식욕억제', '식욕', '급찐', '끊고', '음식', '명절'],
    '요요·실패': ['요요', '실패', '마지막', '고생', '지긋지긋', '끝났', '끝낸', '못끊', '끝내', '끝난'],
    '인플 캐스팅': [r'\([가-힣a-zA-Z\.,]+\)'],  # 괄호 패턴 (정규식)
    '연령대 타겟': ['20대', '30대', '40대', '50대', '60대'],
    '결과 수치': ['-32kg', '-20kg', '32kg', '20kg', '체지방', '뱃살', '하체', '통짜', '볼록', '늘어나'],
    '의료·한의원': ['한의원', '원장', '한의사', '10년', '의료진', '진료'],
    '직장인·일상': ['직장인', '주부', '부부', '여성', '남성', '한달후기', '인천', '수원', '대구', '창원', '부산'],
}

# 정규식 vs substring 자동 판정
def _matches(name: str, pattern: str) -> bool:
    if pattern.startswith(r'\('):
        # 정규식
        return bool(re.search(pattern, name))
    return pattern in name


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


def _grade(branch_cpa, overall_cpa):
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
    df = df[df['month'].isin(NORMAL_MONTHS)]
    df = df.dropna(subset=['소재명'])

    overall = _kpi(df)
    overall_cpa = overall['cpa'] if overall else None
    total_conv = overall['conversions'] if overall else 0

    # 광고별 (ad_id) 키워드 라벨링 후 카테고리별 KPI 집계
    by_keyword = {}
    for category, patterns in KEYWORD_DICT.items():
        # 해당 카테고리에 매칭되는 ad_id 추출
        # 한 ad_id는 한 카테고리 안에서 어느 한 패턴이라도 매칭되면 해당 카테고리에 속함
        ad_names = df[['ad_id', '소재명']].drop_duplicates()
        matched_ids = set()
        for _, row in ad_names.iterrows():
            name = str(row['소재명'])
            if any(_matches(name, p) for p in patterns):
                matched_ids.add(row['ad_id'])
        sub = df[df['ad_id'].isin(matched_ids)]
        k = _kpi(sub)
        if k is None or k['conversions'] < 5:
            # 표본 부족
            by_keyword[category] = None
            continue
        share = round(k['conversions'] / total_conv * 100, 1) if total_conv > 0 else 0
        grade = _grade(k['cpa'], overall_cpa)
        by_keyword[category] = {
            **k,
            'ad_count': len(matched_ids),
            'conv_share_pct': share,
            'cpa_grade': grade,
        }

    # 전환수 큰 순 정렬
    by_keyword = dict(sorted(
        {k: v for k, v in by_keyword.items() if v is not None}.items(),
        key=lambda x: -x[1]['conversions']
    ))

    # 사용량 vs 효율 사분면 분류
    # X = ad_count (사용량), Y = cpa_grade (효율)
    # quadrant: 우수+많음(주력) / 우수+적음(확대 후보) / 부진+많음(개선 시급) / 부진+적음(축소)
    quadrants = {'main': [], 'expand': [], 'fix': [], 'reduce': [], 'neutral': []}
    if by_keyword:
        counts = [d['ad_count'] for d in by_keyword.values()]
        median_count = sorted(counts)[len(counts) // 2] if counts else 0
        for cat, d in by_keyword.items():
            grade = d['cpa_grade']['grade']
            high_count = d['ad_count'] >= median_count
            if grade == 'efficient' and high_count:
                quadrants['main'].append((cat, d))
            elif grade == 'efficient' and not high_count:
                quadrants['expand'].append((cat, d))
            elif grade == 'inefficient' and high_count:
                quadrants['fix'].append((cat, d))
            elif grade == 'inefficient' and not high_count:
                quadrants['reduce'].append((cat, d))
            else:
                quadrants['neutral'].append((cat, d))

    # 자동 인사이트 도출
    insights = []
    if quadrants['main']:
        cat, d = quadrants['main'][0]
        insights.append({
            'label': '주력 메시지',
            'detail': f"'{cat}' · 광고 {d['ad_count']}개로 가장 많이 쓰이면서 CPA {d['cpa_grade']['ratio_pct']}% 우수",
            'action': '6월에도 핵심 메시지로 유지·확대',
        })
    if quadrants['expand']:
        cat, d = quadrants['expand'][0]
        insights.append({
            'label': '확대 후보 메시지',
            'detail': f"'{cat}' · 광고 {d['ad_count']}개로 적게 쓰였으나 CPA {d['cpa_grade']['ratio_pct']}% 우수",
            'action': '6월 신규 소재 제작 시 우선 적용 검토',
        })
    if quadrants['fix']:
        cat, d = quadrants['fix'][0]
        insights.append({
            'label': '개선 시급 메시지',
            'detail': f"'{cat}' · 광고 {d['ad_count']}개로 많이 쓰이지만 CPA {d['cpa_grade']['ratio_pct']}% 부진",
            'action': '메시지 톤·후킹·랜딩 매칭 재점검',
        })
    if quadrants['reduce']:
        cat, d = quadrants['reduce'][0]
        insights.append({
            'label': '축소 검토 메시지',
            'detail': f"'{cat}' · 광고 {d['ad_count']}개로 적게 쓰였고 CPA {d['cpa_grade']['ratio_pct']}% 부진",
            'action': '추가 제작 보류, 기존 광고도 단계적 축소',
        })

    return {
        'baseline_period': NORMAL_MONTHS,
        'overall': overall,
        'by_keyword': by_keyword,
        'quadrants': {
            k: [{'category': c, **d} for c, d in v] for k, v in quadrants.items()
        },
        'insights': insights,
        'keyword_dict': {k: list(v) for k, v in KEYWORD_DICT.items()},
        'criteria': {
            'min_conversions': 5,
            'cpa_grade_threshold': '전체 평균 CPA ±15%',
            'note': '한 광고가 여러 키워드에 동시 매칭될 수 있음 (다중 카운트)',
        },
    }


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260518/parsed.parquet'
    r = analyze(path)
    print(f"[전체 평균 - 2~4월]")
    print(f"  전환 {r['overall']['conversions']:,}건 / CPA {r['overall']['cpa']:,}원\n")

    print(f"[키워드별 성과]")
    print(f"{'카테고리':<15} {'광고':>4} {'전환':>5} {'비중':>5} {'CPA':>8} {'CTR':>6} {'CVR':>6} 효율")
    for cat, d in r['by_keyword'].items():
        g = d['cpa_grade']
        ratio = g['ratio_pct']
        print(f"  {cat:<15} {d['ad_count']:>4} {d['conversions']:>5} {d['conv_share_pct']:>4}% {d['cpa']:>8,} {d['ctr']:>5}% {d['cvr']:>5}% {g['label']} ({ratio:+.0f}%)")

    print(f"\n[사분면 분류]")
    labels = {
        'main': '주력 메시지 (많이+효율좋음)',
        'expand': '확대 후보 (적게+효율좋음)',
        'fix': '개선 시급 (많이+효율부진)',
        'reduce': '축소 검토 (적게+효율부진)',
        'neutral': '평균 수준',
    }
    for q, items in r['quadrants'].items():
        if items:
            cats = ', '.join(i['category'] for i in items)
            print(f"  {labels[q]}: {cats}")

    print(f"\n[자동 인사이트]")
    for ins in r['insights']:
        print(f"  • [{ins['label']}] {ins['detail']}")
        print(f"    → {ins['action']}")
