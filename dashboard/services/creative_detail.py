"""소재 상세 — 전체 KPI + 시청 깔때기 + 인게이지먼트 + 지점별 효율 + 시간 추이"""
from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd

from dashboard.services.data_loader import DataBundle


def _find_creative(creative_tier: pd.DataFrame, name: str) -> Optional[pd.Series]:
    """소재명 또는 매칭키로 검색."""
    if creative_tier.empty:
        return None
    matches = creative_tier[
        (creative_tier['소재명'] == name) | (creative_tier['매칭키'] == name)
    ]
    if matches.empty:
        return None
    return matches.iloc[0]


def _branch_kpi(parsed_creative: pd.DataFrame) -> list[dict]:
    """지점별 KPI (부록 C 패턴)."""
    if parsed_creative.empty:
        return []
    grouped = parsed_creative.groupby('지점').agg(
        cost=('cost', 'sum'), clicks=('clicks', 'sum'),
        conv=('conversions', 'sum'), impr=('impressions', 'sum'),
        days=('date', 'nunique'),
    ).reset_index()
    out = []
    for _, r in grouped.iterrows():
        cost, clicks, conv, impr = int(r['cost']), int(r['clicks']), int(r['conv']), int(r['impr'])
        out.append({
            'branch': r['지점'],
            'cost': cost,
            'clicks': clicks,
            'conversions': conv,
            'impressions': impr,
            'days_active': int(r['days']),
            'cpa': round(cost / conv) if conv else None,
            'cvr': round(conv / clicks * 100, 2) if clicks else None,
            'ctr': round(clicks / impr * 100, 2) if impr else None,
        })
    out.sort(key=lambda x: (x['cpa'] if x['cpa'] else 10**9))
    return out


def _daily_trend(parsed_creative: pd.DataFrame, days: int = 30) -> list[dict]:
    """소재 일별 KPI 추이."""
    if parsed_creative.empty:
        return []
    df = parsed_creative.copy()
    df['date'] = pd.to_datetime(df['date']).dt.date
    daily = df.groupby('date').agg(
        cost=('cost', 'sum'), clicks=('clicks', 'sum'),
        conv=('conversions', 'sum'), impr=('impressions', 'sum'),
    ).reset_index().sort_values('date').tail(days)
    out = []
    for _, r in daily.iterrows():
        cost, clicks, conv, impr = int(r['cost']), int(r['clicks']), int(r['conv']), int(r['impr'])
        out.append({
            'date': r['date'].strftime('%Y-%m-%d'),
            'cost': cost, 'clicks': clicks, 'conversions': conv, 'impressions': impr,
            'cpa': round(cost / conv) if conv else None,
            'cvr': round(conv / clicks * 100, 2) if clicks else None,
            'ctr': round(clicks / impr * 100, 2) if impr else None,
        })
    return out


def _watch_funnel(parsed_creative: pd.DataFrame) -> dict:
    """시청 깔때기 + 인게이지먼트 — 컬럼 있을 때만."""
    if parsed_creative.empty:
        return {}
    impr = int(parsed_creative['impressions'].sum())
    if not impr:
        return {}
    def _col_sum(c):
        return int(parsed_creative[c].sum()) if c in parsed_creative.columns else 0
    def _col_mean(c):
        return round(float(parsed_creative[c].mean()), 2) if c in parsed_creative.columns and len(parsed_creative) else None
    v6 = _col_sum('video_watched_6s')
    return {
        'impressions': impr,
        'v6s_rate': round(v6 / impr * 100, 2) if impr else None,
        'p25_rate': round(_col_sum('video_p25') / impr * 100, 2) if impr else None,
        'p50_rate': round(_col_sum('video_p50') / impr * 100, 2) if impr else None,
        'p75_rate': round(_col_sum('video_p75') / impr * 100, 2) if impr else None,
        'p100_rate': round(_col_sum('video_p100') / impr * 100, 2) if impr else None,
        'eng15s_rate': round(_col_sum('engaged_view_15s') / impr * 100, 2) if impr else None,
        'avg_video_sec': _col_mean('avg_video_play_sec'),
        'like_rate': round(_col_sum('likes') / impr * 100, 3) if impr else None,
        'share_rate': round(_col_sum('shares') / impr * 100, 4) if impr else None,
        'comment_rate': round(_col_sum('comments') / impr * 100, 3) if impr else None,
    }


def build(bundle: DataBundle, name: str, today: Optional[date] = None) -> dict:
    today = today or date.today()
    row = _find_creative(bundle.creative_tier, name)

    # parsed에서 해당 소재 row 모음 (소재명 정확 일치)
    pc = bundle.parsed[
        (bundle.parsed['parse_status'] == 'OK')
        & ((bundle.parsed['소재명'] == name) | (bundle.parsed['매칭키'] == name))
    ].copy()

    # TIER 정보
    tier_info = None
    if row is not None:
        tier_info = {
            'name': row.get('소재명') or row.get('매칭키'),
            'creative_type': row.get('소재유형'),
            'creative_kind': row.get('소재구분'),
            'tier': str(row.get('TIER', '')).upper(),
            'tier_basis': row.get('TIER_근거'),
            'cost_total': int(row.get('총비용', 0)) if pd.notna(row.get('총비용')) else None,
            'clicks_total': int(row.get('총클릭', 0)) if pd.notna(row.get('총클릭')) else None,
            'conv_total': int(row.get('총전환', 0)) if pd.notna(row.get('총전환')) else None,
            'days_active': int(row.get('집행일수', 0)) if pd.notna(row.get('집행일수')) else None,
            'cpa': int(row['CPA']) if pd.notna(row.get('CPA')) else None,
            'cvr': float(row['CVR']) if pd.notna(row.get('CVR')) else None,
            'ctr': float(row['CTR']) if pd.notna(row.get('CTR')) else None,
            'branches_list': list(row.get('집행지점목록')) if row.get('집행지점목록') is not None else [],
            'branch_warning': row.get('지점편중주석'),
        }

    # 소재 액션 로그
    creative_actions = [a for a in (bundle.actions or [])
                        if (a.get('creative_name') == name or a.get('ad_id') == name)][:30]

    return {
        'name': name,
        'today': today.strftime('%Y-%m-%d'),
        'tier_info': tier_info,
        'branch_kpi': _branch_kpi(pc),
        'daily_trend': _daily_trend(pc),
        'watch_funnel': _watch_funnel(pc),
        'actions': creative_actions,
    }


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    from dashboard.services.data_loader import load_bundle
    b = load_bundle()
    name = '주사형비만치료제 고민끝에 50대부부 -32kg'
    d = build(b, name)
    print(f'=== {name} ===')
    print(f'TIER 정보: {d["tier_info"]}')
    print()
    print(f'지점별 KPI ({len(d["branch_kpi"])}):')
    for bk in d['branch_kpi']:
        print(f"  {bk['branch']}: CPA {bk['cpa']} / 전환 {bk['conversions']} / CVR {bk['cvr']}%")
    print()
    print(f'시청 깔때기: {d["watch_funnel"]}')
    print()
    print(f'일별 추이: {len(d["daily_trend"])}일')
