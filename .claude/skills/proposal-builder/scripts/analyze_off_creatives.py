"""OFF 소재 상세 분석 - 6월 재활용 후보 추출

분석 내용:
  1. OFF 시점 분포 + 누적 OFF 소재 수
  2. OFF 직전 N일 성과로 OFF 사유 자동 추정
     - CPA 부진: 전 지점 평균 대비 +20% 이상
     - CTR 피로: 첫 14일 대비 -25% 이상 하락
     - 저효율: 누적 전환 < 10건 (학습 미완)
     - 조기 OFF: 활성 < 14일
     - 정상 종료 (효율 양호한데 OFF) → 6월 재활용 후보
  3. 잘못 OFF한 케이스 = 재활용 후보 (효율 좋았는데 끄거나, 더 운영했어야)

베이스라인: 전 기간 운영 데이터 (OFF 직전 성과 측정용)
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES

OFF_CSV_DEFAULT = 'input/off_creatives.csv'
WINDOW_DAYS = 14  # OFF 직전·초기 14일
CPA_PEER_THRESHOLD = 1.20  # 전 지점 평균 대비 +20% → CPA 부진
CTR_FATIGUE_DROP = -25     # CTR 초기 대비 -25% 하락
MIN_TOTAL_CONV = 10        # 학습 미완 기준


def _load_off_csv(path: str) -> pd.DataFrame:
    """OFF CSV 파싱 (광고명에 콤마가 포함될 수 있으므로 마지막 콤마로 split)."""
    rows = []
    p = Path(path)
    if not p.exists():
        return pd.DataFrame(columns=['ad_name', 'off_date'])
    with open(p, encoding='utf-8-sig') as f:
        header = next(f, '').strip()
        for line in f:
            line = line.rstrip('\n\r')
            if not line:
                continue
            parts = line.rsplit(',', 1)
            if len(parts) == 2:
                rows.append({'ad_name': parts[0].strip(), 'off_date': parts[1].strip()})
    df = pd.DataFrame(rows)
    if 'off_date' in df.columns:
        df['off_date'] = pd.to_datetime(df['off_date'], errors='coerce')
    return df


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
        'ctr': round(clk / impr * 100, 2) if impr > 0 else None,
        'cvr': round(conv / clk * 100, 2) if clk > 0 else None,
        'cpa': int(cost / conv) if conv > 0 else None,
    }


def _diagnose_off(total: dict, early: dict | None, recent: dict | None,
                  span_days: int, peer_cpa: int | None) -> tuple[str, str]:
    """OFF 사유 자동 추정."""
    # 학습 미완 (저효율)
    if total['conversions'] < MIN_TOTAL_CONV:
        return ('low_volume', f'학습 미완 - 누적 전환 {total["conversions"]}건 (학습 임계 미달)')
    # 조기 OFF
    if span_days < WINDOW_DAYS:
        return ('early_off', f'조기 OFF - 활성 {span_days}일로 학습·평가 어려움')
    # CTR 피로 (초기 vs 최근)
    if early and recent and early.get('ctr') and recent.get('ctr'):
        drop = (recent['ctr'] - early['ctr']) / early['ctr'] * 100
        if drop <= CTR_FATIGUE_DROP:
            return ('fatigue', f'CTR 피로 - 초기 {early["ctr"]}% → 최근 {recent["ctr"]}% ({drop:+.1f}%)')
    # CPA 부진
    if peer_cpa and total.get('cpa') and total['cpa'] / peer_cpa >= CPA_PEER_THRESHOLD:
        ratio = (total['cpa'] / peer_cpa - 1) * 100
        return ('cpa_poor', f'CPA 부진 - {total["cpa"]:,}원 (전 지점 평균 대비 +{ratio:.0f}%)')
    # 위 어느 것도 아니면 = 효율 양호한데 OFF → 재활용 후보
    return ('reusable', f'효율 양호 종료 - CPA {total["cpa"]:,}원, 전환 {total["conversions"]}건. 6월 재활용 검토')


REASON_LABEL = {
    'low_volume': '학습 미완',
    'early_off': '조기 OFF',
    'fatigue': 'CTR 피로',
    'cpa_poor': 'CPA 부진',
    'reusable': '재활용 후보',
}


def analyze(parsed_path: str, off_csv_path: str = OFF_CSV_DEFAULT) -> dict:
    df = pd.read_parquet(parsed_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['parse_status'] == 'OK'].copy()

    # OFF CSV 로드
    off_df = _load_off_csv(off_csv_path)
    if len(off_df) == 0:
        return {
            'has_data': False,
            'note': 'OFF 소재 데이터 없음',
        }

    # 전 지점 평균 CPA (정상 운영 월 기준)
    df['month'] = df['date'].dt.strftime('%Y-%m')
    df_normal = df[df['month'].isin(['2026-02', '2026-03', '2026-04'])]
    overall = _kpi(df_normal)
    peer_cpa = overall['cpa'] if overall else None

    # OFF된 ad_name 매칭
    items = []
    for _, off_row in off_df.iterrows():
        name = off_row['ad_name']
        off_date = off_row['off_date']
        # parsed 에서 해당 광고명 일치 row (정확히)
        sub = df[df['ad_name'] == name]
        if len(sub) == 0:
            continue
        active = sub[['cost', 'impressions', 'clicks', 'conversions']].fillna(0).sum(axis=1) > 0
        sub = sub[active]
        if len(sub) == 0:
            continue
        first = sub['date'].min()
        last = sub['date'].max()
        span_days = (last - first).days + 1
        total = _kpi(sub)
        if total is None or total['cost'] == 0:
            continue

        # 초기 14일 vs OFF 직전 14일
        early_cutoff = first + pd.Timedelta(days=WINDOW_DAYS - 1)
        recent_cutoff = last - pd.Timedelta(days=WINDOW_DAYS - 1)
        early_kpi = _kpi(sub[sub['date'] <= early_cutoff]) if span_days >= WINDOW_DAYS * 2 else None
        recent_kpi = _kpi(sub[sub['date'] >= recent_cutoff]) if span_days >= WINDOW_DAYS * 2 else None

        reason_code, reason_text = _diagnose_off(total, early_kpi, recent_kpi, span_days, peer_cpa)

        # 지점 파싱
        branch = None
        parts = name.split('_')
        for part in parts[:3]:
            if part in VALID_BRANCHES:
                branch = part
                break

        items.append({
            'ad_name': name,
            'branch': branch,
            'off_date': off_date.strftime('%Y-%m-%d') if pd.notna(off_date) else '-',
            'first_date': first.strftime('%Y-%m-%d'),
            'last_date': last.strftime('%Y-%m-%d'),
            'span_days': span_days,
            'total': total,
            'early': early_kpi,
            'recent': recent_kpi,
            'reason_code': reason_code,
            'reason_label': REASON_LABEL[reason_code],
            'reason_text': reason_text,
        })

    # 사유별 분류
    by_reason = {k: [] for k in REASON_LABEL.keys()}
    for it in items:
        by_reason[it['reason_code']].append(it)

    # 6월 재활용 후보 = reusable
    reusable_candidates = sorted(
        by_reason['reusable'],
        key=lambda x: -(x['total']['conversions'] or 0)
    )

    # 통계
    stats = {
        'total_off': len(items),
        'by_reason': {k: len(v) for k, v in by_reason.items()},
    }

    # 자동 인사이트
    insights = []
    if reusable_candidates:
        top = reusable_candidates[0]
        insights.append({
            'label': '재활용 우선 후보',
            'detail': f"{len(reusable_candidates)}건 - 효율 양호했음에도 OFF 처리. 6월 재집행으로 빠른 전환 확보 가능",
            'action': f'1순위: {top["ad_name"][:50]} (전환 {top["total"]["conversions"]}건, CPA {top["total"]["cpa"]:,}원)',
        })
    if by_reason['fatigue']:
        insights.append({
            'label': 'OFF 후 학습 - 피로 진단 정확도',
            'detail': f"{len(by_reason['fatigue'])}건이 CTR 피로 신호로 OFF됨",
            'action': '동일 메시지 변주 또는 신규 후킹으로 재제작 가능',
        })
    if by_reason['low_volume']:
        insights.append({
            'label': '학습 미완 OFF',
            'detail': f"{len(by_reason['low_volume'])}건 - 전환 {MIN_TOTAL_CONV}건 미만에서 종료",
            'action': '6월 신규 소재는 최소 14일 + 전환 10건까지 학습 보장 권장',
        })

    return {
        'has_data': True,
        'window_days': WINDOW_DAYS,
        'peer_cpa': peer_cpa,
        'stats': stats,
        'by_reason': by_reason,
        'reusable_candidates': reusable_candidates,
        'insights': insights,
    }


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    path = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260518/parsed.parquet'
    r = analyze(path)
    if not r.get('has_data'):
        print(r.get('note'))
        sys.exit(0)
    s = r['stats']
    print(f"[OFF 소재 총 {s['total_off']}건]")
    print(f"사유별 분포:")
    for code, count in s['by_reason'].items():
        print(f"  {REASON_LABEL[code]:<10}: {count}건")
    print()
    print(f"[재활용 후보 {len(r['reusable_candidates'])}건]")
    for it in r['reusable_candidates'][:10]:
        print(f"  • [{it['branch']}] {it['ad_name'][:55]}")
        print(f"      활성 {it['span_days']}일 / 전환 {it['total']['conversions']}건 / CPA {it['total']['cpa']:,}원")
    print()
    print('[자동 인사이트]')
    for ins in r['insights']:
        print(f"  • [{ins['label']}] {ins['detail']}")
        print(f"    → {ins['action']}")
