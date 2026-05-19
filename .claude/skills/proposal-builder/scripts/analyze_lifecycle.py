"""콘텐츠 라이프사이클 분석 - 얼마나 오래 효율적인가 / 언제 꺼야 하는가

각 매칭키(소재) 단위로:
  1. 활성 기간(span_days) - 첫 집행일부터 마지막 집행일
  2. 초기(첫 14일) vs 최근(마지막 14일) 성과 비교
  3. 피로 신호 자동 진단 (CTR/CVR 하락)
  4. 라이프사이클 단계 분류 (신선 / 성숙 / 장기)
  5. OFF·교체 권장 자동 추출

베이스라인: 전 기간 (2~5월). 5월 운영 중단은 라이프사이클 관점에서 일부 의미 있어 포함.
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 라이프사이클 단계 임계값
STAGE_FRESH_MAX = 14   # 14일 이하 = 신선 (도입·성장기)
STAGE_MATURE_MAX = 45  # 15~45일 = 성숙기, 46일+ = 장기
COMPARE_WINDOW = 14    # 초기·최근 비교 윈도우 (일)

# 피로 신호 임계값
FATIGUE_CTR_DROP = -25  # CTR 초기 대비 -25% 이상
FATIGUE_CVR_DROP = -25  # CVR 초기 대비 -25% 이상

# 최소 표본 (신뢰성)
MIN_CLICKS_PER_WINDOW = 30
MIN_TOTAL_CONV = 5


def _kpi(df: pd.DataFrame) -> dict | None:
    if len(df) == 0:
        return None
    cost = float(df['cost'].sum())
    impr = float(df['impressions'].sum())
    clk = float(df['clicks'].sum())
    conv = float(df['conversions'].sum())
    # frequency 가중평균 (한글 컬럼명 '빈도')
    freq_col = '빈도' if '빈도' in df.columns else 'frequency'
    if freq_col in df.columns and impr > 0:
        freq = float((df[freq_col] * df['impressions']).sum() / impr)
    else:
        freq = None
    return {
        'cost': int(cost),
        'impressions': int(impr),
        'clicks': int(clk),
        'conversions': int(conv),
        'ctr': round(clk / impr * 100, 2) if impr > 0 else None,
        'cvr': round(conv / clk * 100, 2) if clk > 0 else None,
        'cpa': int(cost / conv) if conv > 0 else None,
        'frequency': round(freq, 2) if freq is not None else None,
    }


def _change_pct(early, recent) -> float | None:
    if early is None or recent is None or early == 0:
        return None
    return round((recent - early) / early * 100, 1)


def _classify_stage(span_days: int) -> str:
    if span_days <= STAGE_FRESH_MAX:
        return 'fresh'
    if span_days <= STAGE_MATURE_MAX:
        return 'mature'
    return 'long'


STAGE_LABEL = {
    'fresh': '신선 (~14일)',
    'mature': '성숙 (15~45일)',
    'long': '장기 (46일+)',
}


def _build_variant_guide(long_winners: list) -> dict:
    """장수 우수 소재의 공통 패턴을 분해하여 6월 신규 제작 변주 가이드 도출.

    분해 차원:
      - 소재유형 (예: 진료셀프캠)
      - 메시지 키워드 (주사형비만치료제·고민·세대·결과 수치)
      - 후킹 구조 (예: 문제 제시형, 결과 강조형)
    """
    if not long_winners:
        return {
            'patterns': [],
            'variant_actions': [],
        }
    # 소재유형 빈도
    type_counts = {}
    for w in long_winners:
        # 매칭키 첫 토큰이 소재유형
        cn = w['creative_name']
        parts = cn.split('_', 1)
        if len(parts) >= 1:
            t = parts[0]
            type_counts[t] = type_counts.get(t, 0) + 1
    # 공통 키워드 (단순 키워드 집계)
    keyword_groups = {
        '주사형비만치료제': ['주사형', '비만치료제'],
        '고민·문제 제시': ['고민', '실패', '마지막'],
        '결과 수치 (-kg)': ['-32kg', '-20kg', 'kg'],
        '연령대·관계': ['40대', '50대', '60대', '부부'],
        '대안 메시지': ['더중요', '대신', '없이', '끊고'],
    }
    keyword_hits = {k: 0 for k in keyword_groups}
    for w in long_winners:
        name = w['creative_name']
        for group, patterns in keyword_groups.items():
            if any(p in name for p in patterns):
                keyword_hits[group] += 1

    patterns = []
    for t, n in sorted(type_counts.items(), key=lambda x: -x[1]):
        patterns.append({
            'kind': '소재유형',
            'value': t,
            'count': n,
            'detail': f'장수 우수 {n}건 중 {n}건이 {t} 포맷',
        })
    for kw, n in sorted(keyword_hits.items(), key=lambda x: -x[1]):
        if n > 0:
            patterns.append({
                'kind': '메시지 키워드',
                'value': kw,
                'count': n,
                'detail': f'장수 우수 소재에서 "{kw}" 메시지 {n}건 포함',
            })

    # 변주 액션 가이드 (codex 권장 패턴)
    variant_actions = [
        {
            'axis': '첫 3초 후킹',
            'guide': '문제 제시형(고민·실패)으로 시작 - 장수 우수 소재 공통 후킹 패턴',
        },
        {
            'axis': '연령대 타겟팅',
            'guide': '40대·50대·60대 + 부부/개인 사례 변주 (1지점당 2~3 변주)',
        },
        {
            'axis': '결과 수치',
            'guide': '-32kg 외 -20kg, -15kg 같은 다른 감량 수치 변주 테스트',
        },
        {
            'axis': '대안 메시지',
            'guide': '"주사형 비만치료제 보다 더중요한 / 끊고 / 없이" 같은 대안 표현 재조합',
        },
        {
            'axis': '인플루언서 캐스팅',
            'guide': '지역명 + 인플 닉네임 패턴 유지 (수원·창원에서 효과적)',
        },
    ]
    return {
        'patterns': patterns,
        'variant_actions': variant_actions,
        'source_count': len(long_winners),
    }


def analyze(parsed_path: str) -> dict:
    df = pd.read_parquet(parsed_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['parse_status'] == 'OK'].copy()
    df = df.dropna(subset=['매칭키'])
    # 5월 운영 중단으로 최근 윈도우 노이즈 방지 - 정상 운영 월(2~4월)만 사용
    df['month'] = df['date'].dt.strftime('%Y-%m')
    df = df[df['month'].isin(['2026-02', '2026-03', '2026-04'])]

    items = []
    for key, sub in df.groupby('매칭키'):
        sub = sub.sort_values('date')
        first = sub['date'].min()
        last = sub['date'].max()
        span_days = (last - first).days + 1
        total = _kpi(sub)
        if total is None or total['conversions'] < MIN_TOTAL_CONV:
            continue

        # 초기·최근 비교
        early_cutoff = first + pd.Timedelta(days=COMPARE_WINDOW - 1)
        recent_cutoff = last - pd.Timedelta(days=COMPARE_WINDOW - 1)
        early_df = sub[sub['date'] <= early_cutoff]
        recent_df = sub[sub['date'] >= recent_cutoff]
        # 초기와 최근이 겹치는 경우 (span_days < 14*2) - 비교 의미 약함
        comparable = span_days >= COMPARE_WINDOW * 2
        early_kpi = _kpi(early_df) if comparable else None
        recent_kpi = _kpi(recent_df) if comparable else None

        # 충분한 클릭이 있을 때만 비교
        if early_kpi and recent_kpi:
            if early_kpi['clicks'] < MIN_CLICKS_PER_WINDOW or recent_kpi['clicks'] < MIN_CLICKS_PER_WINDOW:
                early_kpi = None
                recent_kpi = None

        ctr_change = _change_pct(early_kpi['ctr'], recent_kpi['ctr']) if (early_kpi and recent_kpi) else None
        cvr_change = _change_pct(early_kpi['cvr'], recent_kpi['cvr']) if (early_kpi and recent_kpi) else None
        cpa_change = _change_pct(early_kpi['cpa'], recent_kpi['cpa']) if (early_kpi and recent_kpi) else None

        # 피로 신호
        fatigue = False
        fatigue_reasons = []
        if ctr_change is not None and ctr_change <= FATIGUE_CTR_DROP:
            fatigue = True
            fatigue_reasons.append(f'CTR {ctr_change}%')
        if cvr_change is not None and cvr_change <= FATIGUE_CVR_DROP:
            fatigue = True
            fatigue_reasons.append(f'CVR {cvr_change}%')

        # 라이프사이클 단계
        stage = _classify_stage(span_days)

        # 권장 액션
        if stage == 'long' and fatigue:
            recommendation = 'OFF 권장'
            reason = '장기 운영 + 피로 신호 (' + ' / '.join(fatigue_reasons) + ')'
        elif stage == 'long' and not fatigue and ctr_change is not None:
            recommendation = '장수 우수 (보존 검토)'
            reason = f'{span_days}일 운영에도 성과 유지 (CTR {ctr_change}%, CVR {cvr_change}%)'
        elif stage == 'long' and not comparable:
            recommendation = '장기 운영 (비교 데이터 부족)'
            reason = f'{span_days}일 운영 중이나 초기·최근 비교 데이터 부족'
        elif stage == 'mature' and fatigue:
            recommendation = '피로 신호 - 모니터링 강화'
            reason = '성숙기 + 피로 신호 (' + ' / '.join(fatigue_reasons) + ')'
        elif stage == 'fresh' and total['cpa'] and total['cpa'] > 50000:
            recommendation = '초기 효율 부진 - 조기 점검'
            reason = f'신선 단계({span_days}일)이나 CPA {total["cpa"]:,}원 높음'
        else:
            recommendation = '유지'
            reason = '특이 신호 없음'

        items.append({
            'creative_name': key,
            'first_date': first.strftime('%Y-%m-%d'),
            'last_date': last.strftime('%Y-%m-%d'),
            'span_days': span_days,
            'stage': stage,
            'stage_label': STAGE_LABEL[stage],
            'total': total,
            'early': early_kpi,
            'recent': recent_kpi,
            'ctr_change_pct': ctr_change,
            'cvr_change_pct': cvr_change,
            'cpa_change_pct': cpa_change,
            'fatigue': fatigue,
            'fatigue_reasons': fatigue_reasons,
            'recommendation': recommendation,
            'reason': reason,
        })

    # 단계별 + 권장 액션별 그룹화
    by_stage = {'fresh': [], 'mature': [], 'long': []}
    for it in items:
        by_stage[it['stage']].append(it)

    by_recommendation = {}
    for it in items:
        by_recommendation.setdefault(it['recommendation'], []).append(it)

    # OFF 권장 + 장수 우수 = 핵심 운영 후보
    off_candidates = [it for it in items if it['recommendation'] == 'OFF 권장']
    long_winners = [it for it in items if it['recommendation'].startswith('장수 우수')]

    # 단계 분포 통계
    stage_stats = {
        s: {
            'count': len(items_in_stage),
            'avg_cpa': int(sum(i['total']['cpa'] for i in items_in_stage if i['total']['cpa']) / max(1, len([i for i in items_in_stage if i['total']['cpa']]))) if items_in_stage else None,
            'total_conv': sum(i['total']['conversions'] for i in items_in_stage),
        }
        for s, items_in_stage in by_stage.items()
    }

    # 자동 인사이트
    insights = []
    if off_candidates:
        insights.append({
            'label': 'OFF 권장 소재',
            'detail': f'{len(off_candidates)}건 - 장기 운영 + 피로 신호 감지',
            'action': '6월 1주차 광고 정리 시 우선 검토. 검증 KPI: 정리 후 잔여 광고로 CPA·CVR 유지 여부',
        })
    if long_winners:
        insights.append({
            'label': '장수 우수 소재',
            'detail': f'{len(long_winners)}건 - 46일+ 운영에도 성과 유지',
            'action': '메시지·후킹 분해하여 신규 소재 제작 시 차용 검토',
        })
    fatigue_in_mature = [it for it in by_stage['mature'] if it['fatigue']]
    if fatigue_in_mature:
        insights.append({
            'label': '성숙기 피로 진입',
            'detail': f'{len(fatigue_in_mature)}건 - 모니터링 강화 필요',
            'action': '다음 2주 내 추가 하락 시 OFF 후보로 격상',
        })

    # 장수 우수 소재 공통 패턴 → 6월 변주 가이드
    variant_guide = _build_variant_guide(long_winners)

    return {
        'criteria': {
            'stage_fresh_max': STAGE_FRESH_MAX,
            'stage_mature_max': STAGE_MATURE_MAX,
            'compare_window': COMPARE_WINDOW,
            'fatigue_ctr_drop': FATIGUE_CTR_DROP,
            'fatigue_cvr_drop': FATIGUE_CVR_DROP,
            'min_clicks_per_window': MIN_CLICKS_PER_WINDOW,
            'min_total_conv': MIN_TOTAL_CONV,
        },
        'items_count': len(items),
        'stage_stats': stage_stats,
        'by_stage': by_stage,
        'off_candidates': off_candidates,
        'long_winners': long_winners,
        'insights': insights,
        'variant_guide': variant_guide,
    }


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260518/parsed.parquet'
    r = analyze(path)
    print(f"분석 소재: {r['items_count']}개\n")
    print('[단계 분포]')
    for s, stats in r['stage_stats'].items():
        print(f"  {STAGE_LABEL[s]:<18}: {stats['count']}개 · 평균 CPA {stats['avg_cpa']:,}원 · 누적 전환 {stats['total_conv']:,}건")
    print()
    print(f"[OFF 권장 {len(r['off_candidates'])}건]")
    for it in r['off_candidates'][:10]:
        print(f"  • {it['creative_name'][:55]} ({it['span_days']}일) · {it['reason']}")
    print()
    print(f"[장수 우수 {len(r['long_winners'])}건]")
    for it in r['long_winners'][:10]:
        print(f"  • {it['creative_name'][:55]} ({it['span_days']}일) · {it['reason']}")
    print()
    print('[자동 인사이트]')
    for ins in r['insights']:
        print(f"  • [{ins['label']}] {ins['detail']}")
        print(f"    → {ins['action']}")
