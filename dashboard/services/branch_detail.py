"""지점 상세 — KPI 추이 + 광고 그룹 + 소재별 TIER + 신호·액션 필터링"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from dashboard.services.data_loader import DataBundle
from dashboard.services.kpi_progress import compute as compute_kpi
from dashboard.services.alert_engine import detect_alerts
from dashboard.services.action_recommender import generate as generate_actions


def _branch_daily(parsed: pd.DataFrame, branch: str) -> pd.DataFrame:
    df = parsed[parsed['지점'] == branch].copy()
    df['date'] = pd.to_datetime(df['date']).dt.date
    return df.groupby('date').agg(
        cost=('cost', 'sum'), impressions=('impressions', 'sum'),
        clicks=('clicks', 'sum'), conversions=('conversions', 'sum'),
    ).reset_index().sort_values('date')


def _branch_creatives(creative_tier: pd.DataFrame, parsed: pd.DataFrame, branch: str) -> list[dict]:
    """지점 내 소재별 TIER + 효율 (부록 C와 동일 패턴: 소재 TIER + 지점별 KPI 재집계)."""
    if creative_tier.empty:
        return []
    # 해당 지점이 운영한 소재만
    tier_rows = creative_tier[creative_tier['집행지점목록'].apply(
        lambda lst: branch in list(lst) if lst is not None else False
    )]
    if tier_rows.empty:
        return []
    # parsed에서 지점×소재 KPI 재집계 (전 기간 — OFF 포함, 부록 C와 동일 패턴)
    p_branch = parsed[(parsed['parse_status'] == 'OK') & (parsed['지점'] == branch)].copy()
    grouped_lookup = {}
    if not p_branch.empty:
        grouped = p_branch.groupby(['소재구분', '소재유형', '소재명']).agg(
            cost=('cost', 'sum'), clicks=('clicks', 'sum'),
            conv=('conversions', 'sum'), impr=('impressions', 'sum'),
            days=('date', 'nunique'),
        ).reset_index()
        if not grouped.empty:
            grouped['cpa'] = grouped.apply(lambda r: round(r['cost']/r['conv']) if r['conv'] else None, axis=1)
            grouped['cvr'] = grouped.apply(lambda r: round(r['conv']/r['clicks']*100, 2) if r['clicks'] else None, axis=1)
            grouped['ctr'] = grouped.apply(lambda r: round(r['clicks']/r['impr']*100, 2) if r['impr'] else None, axis=1)
            grouped_lookup = {(r['소재구분'], r['소재유형'], r['소재명']): r.to_dict() for _, r in grouped.iterrows()}

    TIER_ORDER = {'TIER1': 0, 'TIER2': 1, 'TIER3': 2, 'TIER4': 3, 'LOW_VOLUME': 4, 'UNCLASSIFIED': 5}
    out = []
    for _, r in tier_rows.iterrows():
        key = (r['소재구분'], r['소재유형'], r['소재명'])
        bk = grouped_lookup.get(key)
        if bk:
            cost, clicks, conv, cpa, cvr, ctr, days = bk['cost'], bk['clicks'], bk['conv'], bk['cpa'], bk['cvr'], bk['ctr'], bk['days']
            kpi_source = 'branch'
        else:
            cost = r.get('총비용'); clicks = r.get('총클릭'); conv = r.get('총전환')
            cpa = r.get('CPA'); cvr = r.get('CVR'); ctr = r.get('CTR'); days = r.get('집행일수')
            kpi_source = 'aggregate'
        out.append({
            'name': r.get('소재명') or r.get('매칭키'),
            'creative_type': r.get('소재유형'),
            'tier': str(r.get('TIER', '')).upper(),
            'cost': int(cost) if pd.notna(cost) else None,
            'clicks': int(clicks) if pd.notna(clicks) else None,
            'conversions': int(conv) if pd.notna(conv) else None,
            'cpa': int(cpa) if cpa and pd.notna(cpa) else None,
            'cvr': float(cvr) if cvr and pd.notna(cvr) else None,
            'ctr': float(ctr) if ctr and pd.notna(ctr) else None,
            'days_active': int(days) if pd.notna(days) else None,
            'kpi_source': kpi_source,
        })
    out.sort(key=lambda x: (TIER_ORDER.get(x['tier'], 99), x.get('cpa') if x.get('cpa') else 10**9))
    return out


def build(bundle: DataBundle, branch: str, today: Optional[date] = None) -> dict:
    today = today or date.today()
    # 지점 일별 KPI
    daily = _branch_daily(bundle.parsed, branch)
    last_n_days = []
    if not daily.empty:
        recent = daily.tail(14)   # 최근 14일
        for _, r in recent.iterrows():
            cost, clicks, conv = int(r['cost']), int(r['clicks']), int(r['conversions'])
            last_n_days.append({
                'date': r['date'].strftime('%Y-%m-%d'),
                'cost': cost, 'clicks': clicks, 'conversions': conv,
                'impressions': int(r['impressions']),
                'cpa': round(cost / conv) if conv else None,
                'cvr': round(conv / clicks * 100, 2) if clicks else None,
                'ctr': round(clicks / int(r['impressions']) * 100, 2) if r['impressions'] else None,
            })

    # 3·7일 MA
    cpa_3, cpa_7, cvr_3, cvr_7 = None, None, None, None
    if not daily.empty:
        recent3 = daily.tail(3)
        recent7 = daily.tail(7)
        def _avg(df, metric):
            df = df.copy()
            df['cpa'] = df.apply(lambda r: r['cost'] / r['conversions'] if r['conversions'] else None, axis=1)
            df['cvr'] = df.apply(lambda r: r['conversions'] / r['clicks'] * 100 if r['clicks'] else None, axis=1)
            vals = df[metric].dropna()
            return float(vals.mean()) if not vals.empty else None
        cpa_3 = _avg(recent3, 'cpa'); cpa_7 = _avg(recent7, 'cpa')
        cvr_3 = _avg(recent3, 'cvr'); cvr_7 = _avg(recent7, 'cvr')

    # 지점 KPI (KPI Progress에서 추출)
    kpi = compute_kpi(bundle, today)
    branch_kpi = kpi.branches.get(branch, {})

    # 지점 단위 신호·액션 필터
    all_alerts = detect_alerts(bundle, today)
    branch_alerts = [a for a in all_alerts if a.target_type == 'branch' and a.target_name == branch]

    all_recs = generate_actions(bundle)
    branch_recs = {
        cat: [r for r in items if r.target_type == 'branch' and r.target_name == branch]
        for cat, items in all_recs.items()
    }
    setting_recs = [r for r in all_recs.get('setting', []) if r.target_type == 'branch' and r.target_name == branch]
    branch_recs['setting'] = setting_recs

    # 지점 소재 TIER 표
    creatives = _branch_creatives(bundle.creative_tier, bundle.parsed, branch)

    # 지점 액션 로그
    branch_actions = [a for a in (bundle.actions or []) if a.get('branch') == branch][:30]

    return {
        'branch': branch,
        'today': today.strftime('%Y-%m-%d'),
        'branch_kpi': branch_kpi,
        'last_n_days': last_n_days,
        'cpa_3day_avg': round(cpa_3) if cpa_3 else None,
        'cpa_7day_avg': round(cpa_7) if cpa_7 else None,
        'cvr_3day_avg': round(cvr_3, 2) if cvr_3 else None,
        'cvr_7day_avg': round(cvr_7, 2) if cvr_7 else None,
        'alerts': branch_alerts,
        'recommendations': branch_recs,
        'creatives': creatives,
        'actions': branch_actions,
        'target_cpa': kpi.target_cpa,
    }


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    from dashboard.services.data_loader import load_bundle
    b = load_bundle()
    d = build(b, '천안', today=date(2026, 5, 19))
    print(f'=== 천안 상세 ===')
    print(f'KPI: {d["branch_kpi"]}')
    print(f'CPA 3일 MA: {d["cpa_3day_avg"]} · 7일 MA: {d["cpa_7day_avg"]}')
    print(f'최근 일별: {len(d["last_n_days"])}일')
    print(f'신호: {len(d["alerts"])}개')
    print(f'추천 액션: {sum(len(v) for v in d["recommendations"].values())}개')
    print(f'소재: {len(d["creatives"])}개')
    for c in d['creatives'][:5]:
        print(f'  [{c["tier"]}] {c["name"]}: CPA {c["cpa"]} · CVR {c["cvr"]}% · {c["kpi_source"]}')
