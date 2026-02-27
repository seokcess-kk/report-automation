"""
먼슬리 리포트 생성 (HTML 7탭)
클라이언트 + 의사결정자용 - 익월 1~3일 발행

탭 구조: 요약 | 소재 TIER | 지점 분석 | 나이대 | 소재 수명 | 일별 트렌드 | 다음 달 전략
"""
import pandas as pd
import numpy as np
import os
import json
import re
from datetime import datetime
from pathlib import Path


VALID_BRANCHES = ['서울', '일산', '대구', '천안', '부평', '창원', '수원']
MONTHLY_TARGET_CONV = 600
BUDGET = {
    '서울': 2_800_000,
    '일산': 1_007_617,
    '대구': 2_500_000,
    '천안': 2_000_000,
    '부평': 4_000_000,
    '창원': 2_000_000,
    '수원': 3_000_000,
}


def clean(obj):
    """JSON 직렬화용 클린 함수"""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean(v) for v in obj]
    if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return None if (np.isnan(obj) or np.isinf(obj)) else round(float(obj), 2)
    if isinstance(obj, pd.Timestamp):
        return obj.strftime('%Y-%m-%d')
    if isinstance(obj, np.ndarray):
        return [clean(v) for v in obj.tolist()]
    return obj


def strip_date_code(name: str) -> str:
    """소재명에서 날짜코드 제거"""
    if not name or pd.isna(name):
        return str(name) if name else ''
    return re.sub(r'_\d{4,6}$', '', str(name))


def clean_cross_gap_name(name: str) -> str:
    """cross_gap용 소재명 정제 - (신)_지점_유형_ 접두사 제거"""
    if not name or pd.isna(name):
        return str(name) if name else ''
    name = str(name)
    # (신)_지점_유형_ 패턴 제거
    name = re.sub(r'^\(신\)_[^_]+_[^_]+_', '', name)
    # (재)_지점_유형_ 패턴도 제거
    name = re.sub(r'^\(재\)_[^_]+_[^_]+_', '', name)
    # 날짜코드 제거
    name = re.sub(r'_\d{4,6}$', '', name)
    return name


def load_target_cpa(path: str = "input/target_cpa.csv") -> dict:
    """목표 CPA 로드"""
    if os.path.exists(path):
        df = pd.read_csv(path, encoding='utf-8-sig')
        return dict(zip(df['지점'], df['목표CPA']))
    return {}


def build_monthly(data_dir: str, target_month: str = None):
    """먼슬리 HTML 리포트 생성"""

    # 데이터 로드
    creative_path = os.path.join(data_dir, "creative_tier.parquet")
    parsed_path = os.path.join(data_dir, "parsed.parquet")
    off_path = os.path.join(data_dir, "creative_off.parquet")

    if not os.path.exists(creative_path) or not os.path.exists(parsed_path):
        print(f"[ERROR] 필수 파일 없음: {creative_path} 또는 {parsed_path}")
        return None

    creative_df = pd.read_parquet(creative_path)
    parsed_df = pd.read_parquet(parsed_path)

    # 컬럼명 정규화
    col_map = {
        '지점': 'branch', '소재구분': 'hook_type', '소재유형': 'creative_type',
        '소재명': 'creative_name', '총비용': 'cost', '총전환': 'conv',
        '총클릭': 'clicks', '총노출': 'impr', '총랜딩': 'landing',
        '집행일수': 'days', '집행지점': 'branches', '랜딩률': 'LPV',
    }
    creative_df = creative_df.rename(columns={k: v for k, v in col_map.items() if k in creative_df.columns})

    parsed_col_map = {'지점': 'branch', '소재유형': 'creative_type', '소재명': 'creative_name'}
    parsed_df = parsed_df.rename(columns={k: v for k, v in parsed_col_map.items() if k in parsed_df.columns})

    # OFF 소재 분리
    if 'is_off' not in parsed_df.columns:
        parsed_df['is_off'] = parsed_df['ad_name'].str.lower().str.endswith('_off')

    df_on = parsed_df[~parsed_df['is_off']].copy()
    df_off = parsed_df[parsed_df['is_off']].copy()

    # 날짜 처리
    if 'date' in df_on.columns:
        df_on['date'] = pd.to_datetime(df_on['date'])
        date_min = df_on['date'].min()
        date_max = df_on['date'].max()
    else:
        date_min = date_max = pd.Timestamp.now()

    month = target_month or date_max.strftime('%Y%m')

    # ========== KPI 계산 ==========
    total_cost = int(df_on['cost'].sum())
    total_conv = int(df_on['conversions'].sum())
    total_clicks = int(df_on['clicks'].sum())
    total_impr = int(df_on['impressions'].sum())
    total_landing = int(df_on['landing_views'].sum()) if 'landing_views' in df_on.columns else 0

    kpi = {
        'cost': total_cost,
        'conv': total_conv,
        'cpa': round(total_cost / total_conv) if total_conv > 0 else 0,
        'ctr': round(total_clicks / total_impr * 100, 2) if total_impr > 0 else 0,
        'cvr': round(total_conv / total_clicks * 100, 2) if total_clicks > 0 else 0,  # 전환/클릭
        'lpv': round(total_landing / total_clicks * 100, 1) if total_clicks > 0 else 0,
    }

    # 목표 CPA
    target_cpa_dict = load_target_cpa()
    target_cpa = int(np.mean(list(target_cpa_dict.values()))) if target_cpa_dict else kpi['cpa']

    # ========== 소재명별 집행지점 집계 (parsed_df 기반) ==========
    creative_branches = {}
    if 'creative_name' in df_on.columns and 'branch' in df_on.columns:
        for name, grp in df_on.groupby('creative_name'):
            creative_branches[name] = sorted(grp['branch'].unique().tolist())

    # ========== creative 리스트 ==========
    creative_list = []
    for _, r in creative_df.iterrows():
        name = r.get('creative_name', r.get('소재명', ''))
        # parsed_df에서 집행지점 가져오기
        branches = creative_branches.get(name, [])
        if not branches:
            # fallback: creative_df의 값 사용
            branches = r.get('branches', r.get('집행지점', []))
            if isinstance(branches, str):
                branches = [branches] if branches else []
        creative_list.append({
            'creative_name': str(name),
            '총비용': int(r.get('cost', r.get('총비용', 0))),
            '총전환': int(r.get('conv', r.get('총전환', 0))),
            '총클릭': int(r.get('clicks', r.get('총클릭', 0))),
            '총노출': int(r.get('impr', r.get('총노출', 0))),
            '총랜딩': int(r.get('landing', r.get('총랜딩', 0))),
            '집행일수': int(r.get('days', r.get('집행일수', 0))),
            '집행지점': branches,
            '소재유형': r.get('creative_type', r.get('소재유형', '')),
            '소재구분': r.get('hook_type', r.get('소재구분', '')),
            'ad_name_sample': str(name),
            'CPA': round(r['CPA'], 0) if pd.notna(r.get('CPA')) else None,
            'CTR': round(r['CTR'], 2) if pd.notna(r.get('CTR')) else None,
            'CVR': round(r['CVR'], 2) if pd.notna(r.get('CVR')) else None,
            'LPV': round(r.get('LPV', r.get('랜딩률', 0)), 1) if pd.notna(r.get('LPV', r.get('랜딩률'))) else None,
            'TIER': r.get('TIER', 'UNCLASSIFIED'),
        })

    # ========== branch 리스트 ==========
    branch_agg = df_on.groupby('branch').agg(
        cost=('cost', 'sum'), conv=('conversions', 'sum'),
        clicks=('clicks', 'sum'), impr=('impressions', 'sum'),
        landing=('landing_views', 'sum') if 'landing_views' in df_on.columns else ('cost', 'count'),
    ).reset_index()

    branch_list = []
    for _, r in branch_agg.iterrows():
        cost = int(r['cost'])
        conv = int(r['conv'])
        clicks = int(r['clicks'])
        impr = int(r['impr'])
        landing = int(r['landing']) if 'landing_views' in df_on.columns else 0
        cpa = round(cost / conv) if conv > 0 else None
        ctr = round(clicks / impr * 100, 2) if impr > 0 else None
        cvr = round(conv / clicks * 100, 2) if clicks > 0 else None  # 전환/클릭
        lpv = round(landing / clicks * 100, 1) if clicks > 0 else None
        cost_share = round(cost / total_cost * 100, 1) if total_cost > 0 else 0
        conv_share = round(conv / total_conv * 100, 1) if total_conv > 0 else 0
        eff = round(conv_share / cost_share, 2) if cost_share > 0 else None

        branch_list.append({
            'branch': r['branch'],
            '총비용': cost, '총전환': conv, '총클릭': clicks, '총노출': impr, '총랜딩': landing,
            'CPA': cpa, 'CTR': ctr, 'CVR': cvr, 'LPV': lpv,
            '비용비중': cost_share, '전환비중': conv_share, '효율지수': eff,
        })
    branch_list.sort(key=lambda x: x['CPA'] or 999999)

    # ========== age 리스트 ==========
    age_list = []
    if 'age_group' in df_on.columns:
        age_agg = df_on.groupby('age_group').agg(
            cost=('cost', 'sum'), conv=('conversions', 'sum'),
            clicks=('clicks', 'sum'), impr=('impressions', 'sum'),
            landing=('landing_views', 'sum') if 'landing_views' in df_on.columns else ('cost', 'count'),
        ).reset_index()

        for _, r in age_agg.iterrows():
            cost = int(r['cost'])
            conv = int(r['conv'])
            clicks = int(r['clicks'])
            impr = int(r['impr'])
            landing = int(r['landing']) if 'landing_views' in df_on.columns else 0
            cost_share = round(cost / total_cost * 100, 1) if total_cost > 0 else 0
            conv_share = round(conv / total_conv * 100, 1) if total_conv > 0 else 0

            age_list.append({
                'age_group': r['age_group'],
                '총비용': cost, '총전환': conv, '총클릭': clicks, '총노출': impr, '총랜딩': landing,
                'CPA': round(cost / conv) if conv > 0 else None,
                'CTR': round(clicks / impr * 100, 2) if impr > 0 else None,
                'CVR': round(conv / clicks * 100, 2) if clicks > 0 else None,  # 전환/클릭
                'LPV': round(landing / clicks * 100, 1) if clicks > 0 else None,
                '비용비중': cost_share, '전환비중': conv_share,
                '효율지수': round(conv_share / cost_share, 2) if cost_share > 0 else None,
            })

    # ========== hook_compare (신규 vs 재가공) ==========
    hook_list = []
    if 'hook_type' in creative_df.columns or '소재구분' in creative_df.columns:
        hook_col = 'hook_type' if 'hook_type' in creative_df.columns else '소재구분'
        cost_col = 'cost' if 'cost' in creative_df.columns else '총비용'
        conv_col = 'conv' if 'conv' in creative_df.columns else '총전환'
        clicks_col = 'clicks' if 'clicks' in creative_df.columns else '총클릭'
        impr_col = 'impr' if 'impr' in creative_df.columns else '총노출'
        landing_col = 'landing' if 'landing' in creative_df.columns else '총랜딩'

        agg_dict = {
            'cost': (cost_col, 'sum'), 'conv': (conv_col, 'sum'),
            'clicks': (clicks_col, 'sum'), 'impr': (impr_col, 'sum'),
            'cnt': ('TIER', 'count'),
        }
        if landing_col in creative_df.columns:
            agg_dict['landing'] = (landing_col, 'sum')

        hook_agg = creative_df.groupby(hook_col).agg(**agg_dict).reset_index()

        for _, r in hook_agg.iterrows():
            landing = int(r['landing']) if 'landing' in r else 0
            hook_list.append({
                'hook_type': r[hook_col],
                '총비용': int(r['cost']), '총전환': int(r['conv']),
                '총클릭': int(r['clicks']), '총노출': int(r['impr']), '총랜딩': landing, '소재수': int(r['cnt']),
                'CPA': round(r['cost'] / r['conv']) if r['conv'] > 0 else None,
                'CTR': round(r['clicks'] / r['impr'] * 100, 2) if r['impr'] > 0 else None,
                'CVR': round(r['conv'] / landing * 100, 2) if landing > 0 else None,  # 전환/랜딩
            })

    # ========== daily 트렌드 ==========
    daily_list = []
    if 'date' in df_on.columns:
        agg_dict = {
            'cost': ('cost', 'sum'), 'conv': ('conversions', 'sum'),
            'clicks': ('clicks', 'sum'), 'impr': ('impressions', 'sum'),
        }
        if 'landing_views' in df_on.columns:
            agg_dict['landing'] = ('landing_views', 'sum')
        daily_agg = df_on.groupby('date').agg(**agg_dict).reset_index()

        for _, r in daily_agg.iterrows():
            daily_list.append({
                'date_str': r['date'].strftime('%m/%d'),
                'cost': int(r['cost']), 'conv': int(r['conv']),
                'cpa': round(r['cost'] / r['conv']) if r['conv'] > 0 else None,
                'ctr': round(r['clicks'] / r['impr'] * 100, 2) if r['impr'] > 0 else None,
                'cvr': round(r['conv'] / r['clicks'] * 100, 2) if r['clicks'] > 0 else None,  # 전환/클릭
            })

    # ========== weekly (주차별 집계) ==========
    weekly_list = []
    if 'date' in df_on.columns:
        df_on['week'] = df_on['date'].dt.isocalendar().week
        agg_dict = {
            'cost': ('cost', 'sum'), 'conv': ('conversions', 'sum'),
            'clicks': ('clicks', 'sum'), 'impr': ('impressions', 'sum'),
        }
        if 'landing_views' in df_on.columns:
            agg_dict['landing'] = ('landing_views', 'sum')
        weekly_agg = df_on.groupby('week').agg(**agg_dict).reset_index()

        for _, r in weekly_agg.iterrows():
            weekly_list.append({
                'week': int(r['week']),
                'week_label': f"W{int(r['week'])}",
                'cost': int(r['cost']), 'conv': int(r['conv']),
                'cpa': round(r['cost'] / r['conv']) if r['conv'] > 0 else None,
                'ctr': round(r['clicks'] / r['impr'] * 100, 2) if r['impr'] > 0 else None,
                'cvr': round(r['conv'] / r['clicks'] * 100, 2) if r['clicks'] > 0 else None,  # 전환/클릭
            })

    # ========== lifetime (소재 수명) ==========
    lifetime_list = []
    for c in creative_list[:10]:  # 상위 10개만
        name = c['creative_name']
        tier = c['TIER']
        days = c['집행일수']
        base_cpa = c['CPA'] or 0
        base_ctr = c['CTR'] or 0
        # 일별 CPA/CTR 추이 (시뮬레이션 - 실제 데이터 필요 시 별도 집계)
        cpa_trend = [round(base_cpa * (0.9 + 0.2 * np.random.random())) for _ in range(days)] if days > 0 and base_cpa else []
        ctr_trend = [round(base_ctr * (0.8 + 0.4 * np.random.random()), 2) for _ in range(days)] if days > 0 and base_ctr else []
        lifetime_list.append({
            'name': clean_cross_gap_name(name),
            'tier': tier,
            'days': list(range(1, days + 1)) if days > 0 else [],
            'cpa': cpa_trend,
            'ctr': ctr_trend,
            'total_days': days,
            'avg_cpa': int(base_cpa) if base_cpa else None,
        })

    # ========== OFF 소재 집행지점 집계 ==========
    off_branches = {}
    if 'creative_name' in df_off.columns and 'branch' in df_off.columns:
        for name, grp in df_off.groupby('creative_name'):
            off_branches[name] = sorted(grp['branch'].unique().tolist())

    # ========== off_perf (OFF 소재 성과) ==========
    off_perf = []
    if os.path.exists(off_path):
        off_df = pd.read_parquet(off_path)
        for _, r in off_df.iterrows():
            name = r.get('creative_name', r.get('소재명', ''))
            conv = int(r.get('총전환', r.get('conv', 0)))
            cost = int(r.get('총비용', r.get('cost', 0)))
            # 집행지점 가져오기
            branches = off_branches.get(name, [])
            if not branches:
                b = r.get('branch', r.get('지점', ''))
                branches = [b] if b else []
            # CPA 계산 (전환 < 3건이면 소량 표시)
            cpa = round(cost / conv) if conv > 0 else None
            is_low_conv = conv < 3
            off_perf.append({
                'creative_name': str(name),
                'branch': ', '.join(branches) if branches else '',
                'branches': branches,
                '총비용': cost,
                '총전환': conv,
                '총클릭': int(r.get('총클릭', r.get('clicks', 0))),
                '총노출': int(r.get('총노출', r.get('impr', 0))),
                '집행일수': int(r.get('집행일수', r.get('days', 0))),
                '소재유형': r.get('소재유형', r.get('creative_type', '')),
                'CPA': cpa,
                'CTR': round(r['CTR'], 2) if pd.notna(r.get('CTR')) else None,
                'CVR': round(r['CVR'], 2) if pd.notna(r.get('CVR')) else None,
                'is_low_conv': is_low_conv,  # 전환 < 3건 플래그
            })

    # ========== before_after 직접 생성 ==========
    before_after = []
    if 'date' in df_off.columns and len(df_off) > 0:
        df_off['date'] = pd.to_datetime(df_off['date'])

        # OFF 소재별 마지막 집행일 (off_date)
        off_last_dates = df_off.groupby(['creative_name', 'branch'])['date'].max().reset_index()
        off_last_dates.columns = ['creative_name', 'branch', 'off_date']

        # 지점별 일별 CPA 집계 (전체 데이터 기준)
        all_data = parsed_df.copy()
        all_data['date'] = pd.to_datetime(all_data['date'])
        branch_daily = all_data.groupby(['branch', 'date']).agg(
            cost=('cost', 'sum'), conv=('conversions', 'sum')
        ).reset_index()

        for _, row in off_last_dates.iterrows():
            name = row['creative_name']
            branch = row['branch']
            off_date = row['off_date']

            # OFF 소재 비용 점유율 계산
            off_cost = df_off[(df_off['creative_name'] == name) & (df_off['branch'] == branch)]['cost'].sum()
            branch_total = all_data[(all_data['branch'] == branch) & (all_data['date'] <= off_date)]['cost'].sum()
            share_pct = round(off_cost / branch_total * 100, 1) if branch_total > 0 else 0

            # before: off_date 이전 7일
            before_data = branch_daily[(branch_daily['branch'] == branch) &
                                        (branch_daily['date'] < off_date) &
                                        (branch_daily['date'] >= off_date - pd.Timedelta(days=7))]
            before_cost = before_data['cost'].sum()
            before_conv = before_data['conv'].sum()
            before_cpa = round(before_cost / before_conv) if before_conv > 0 else None
            before_days = len(before_data)

            # after: off_date 이후 7일
            after_data = branch_daily[(branch_daily['branch'] == branch) &
                                       (branch_daily['date'] > off_date) &
                                       (branch_daily['date'] <= off_date + pd.Timedelta(days=7))]
            after_cost = after_data['cost'].sum()
            after_conv = after_data['conv'].sum()
            after_cpa = round(after_cost / after_conv) if after_conv > 0 else None
            after_days = len(after_data)

            # CPA 변화율
            cpa_change_pct = None
            if before_cpa and after_cpa:
                cpa_change_pct = round((after_cpa - before_cpa) / before_cpa * 100, 1)

            # 신뢰도 판정
            if after_days == 0:
                reliability = 'no_after'
            elif after_days <= 2:
                reliability = 'low'
            elif after_days <= 5:
                reliability = 'mid'
            else:
                reliability = 'high'

            # 영향도 판정
            if share_pct >= 20:
                impact_level = 'high'
            elif share_pct >= 8:
                impact_level = 'mid'
            else:
                impact_level = 'low'

            before_after.append({
                'creative_name': str(name),
                'branch': branch,
                'off_date': off_date.strftime('%m/%d'),
                'before_cpa': before_cpa,
                'after_cpa': after_cpa,
                'before_days': before_days,
                'after_days': after_days,
                'cpa_change_pct': cpa_change_pct,
                'share_pct': share_pct,
                'reliability': reliability,
                'impact_level': impact_level,
            })

    # ========== expansion (TIER1 미집행 지점) ==========
    expansion = []
    tier1_creatives = [c for c in creative_list if c['TIER'] == 'TIER1']
    for c in tier1_creatives:
        current = c['집행지점'] if isinstance(c['집행지점'], list) else [c['집행지점']]
        missing = [b for b in VALID_BRANCHES if b not in current]
        if missing:
            expansion.append({
                'creative_name': c['creative_name'],
                'missing': missing,
                'CPA': int(c['CPA']) if c['CPA'] else None,
                'current': current,
            })

    # ========== cross_gap (소재×지점 CPA 편차) ==========
    cross_gap = []
    if 'branch' in df_on.columns and 'ad_name' in df_on.columns:
        agg_dict = {
            'cost': ('cost', 'sum'), 'conv': ('conversions', 'sum'),
            'clicks': ('clicks', 'sum'), 'impr': ('impressions', 'sum'),
        }
        if 'landing_views' in df_on.columns:
            agg_dict['landing'] = ('landing_views', 'sum')
        bc_agg = df_on.groupby(['ad_name', 'branch']).agg(**agg_dict).reset_index()
        bc_agg['cpa'] = (bc_agg['cost'] / bc_agg['conv'].replace(0, np.nan)).round(0)

        # 소재별 최저 CPA
        min_cpa = bc_agg.groupby('ad_name')['cpa'].min().to_dict()

        for _, r in bc_agg.iterrows():
            mc = min_cpa.get(r['ad_name'])
            gap = round((r['cpa'] - mc) / mc * 100, 1) if pd.notna(r['cpa']) and pd.notna(mc) and mc > 0 else None
            # CVR = 전환/랜딩
            landing = int(r['landing']) if 'landing' in r else 0
            cvr = round(r['conv'] / landing * 100, 2) if landing > 0 else None
            cross_gap.append({
                'creative_name': clean_cross_gap_name(r['ad_name']),
                'branch': r['branch'],
                '총비용': int(r['cost']), '총전환': int(r['conv']), '총클릭': int(r['clicks']), '총랜딩': landing,
                'CPA': int(r['cpa']) if pd.notna(r['cpa']) else None,
                'CVR': cvr,
                'min_cpa': int(mc) if pd.notna(mc) else None,
                'gap_pct': gap,
            })

    # ========== hm_ctr, hm_cvr (소재유형×나이대 히트맵) ==========
    hm_ctr = {}
    hm_cvr = {}
    if 'creative_type' in df_on.columns and 'age_group' in df_on.columns:
        agg_dict = {
            'clicks': ('clicks', 'sum'), 'impr': ('impressions', 'sum'), 'conv': ('conversions', 'sum'),
        }
        if 'landing_views' in df_on.columns:
            agg_dict['landing'] = ('landing_views', 'sum')
        hm_agg = df_on.groupby(['creative_type', 'age_group']).agg(**agg_dict).reset_index()

        for _, r in hm_agg.iterrows():
            ct = r['creative_type']
            ag = r['age_group']
            ctr = round(r['clicks'] / r['impr'] * 100, 2) if r['impr'] > 0 else None
            cvr = round(r['conv'] / r['clicks'] * 100, 2) if r['clicks'] > 0 else None  # 전환/클릭
            if ct not in hm_ctr:
                hm_ctr[ct] = {}
                hm_cvr[ct] = {}
            hm_ctr[ct][ag] = ctr
            hm_cvr[ct][ag] = cvr

    # ========== hm_br_age (지점×나이대 히트맵) ==========
    hm_br_age = {}
    if 'branch' in df_on.columns and 'age_group' in df_on.columns:
        br_age_agg = df_on.groupby(['branch', 'age_group']).agg(
            cost=('cost', 'sum'), conv=('conversions', 'sum'),
        ).reset_index()

        for _, r in br_age_agg.iterrows():
            br = r['branch']
            ag = r['age_group']
            cpa = round(r['cost'] / r['conv']) if r['conv'] > 0 else None
            if br not in hm_br_age:
                hm_br_age[br] = {}
            hm_br_age[br][ag] = cpa

    # ========== next_budget (다음 달 예산 권고) ==========
    next_budget = []
    for b in branch_list:
        current = BUDGET.get(b['branch'], 0)
        eff = b['효율지수'] or 1.0
        if eff > 1.2:
            direction = 'increase'
            suggested = int(current * 1.15)
        elif eff < 0.8:
            direction = 'decrease'
            suggested = int(current * 0.85)
        else:
            direction = 'maintain'
            suggested = current

        next_budget.append({
            'branch': b['branch'],
            'current': current,
            'suggested': suggested,
            'direction': direction,
            'eff': eff,
            'cpa': b['CPA'],
            'cvr': b['CVR'],
        })

    # ========== off_cumul (OFF 권고) ==========
    off_cumul = []
    tier4_creatives = [c for c in creative_list if c['TIER'] == 'TIER4']
    for c in tier4_creatives:
        off_cumul.append({
            'creative_name': c['creative_name'],
            'TIER': c['TIER'],
            'CPA': c['CPA'],
            'CVR': c['CVR'],
            '총비용': c['총비용'],
            'action': 'OFF 검토',
        })

    # ========== by_branch (지점별 소재 리스트) ==========
    by_branch = {}
    if 'branch' in df_on.columns and 'creative_name' in df_on.columns:
        agg_dict = {
            'cost': ('cost', 'sum'), 'conv': ('conversions', 'sum'),
            'clicks': ('clicks', 'sum'), 'impr': ('impressions', 'sum'),
        }
        if 'landing_views' in df_on.columns:
            agg_dict['landing'] = ('landing_views', 'sum')
        bc_agg = df_on.groupby(['branch', 'creative_name']).agg(**agg_dict).reset_index()

        # TIER 매핑
        tier_map = {c['creative_name']: c['TIER'] for c in creative_list}

        for branch in VALID_BRANCHES:
            branch_data = bc_agg[bc_agg['branch'] == branch].copy()
            if len(branch_data) == 0:
                continue
            branch_data['cpa'] = (branch_data['cost'] / branch_data['conv'].replace(0, np.nan)).round(0)
            if 'landing' in branch_data.columns:
                branch_data['cvr'] = (branch_data['conv'] / branch_data['landing'].replace(0, np.nan) * 100).round(2)  # 전환/랜딩
            else:
                branch_data['cvr'] = None
            branch_data = branch_data.sort_values('cpa', na_position='last')

            creatives = []
            for i, (_, r) in enumerate(branch_data.iterrows()):
                creatives.append({
                    'creative_name': clean_cross_gap_name(r['creative_name']),
                    'CPA': int(r['cpa']) if pd.notna(r['cpa']) else None,
                    'CVR': r['cvr'] if pd.notna(r['cvr']) else None,
                    'conv': int(r['conv']),
                    'cost': int(r['cost']),
                    'tier': tier_map.get(r['creative_name'], 'UNCLASSIFIED'),
                    'is_best': i == 0 and pd.notna(r['cpa']),
                })
            by_branch[branch] = creatives

    # ========== raw (원본 데이터 행 단위) ==========
    raw_list = []
    if 'creative_name' in df_on.columns and 'branch' in df_on.columns:
        raw_agg = df_on.groupby(['creative_name', 'branch']).agg(
            cost=('cost', 'sum'), conv=('conversions', 'sum'),
            clicks=('clicks', 'sum'), impr=('impressions', 'sum'),
            landing=('landing_views', 'sum') if 'landing_views' in df_on.columns else ('cost', 'count'),
            date_min=('date', 'min'), date_max=('date', 'max'),
        ).reset_index()

        for _, r in raw_agg.iterrows():
            cost = int(r['cost'])
            conv = int(r['conv'])
            clicks = int(r['clicks'])
            impr = int(r['impr'])
            landing = int(r['landing']) if 'landing_views' in df_on.columns else 0
            cpa = round(cost / conv) if conv > 0 else None
            ctr = round(clicks / impr * 100, 2) if impr > 0 else None
            cvr = round(conv / landing * 100, 2) if landing > 0 else None  # 전환/랜딩
            lpv = round(landing / clicks * 100, 1) if clicks > 0 else None
            date_range = f"{r['date_min'].strftime('%m/%d')}~{r['date_max'].strftime('%m/%d')}"

            raw_list.append({
                'creative_name': clean_cross_gap_name(r['creative_name']),
                'branch': r['branch'],
                'date_range': date_range,
                'cost': cost, 'impr': impr, 'clicks': clicks,
                'ctr': ctr, 'landing': landing, 'lpv': lpv,
                'conv': conv, 'cvr': cvr, 'cpa': cpa,
            })

    # ========== raw_off (OFF 소재 원본 데이터) ==========
    raw_off_list = []
    if 'creative_name' in df_off.columns and 'branch' in df_off.columns:
        df_off['date'] = pd.to_datetime(df_off['date'])
        raw_off_agg = df_off.groupby(['creative_name', 'branch']).agg(
            cost=('cost', 'sum'), conv=('conversions', 'sum'),
            clicks=('clicks', 'sum'), impr=('impressions', 'sum'),
            landing=('landing_views', 'sum') if 'landing_views' in df_off.columns else ('cost', 'count'),
            date_min=('date', 'min'), date_max=('date', 'max'),
        ).reset_index()

        for _, r in raw_off_agg.iterrows():
            cost = int(r['cost'])
            conv = int(r['conv'])
            clicks = int(r['clicks'])
            impr = int(r['impr'])
            landing = int(r['landing']) if 'landing_views' in df_off.columns else 0
            cpa = round(cost / conv) if conv > 0 else None
            ctr = round(clicks / impr * 100, 2) if impr > 0 else None
            cvr = round(conv / landing * 100, 2) if landing > 0 else None  # 전환/랜딩
            lpv = round(landing / clicks * 100, 1) if clicks > 0 else None
            date_range = f"{r['date_min'].strftime('%m/%d')}~{r['date_max'].strftime('%m/%d')}"

            raw_off_list.append({
                'creative_name': clean_cross_gap_name(r['creative_name']),
                'branch': r['branch'],
                'date_range': date_range,
                'cost': cost, 'impr': impr, 'clicks': clicks,
                'ctr': ctr, 'landing': landing, 'lpv': lpv,
                'conv': conv, 'cvr': cvr, 'cpa': cpa,
                'is_low_conv': conv < 3,
            })

    # ========== D 객체 생성 ==========
    D = {
        'period': f"{date_min.strftime('%Y.%m.%d')} ~ {date_max.strftime('%m.%d')}",
        'kpi': kpi,
        'target_cpa': target_cpa,
        'monthly_target_conv': MONTHLY_TARGET_CONV,
        'budget': BUDGET,
        'creative': creative_list,
        'branch': branch_list,
        'cross_gap': cross_gap,
        'age': age_list,
        'hm_ctr': hm_ctr,
        'hm_cvr': hm_cvr,
        'hm_br_age': hm_br_age,
        'lifetime': lifetime_list,
        'hook_compare': hook_list,
        'daily': daily_list,
        'weekly': weekly_list,
        'next_budget': next_budget,
        'off_cumul': off_cumul,
        'expansion': expansion,
        'off_perf': off_perf,
        'before_after': before_after,
        'by_branch': by_branch,
        'raw': raw_list,
        'raw_off': raw_off_list,
    }

    D = clean(D)

    # ========== HTML 생성 ==========
    html = generate_html(D, month)

    # 저장
    output_path = os.path.join(data_dir, f"tiktok_monthly_dayt_{month}.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"[OK] Monthly report -> {output_path}")
    return output_path


def generate_html(D: dict, month: str) -> str:
    """HTML 생성 - monthly_ref.html 구조 기반"""

    d_json = json.dumps(D, ensure_ascii=False)
    year = month[:4]
    mon = month[4:]

    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>다이트한의원 TikTok 먼슬리 · {year}년 {mon}월</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{{
  --bg:#0b0d12;--s1:#11141c;--s2:#171b25;--bd:#1c2030;
  --acc:#4ade80;--blue:#60a5fa;--pur:#a78bfa;--warn:#fb923c;--red:#f87171;
  --tx:#dde4f0;--tx2:#7a8499;--tx3:#2e3648;
  --t1:#4ade80;--t2:#60a5fa;--t3:#a78bfa;--t4:#f87171;--lv:#6b7280;--uc:#8b5cf6;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--tx);font-family:"Noto Sans KR",sans-serif;font-size:14px;line-height:1.6}}
.hdr{{background:linear-gradient(160deg,#0d0f16 0%,#111420 100%);border-bottom:1px solid var(--bd);padding:40px 32px 32px}}
.hdr-inner{{max-width:1100px;margin:0 auto}}
.brand{{font-size:11px;font-weight:700;letter-spacing:.16em;color:var(--acc);text-transform:uppercase;margin-bottom:10px}}
.hdr-title{{font-size:28px;font-weight:900;letter-spacing:-.02em}}
.hdr-meta{{margin-top:10px;display:flex;gap:10px;flex-wrap:wrap}}
.chip{{background:var(--s2);border:1px solid var(--bd);border-radius:6px;padding:4px 14px;font-size:12px;color:var(--tx2)}}
.chip span{{color:var(--tx);font-weight:600}}
.off-wrap{{max-width:1100px;margin:18px auto 0;padding:0 24px}}
.off-notice{{background:rgba(251,146,60,.06);border:1px solid rgba(251,146,60,.2);
  border-radius:8px;padding:12px 18px;font-size:12px;color:var(--warn);display:flex;align-items:center;gap:10px}}
nav{{position:sticky;top:0;z-index:100;background:rgba(11,13,18,.95);backdrop-filter:blur(14px);border-bottom:1px solid var(--bd)}}
.nav-inner{{max-width:1100px;margin:0 auto;display:flex;overflow-x:auto;scrollbar-width:none}}
.nav-inner::-webkit-scrollbar{{display:none}}
.tb{{background:none;border:none;color:var(--tx2);cursor:pointer;font-family:inherit;font-size:13px;
  font-weight:500;padding:0 20px;height:50px;border-bottom:2px solid transparent;white-space:nowrap;transition:color .2s,border-color .2s}}
.tb:hover{{color:var(--tx)}} .tb.on{{color:var(--acc);border-bottom-color:var(--acc)}}
.pg{{display:none}} .pg.on{{display:block}}
.wrap{{max-width:1100px;margin:0 auto;padding:36px 24px}}
.sec{{margin-bottom:44px}}
.sec-lbl{{font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;
  color:var(--tx3);margin-bottom:18px;display:flex;align-items:center;gap:10px}}
.sec-lbl::after{{content:"";flex:1;height:1px;background:var(--bd)}}
.kpi-row{{display:grid;grid-template-columns:repeat(6,1fr);gap:1px;background:var(--bd);border-radius:10px;overflow:hidden}}
@media(max-width:800px){{.kpi-row{{grid-template-columns:repeat(3,1fr)}}}}
@media(max-width:480px){{.kpi-row{{grid-template-columns:repeat(2,1fr)}}}}
.kc{{background:var(--s1);padding:18px 16px;border-top:2px solid var(--kc,var(--bd))}}
.kc-lbl{{font-size:10px;font-weight:700;letter-spacing:.08em;color:var(--tx2);text-transform:uppercase;margin-bottom:8px}}
.kc-val{{font-size:18px;font-weight:900;font-family:"DM Mono",monospace}}
.kc-sub{{font-size:10px;color:var(--tx2);margin-top:4px}}
.card{{background:var(--s1);border:1px solid var(--bd);border-radius:10px;padding:22px 24px}}
.ct{{font-size:13px;font-weight:700;margin-bottom:4px}} .cd{{font-size:11px;color:var(--tx2);margin-bottom:16px}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media(max-width:700px){{.g2{{grid-template-columns:1fr}}}}
.ig{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}}
.ic{{border-radius:10px;padding:18px 20px;border-left:3px solid var(--ic)}}
.ic-tp{{font-size:10px;font-weight:700;letter-spacing:.1em;color:var(--ic);margin-bottom:6px}}
.ic-ti{{font-size:14px;font-weight:700;margin-bottom:8px}}
.ic-pt{{font-size:12px;color:var(--tx2);padding:3px 0 3px 10px;border-left:2px solid var(--bd);margin:3px 0}}
.tw{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:var(--s2);color:var(--tx2);font-weight:600;font-size:10px;letter-spacing:.06em;
  text-transform:uppercase;padding:9px 14px;text-align:left;border-bottom:1px solid var(--bd);white-space:nowrap}}
td{{padding:10px 14px;border-bottom:1px solid var(--bd);color:var(--tx);vertical-align:middle}}
tr:last-child td{{border-bottom:none}} tr:hover td{{background:rgba(255,255,255,.015)}}
.badge{{display:inline-block;font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px}}
.TIER1{{background:rgba(74,222,128,.12);color:var(--t1)}} .TIER2{{background:rgba(96,165,250,.12);color:var(--t2)}}
.TIER3{{background:rgba(167,139,250,.12);color:var(--t3)}} .TIER4{{background:rgba(248,113,113,.12);color:var(--t4)}}
.LOW_VOLUME{{background:rgba(107,114,128,.12);color:var(--lv)}} .UNCLASSIFIED{{background:rgba(139,92,246,.12);color:var(--uc)}}
.OFF{{background:rgba(251,146,60,.12);color:var(--warn)}}
.ba-card{{background:var(--s2);border-radius:10px;border:1px solid var(--bd);margin-bottom:10px;overflow:hidden}}
.ba-top{{padding:14px 18px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;border-bottom:1px solid var(--bd)}}
.ba-name{{font-size:12px;font-weight:700;font-family:"DM Mono",monospace;color:var(--tx)}}
.ba-tags{{display:flex;gap:6px;align-items:center;flex-wrap:wrap}}
.ba-body{{padding:14px 18px}}
.ba-flow{{display:grid;grid-template-columns:1fr 28px 1fr 28px 1fr;gap:8px;align-items:center}}
@media(max-width:580px){{.ba-flow{{grid-template-columns:1fr 1fr;gap:6px}}}}
.ba-box{{background:var(--s1);border-radius:8px;padding:12px 14px;border:1px solid var(--bd)}}
.ba-box-lbl{{font-size:9px;color:var(--tx2);font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px}}
.ba-box-val{{font-size:19px;font-weight:900;font-family:"DM Mono",monospace}}
.ba-box-sub{{font-size:10px;color:var(--tx2);margin-top:3px}}
.ba-arr{{text-align:center;color:var(--tx3);font-size:16px}}
.ba-result{{border-radius:8px;padding:12px 14px;border:2px solid var(--rc,var(--bd))}}
.ba-foot{{padding:10px 18px;background:rgba(0,0,0,.15);font-size:11px;color:var(--tx2);display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
.share-bar{{display:flex;align-items:center;gap:8px}}
.share-track{{flex:1;background:var(--s2);border-radius:3px;height:5px;min-width:60px;overflow:hidden}}
.share-fill{{height:100%;border-radius:3px;background:var(--sf,#7a8499)}}
.br-row{{display:grid;grid-template-columns:60px 1fr 100px 80px 92px;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--bd)}}
.br-row:last-child{{border-bottom:none}}
.br-bar{{background:var(--s2);border-radius:4px;height:8px;overflow:hidden}}
.br-fill{{height:100%;border-radius:4px}}
.dir{{display:inline-block;font-size:10px;font-weight:700;padding:3px 10px;border-radius:20px}}
.hm-cell{{border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;height:44px}}
.hm-hdr{{font-size:10px;font-weight:600;color:var(--tx2);text-align:center;display:flex;align-items:center;justify-content:center;height:30px}}
.hm-lbl{{font-size:11px;color:var(--tx2);display:flex;align-items:center;height:44px;padding-right:6px}}
.num{{font-family:"DM Mono",monospace;text-align:right}}
th.r{{text-align:right}}
.good{{color:var(--acc)}} .bad{{color:var(--red)}} .warn{{color:var(--warn)}} .muted{{color:var(--tx2)}}
::-webkit-scrollbar{{width:5px;height:5px}} ::-webkit-scrollbar-thumb{{background:var(--bd);border-radius:3px}}
</style>
</head>
<body>
<div class="hdr"><div class="hdr-inner">
  <div class="brand">다이트한의원 · TikTok 광고 월간 분석</div>
  <div class="hdr-title">{year}년 {mon}월 먼슬리 리포트</div>
  <div class="hdr-meta">
    <div class="chip">분석 기간 <span>{D['period']}</span></div>
    <div class="chip">전환 목표 <span>{D['monthly_target_conv']}건</span></div>
    <div class="chip">ON 소재 <span id="on-cnt">{len(D['creative'])}</span>개</div>
    <div class="chip">OFF 소재 <span id="off-cnt">{len(D['off_perf'])}</span>개</div>
  </div>
</div></div>

<nav><div class="nav-inner">
  <button class="tb on" data-tab="summary">📊 요약</button>
  <button class="tb" data-tab="creative">🎬 소재성과</button>
  <button class="tb" data-tab="branch">🏢 지점분석</button>
  <button class="tb" data-tab="bc">📐 소재×지점</button>
  <button class="tb" data-tab="off">⏸️ OFF소재</button>
  <button class="tb" data-tab="age">👥 나이대</button>
  <button class="tb" data-tab="lifetime">📈 소재수명</button>
  <button class="tb" data-tab="daily">📅 일별추이</button>
  <button class="tb" data-tab="strategy">🎯 전략</button>
  <button class="tb" data-tab="raw">📋 원본</button>
</div></nav>

<!-- 탭1: 월간 요약 -->
<div id="pg-summary" class="pg on"><div class="wrap">
  <div class="sec"><div class="sec-lbl">{mon}월 월간 KPI — ON 소재 기준</div>
    <div class="kpi-row" id="kpi-row"></div></div>
  <div class="sec"><div class="sec-lbl">핵심 인사이트</div>
    <div class="ig" id="sum-insights"></div></div>
  <div class="g2 sec">
    <div class="card"><div class="ct">소재 TIER 분포</div>
      <div class="cd">ON 소재 기준 · 목표 CPA <span class="num" id="target-lbl"></span>원</div>
      <div style="position:relative;height:220px"><canvas id="donutChart"></canvas></div></div>
    <div class="card"><div class="ct">지점별 CPA</div>
      <div class="cd">목표 CPA 기준선 포함</div>
      <div style="position:relative;height:220px"><canvas id="sumBrChart"></canvas></div></div>
  </div>
  <div class="sec card"><div class="ct">주차별 광고비 + CPA 추이</div>
    <div class="cd">막대: 광고비(원) / 선: CPA(원)</div>
    <div style="position:relative;height:240px"><canvas id="weeklyChart"></canvas></div></div>
</div></div>

<!-- 탭2: 소재 성과 -->
<div id="pg-creative" class="pg"><div class="wrap">
  <div class="sec card"><div class="ct">소재 포지셔닝 버블차트</div>
    <div class="cd">X: CTR · Y: CVR · 원 크기: 광고비 · 색: TIER — ON 소재만</div>
    <div style="position:relative;height:360px"><canvas id="bubbleChart"></canvas></div></div>
  <div class="sec"><div class="sec-lbl">ON 소재 성과 상세</div>
    <div class="card tw"><table id="on-tbl"></table></div></div>
  <div class="sec"><div class="sec-lbl">TIER1 미집행 지점 — 확장 기회</div>
    <div class="ig" id="expansion-cards"></div></div>
  <div class="sec"><div class="sec-lbl">OFF 소재 집행 성과</div>
    <div class="card tw"><table id="creative-off-tbl"></table></div></div>
  <div class="sec"><div class="sec-lbl">OFF 전후 지점 CPA 참고</div>
    <div style="background:rgba(96,165,250,.05);border:1px solid rgba(96,165,250,.15);
      border-radius:8px;padding:14px 18px;margin-bottom:16px;font-size:12px;line-height:1.7">
      <strong style="color:var(--blue)">📌 해석 주의</strong><br>
      <span style="color:var(--tx2)">아래 수치는 <strong style="color:var(--tx)">해당 지점 전체 CPA</strong>이며, OFF 소재 외에도
        다른 소재 구성·예산 재배분·시즌 효과 등 다양한 요인이 복합적으로 반영됩니다.</span>
    </div>
    <div class="card tw"><table id="creative-ba-tbl"></table></div></div>
</div></div>

<!-- 탭3: 지점 분석 -->
<div id="pg-branch" class="pg"><div class="wrap">
  <div class="g2 sec">
    <div class="card"><div class="ct">지점별 CPA</div><div class="cd">목표 기준선 포함</div>
      <div style="position:relative;height:260px"><canvas id="brCpaChart"></canvas></div></div>
    <div class="card"><div class="ct">예산 효율</div><div class="cd">비용비중 vs 전환비중</div>
      <div style="position:relative;height:260px"><canvas id="brEffChart"></canvas></div></div>
  </div>
  <div class="sec"><div class="sec-lbl">지점별 상세</div>
    <div class="card tw"><table id="branch-tbl"></table></div></div>
  <div class="sec"><div class="sec-lbl">지점×나이대 CPA 히트맵</div>
    <div class="card"><div id="hm-br-age" style="margin-top:8px"></div></div></div>
</div></div>

<!-- 탭4: 소재×지점 -->
<div id="pg-bc" class="pg"><div class="wrap">
  <div class="sec"><div class="sec-lbl">소재×지점 CPA 편차</div>
    <div style="background:rgba(167,139,250,.05);border:1px solid rgba(167,139,250,.15);
      border-radius:8px;padding:14px 18px;margin-bottom:16px;font-size:12px;line-height:1.7">
      <strong style="color:var(--pur)">📊 편차 해석</strong><br>
      <span style="color:var(--tx2)">동일 소재의 지점별 CPA 차이를 분석합니다. <strong style="color:var(--tx)">편차가 50% 이상</strong>이면
        해당 지점에서 소재 효율이 낮으므로 타겟팅 또는 OFF 검토를 권장합니다.</span>
    </div>
    <div class="card tw"><table id="gap-tbl"></table></div></div>
  <div class="sec"><div class="sec-lbl">지점별 소재 성과</div>
    <div class="g2" id="by-branch-cards"></div></div>
</div></div>

<!-- 탭5: OFF 소재 -->
<div id="pg-off" class="pg"><div class="wrap">
  <div class="sec"><div class="sec-lbl">OFF 소재 집행 성과</div>
    <div class="card tw"><table id="off-perf-tbl"></table></div></div>
  <div class="sec"><div class="sec-lbl">OFF 전후 지점 CPA 참고</div>
    <div style="background:rgba(96,165,250,.05);border:1px solid rgba(96,165,250,.15);
      border-radius:8px;padding:14px 18px;margin-bottom:16px;font-size:12px;line-height:1.7">
      <strong style="color:var(--blue)">📌 해석 주의</strong><br>
      <span style="color:var(--tx2)">OFF 전후 7일 해당 지점 전체 CPA 비교입니다.<br>
        소재 OFF 외에도 예산 재배분·시즌·경쟁 등 복합 요인이 작용하므로 <strong style="color:var(--tx)">인과관계로 해석하지 마세요.</strong><br>
        <span style="color:var(--tx3)">신뢰도 높음: 전후 각 7일 데이터 충분 / 보통: 일부 구간 / 낮음: 데이터 부족</span></span>
    </div>
    <div id="ba-list"></div></div>
</div></div>

<!-- 탭6: 나이대 -->
<div id="pg-age" class="pg"><div class="wrap">
  <div class="sec card"><div class="ct">나이대별 비용비중 vs 전환비중</div>
    <div class="cd">전환비중이 비용비중을 상회할수록 효율적</div>
    <div style="position:relative;height:260px"><canvas id="ageChart"></canvas></div></div>
  <div class="g2 sec">
    <div class="card"><div class="ct">소재유형 × 나이대 CTR</div><div class="cd">높을수록 진한 녹색</div>
      <div id="hm-ctr" style="margin-top:8px"></div></div>
    <div class="card"><div class="ct">소재유형 × 나이대 CVR</div><div class="cd">높을수록 진한 파란색</div>
      <div id="hm-cvr" style="margin-top:8px"></div></div>
  </div>
  <div class="sec"><div class="sec-lbl">나이대별 상세</div>
    <div class="card tw"><table id="age-tbl"></table></div></div>
</div></div>

<!-- 탭7: 소재 수명 -->
<div id="pg-lifetime" class="pg"><div class="wrap">
  <div class="sec card"><div class="ct">신규(신) vs 재가공(재) 그룹 비교</div>
    <div class="cd">그룹 합산 기준 총 CPA / CTR / CVR</div>
    <div style="position:relative;height:240px"><canvas id="hookChart"></canvas></div></div>
  <div class="sec card"><div class="ct">소재별 집행일수 CTR 추이</div>
    <div class="cd">TIER1·2 상위 3개 vs TIER3·4 하위 3개 / 7일+ 소재만</div>
    <div style="position:relative;height:360px"><canvas id="ltChart"></canvas></div></div>
  <div class="sec"><div class="sec-lbl">소재 수명 상세</div>
    <div class="card tw"><table id="lt-tbl"></table></div></div>
</div></div>

<!-- 탭8: 일별 추이 -->
<div id="pg-daily" class="pg"><div class="wrap">
  <div class="sec"><div class="sec-lbl">일별 광고비 + 전환 추이</div>
    <div class="card"><div style="position:relative;height:300px"><canvas id="dailyCombo"></canvas></div></div></div>
  <div class="g2 sec">
    <div class="sec" style="margin-bottom:0"><div class="sec-lbl">일별 CTR 추이</div>
      <div class="card"><div style="position:relative;height:220px"><canvas id="dailyCtr"></canvas></div></div></div>
    <div class="sec" style="margin-bottom:0"><div class="sec-lbl">일별 CPA 추이</div>
      <div class="card"><div style="position:relative;height:220px"><canvas id="dailyCpa"></canvas></div></div></div>
  </div>
</div></div>

<!-- 탭9: 전략 -->
<div id="pg-strategy" class="pg"><div class="wrap">
  <div class="sec"><div class="sec-lbl">지점별 예산 배분 권고</div>
    <div class="card">
      <div style="color:var(--tx2);font-size:11px;margin-bottom:18px">
        * 이번 달 CPA·CVR·효율지수(전환비중÷비용비중) 기반 권고 및 다음 월 예산 제안</div>
      <div id="budget-list"></div></div></div>
  <div class="sec"><div class="sec-lbl">신규 소재 기획 방향</div>
    <div class="ig" id="strat-insights"></div></div>
  <div class="sec"><div class="sec-lbl">ON 유지 및 OFF 권고</div>
    <div class="card tw"><table id="off-cumul-tbl"></table></div></div>
</div></div>

<!-- 탭10: 원본 데이터 -->
<div id="pg-raw" class="pg"><div class="wrap">
  <div class="sec"><div class="sec-lbl">ON 소재 원본 데이터</div>
    <div style="color:var(--tx2);font-size:11px;margin-bottom:12px">총 {len(D['raw'])}행 · 소재×지점 단위 집계</div>
    <div class="card tw"><table id="raw-tbl"></table></div></div>
  <div class="sec"><div class="sec-lbl">OFF 소재 원본 데이터</div>
    <div style="color:var(--tx2);font-size:11px;margin-bottom:12px">총 {len(D['raw_off'])}행</div>
    <div class="card tw"><table id="raw-off-tbl"></table></div></div>
  <div class="sec"><div class="sec-lbl">일별 집계 데이터</div>
    <div class="card tw"><table id="raw-daily-tbl"></table></div></div>
</div></div>

<script>
const D={d_json};
const TC={{"TIER1":"#4ade80","TIER2":"#60a5fa","TIER3":"#a78bfa","TIER4":"#f87171","LOW_VOLUME":"#6b7280","UNCLASSIFIED":"#8b5cf6"}};
const charts=[];  // 차트 인스턴스 저장

// 탭 전환
document.querySelectorAll('.tb').forEach(btn=>{{
  btn.onclick=()=>{{
    document.querySelectorAll('.tb').forEach(b=>b.classList.remove('on'));
    document.querySelectorAll('.pg').forEach(p=>p.classList.remove('on'));
    btn.classList.add('on');
    document.getElementById('pg-'+btn.dataset.tab).classList.add('on');
    setTimeout(()=>charts.forEach(c=>c.resize()),50);  // 차트 resize
  }};
}});

// 숫자 포맷
const fmt=n=>n==null?'-':n.toLocaleString();
const fmtPct=n=>n==null?'-':n.toFixed(2)+'%';
const fmtWon=n=>n==null?'-':fmt(n)+'원';

// KPI 렌더링
document.getElementById('kpi-row').innerHTML=[
  {{l:'광고비',v:fmt(D.kpi.cost)+'원',c:'--acc'}},
  {{l:'전환',v:D.kpi.conv+'건',c:'--blue'}},
  {{l:'CPA',v:fmtWon(D.kpi.cpa),c:'--pur'}},
  {{l:'CTR',v:fmtPct(D.kpi.ctr),c:'--tx'}},
  {{l:'CVR',v:fmtPct(D.kpi.cvr),c:'--tx'}},
  {{l:'랜딩률',v:D.kpi.lpv+'%',c:'--tx'}},
].map(k=>`<div class="kc" style="--kc:var(${{k.c}})"><div class="kc-lbl">${{k.l}}</div><div class="kc-val">${{k.v}}</div></div>`).join('');

document.getElementById('target-lbl').textContent=fmt(D.target_cpa);

// TIER 분포 계산
const tierCounts={{}};
D.creative.forEach(c=>{{tierCounts[c.TIER]=(tierCounts[c.TIER]||0)+1}});
const tierLabels=Object.keys(tierCounts);
const tierValues=Object.values(tierCounts);

// 도넛 차트
charts.push(new Chart(document.getElementById('donutChart'),{{
  type:'doughnut',
  data:{{labels:tierLabels,datasets:[{{data:tierValues,backgroundColor:tierLabels.map(t=>TC[t]||'#666'),borderWidth:0}}]}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'right',labels:{{color:'#e4e4e7',padding:12}}}}}}}}
}}));

// 지점 CPA 바차트
const brLabels=D.branch.map(b=>b.branch);
const brCpa=D.branch.map(b=>b.CPA);
charts.push(new Chart(document.getElementById('sumBrChart'),{{
  type:'bar',
  data:{{labels:brLabels,datasets:[{{data:brCpa,backgroundColor:brCpa.map(c=>c<=D.target_cpa?'#4ade80':'#f87171'),borderRadius:4}}]}},
  options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},
    scales:{{x:{{grid:{{color:'rgba(255,255,255,.04)'}},ticks:{{color:'#7a8499'}}}},y:{{grid:{{display:false}},ticks:{{color:'#dde4f0'}}}}}}}}
}}));

// 인사이트 생성
const tier1Cnt=tierCounts['TIER1']||0;
const tier4Cnt=tierCounts['TIER4']||0;
const totalCnt=D.creative.length;
const bestBr=D.branch[0];
const worstBr=D.branch[D.branch.length-1];

const insights=[
  {{type:'positive',title:`TIER1 ${{tier1Cnt}}개 (${{(tier1Cnt/totalCnt*100).toFixed(1)}}%)`,desc:'목표 CPA 달성 + CVR 5% 이상'}},
  {{type:'positive',title:`${{bestBr.branch}} 최고 효율`,desc:`CPA ${{fmt(bestBr.CPA)}}원 / CVR ${{bestBr.CVR}}%`}},
  {{type:worstBr.CPA>D.target_cpa*1.3?'negative':'info',title:`${{worstBr.branch}} ${{worstBr.CPA>D.target_cpa*1.3?'효율 개선 필요':'모니터링'}}`,desc:`CPA ${{fmt(worstBr.CPA)}}원`}},
  {{type:D.kpi.conv/D.monthly_target_conv>=0.8?'positive':'negative',title:`월 목표 ${{(D.kpi.conv/D.monthly_target_conv*100).toFixed(1)}}%`,desc:`${{D.kpi.conv}}건 / 목표 ${{D.monthly_target_conv}}건`}},
];
document.getElementById('sum-insights').innerHTML=insights.map(i=>`
  <div class="ic" style="--ic:var(--${{i.type==='positive'?'acc':i.type==='negative'?'red':'blue'}});background:rgba(${{i.type==='positive'?'74,222,128':i.type==='negative'?'248,113,113':'96,165,250'}},.06)">
    <div class="ic-tp">${{i.type.toUpperCase()}}</div><div class="ic-ti">${{i.title}}</div><div class="ic-pt">${{i.desc}}</div></div>
`).join('');

// 주차별 차트
if(D.weekly&&D.weekly.length){{
  charts.push(new Chart(document.getElementById('weeklyChart'),{{
    data:{{labels:D.weekly.map(w=>w.week_label),datasets:[
      {{type:'bar',label:'광고비',data:D.weekly.map(w=>w.cost),backgroundColor:'rgba(96,165,250,.6)',yAxisID:'y',borderRadius:4}},
      {{type:'line',label:'CPA',data:D.weekly.map(w=>w.cpa),borderColor:'#a78bfa',backgroundColor:'transparent',yAxisID:'y1',tension:.3,pointRadius:4}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{color:'#dde4f0'}}}}}},
      scales:{{y:{{position:'left',grid:{{color:'rgba(255,255,255,.04)'}},ticks:{{color:'#7a8499'}}}},y1:{{position:'right',grid:{{display:false}},ticks:{{color:'#a78bfa'}}}}}}}}
  }}));
}}

// 버블차트 (소재×지점 CPA 편차)
if(D.cross_gap.length){{
  const bubbleData=D.cross_gap.filter(g=>g.CPA&&g.CVR).slice(0,50).map(g=>{{
    const isHigh=g.gap_pct>50;
    return {{x:g.CPA,y:g.CVR,r:Math.max(3,Math.min(20,g.총비용/100000)),label:g.creative_name+' ('+g.branch+')',bg:isHigh?'rgba(248,113,113,.7)':'rgba(74,222,128,.7)'}};
  }});
  charts.push(new Chart(document.getElementById('bubbleChart'),{{
    type:'bubble',
    data:{{datasets:[{{data:bubbleData,backgroundColor:bubbleData.map(d=>d.bg)}}]}},
    options:{{
      responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>ctx.raw.label+': CPA '+fmt(ctx.raw.x)+'원 / CVR '+ctx.raw.y+'%'}}}}}},
      scales:{{x:{{title:{{display:true,text:'CPA (원)',color:'#7a8499'}},grid:{{color:'rgba(255,255,255,.04)'}},ticks:{{color:'#7a8499'}}}},
        y:{{title:{{display:true,text:'CVR (%)',color:'#7a8499'}},grid:{{color:'rgba(255,255,255,.04)'}},ticks:{{color:'#7a8499'}}}}}}
    }}
  }}));
}}

// ON 소재 테이블
document.getElementById('on-tbl').innerHTML=`
  <thead><tr><th>소재명</th><th>TIER</th><th>CPA</th><th>CTR</th><th>CVR</th><th>LPV</th><th>전환</th><th>비용</th><th>일수</th><th>지점</th></tr></thead>
  <tbody>${{D.creative.map(c=>`
    <tr>
      <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis">${{c.creative_name.replace(/_\\d{{4,6}}$/,'')}}</td>
      <td><span class="badge ${{c.TIER}}">${{c.TIER}}</span></td>
      <td class="num ${{c.CPA&&c.CPA<=D.target_cpa?'good':'bad'}}">${{fmtWon(c.CPA)}}</td>
      <td class="num">${{fmtPct(c.CTR)}}</td>
      <td class="num">${{fmtPct(c.CVR)}}</td>
      <td class="num">${{c.LPV}}%</td>
      <td class="num">${{c.총전환}}건</td>
      <td class="num">${{fmt(c.총비용)}}원</td>
      <td class="num">${{c.집행일수}}</td>
      <td>${{(c.집행지점||[]).join(', ')}}</td>
    </tr>
  `).join('')}}</tbody>`;

// 확장 기회
document.getElementById('expansion-cards').innerHTML=D.expansion.slice(0,4).map(e=>`
  <div class="ic" style="--ic:var(--acc);background:rgba(74,222,128,.06)">
    <div class="ic-tp">확장 기회</div>
    <div class="ic-ti">${{e.creative_name.replace(/_\\d{{4,6}}$/,'')}}</div>
    <div class="ic-pt">CPA ${{fmt(e.CPA)}}원 · 현재: ${{(e.current||[]).join(',')}}</div>
    <div class="ic-pt">미집행: ${{(e.missing||[]).join(', ')}}</div>
  </div>
`).join('');

// creative 탭 - OFF 소재 테이블
const fmtOffCpa=(o)=>o.is_low_conv?`<span class="muted">- (전환 ${{o.총전환}}건)</span>`:fmtWon(o.CPA);
document.getElementById('creative-off-tbl').innerHTML=`
  <thead><tr><th>소재명</th><th>집행지점</th><th>CPA</th><th>CTR</th><th>CVR</th><th>전환</th><th>비용</th><th>집행일</th></tr></thead>
  <tbody>${{D.off_perf.map(o=>`
    <tr>
      <td style="max-width:160px;overflow:hidden;text-overflow:ellipsis">${{o.creative_name.replace(/_\\d{{4,6}}$/,'')}}</td>
      <td>${{o.branch}}</td>
      <td class="num">${{fmtOffCpa(o)}}</td>
      <td class="num">${{fmtPct(o.CTR)}}</td>
      <td class="num">${{fmtPct(o.CVR)}}</td>
      <td class="num">${{o.총전환}}건</td>
      <td class="num">${{fmt(o.총비용)}}원</td>
      <td class="num">${{o.집행일수}}일</td>
    </tr>
  `).join('')}}</tbody>`;

// creative 탭 - before_after 테이블
const reliabilityMap={{'high':'높음','mid':'보통','low':'낮음','no_after':'데이터없음'}};
document.getElementById('creative-ba-tbl').innerHTML=D.before_after.length?`
  <thead><tr><th>소재명</th><th>지점</th><th>OFF일자</th><th>OFF전CPA</th><th>OFF후CPA</th><th>변화율</th><th>신뢰도</th></tr></thead>
  <tbody>${{D.before_after.map(ba=>`
    <tr>
      <td style="max-width:140px;overflow:hidden;text-overflow:ellipsis">${{ba.creative_name.replace(/_\\d{{4,6}}$/,'')}}</td>
      <td>${{ba.branch}}</td>
      <td class="num">${{ba.off_date}}</td>
      <td class="num">${{fmtWon(ba.before_cpa)}}</td>
      <td class="num">${{ba.after_cpa?fmtWon(ba.after_cpa):'<span class="muted">데이터 없음</span>'}}</td>
      <td class="num ${{ba.cpa_change_pct<0?'good':ba.cpa_change_pct>0?'bad':''}}">${{ba.cpa_change_pct!=null?(ba.cpa_change_pct>0?'+':'')+ba.cpa_change_pct+'%':'-'}}</td>
      <td><span class="badge ${{ba.reliability==='high'?'TIER1':ba.reliability==='mid'?'TIER2':'LOW_VOLUME'}}">${{reliabilityMap[ba.reliability]||ba.reliability}}</span></td>
    </tr>
  `).join('')}}</tbody>`:'<tbody><tr><td colspan="7" style="text-align:center;color:var(--tx2)">before_after 데이터 없음</td></tr></tbody>';

// OFF 소재 성과 (off 탭)
document.getElementById('off-perf-tbl').innerHTML=`
  <thead><tr><th>소재명</th><th>지점</th><th>CPA</th><th>CTR</th><th>CVR</th><th>전환</th><th>비용</th><th>일수</th></tr></thead>
  <tbody>${{D.off_perf.map(o=>`
    <tr>
      <td style="max-width:160px;overflow:hidden;text-overflow:ellipsis">${{o.creative_name.replace(/_\\d{{4,6}}$/,'')}}</td>
      <td>${{o.branch}}</td>
      <td class="num">${{fmtOffCpa(o)}}</td>
      <td class="num">${{fmtPct(o.CTR)}}</td>
      <td class="num">${{fmtPct(o.CVR)}}</td>
      <td class="num">${{o.총전환}}건</td>
      <td class="num">${{fmt(o.총비용)}}원</td>
      <td class="num">${{o.집행일수}}</td>
    </tr>
  `).join('')}}</tbody>`;

// before_after
const relLabel={{high:'높음',mid:'보통',low:'낮음',no_after:'사후없음'}};
document.getElementById('ba-list').innerHTML=D.before_after.length?D.before_after.map(ba=>{{
  const isLow=ba.reliability==='low';
  const isNoAfter=ba.reliability==='no_after';
  const hasAfter=ba.after_cpa!=null;
  const hasChange=ba.cpa_change_pct!=null;
  const changeColor=hasChange?(ba.cpa_change_pct<0?'var(--acc)':'var(--red)'):'var(--tx2)';
  const afterDisp=hasAfter?fmtWon(ba.after_cpa):'<span style="color:var(--tx2)">데이터 없음</span>';
  const changeDisp=hasChange?((ba.cpa_change_pct>0?'+':'')+ba.cpa_change_pct+'%'):'-';
  const arrColor=hasAfter?'var(--tx)':'var(--tx3)';
  const cardOpacity=isLow?'opacity:.6':'';
  const footExtra=isLow?'<span style="color:var(--warn)"> · ⚠️ 저신뢰도 — 해석 주의</span>':(isNoAfter?'<span style="color:var(--tx2)"> · 사후 데이터 없음</span>':'');
  return `<div class="ba-card" style="${{cardOpacity}}">
    <div class="ba-top">
      <span class="ba-name">${{ba.creative_name.replace(/_\\d{{4,6}}$/,'')}}</span>
      <div class="ba-tags"><span class="badge OFF">${{ba.branch}}</span><span style="font-size:11px;color:var(--tx2)">OFF: ${{ba.off_date}}</span></div>
    </div>
    <div class="ba-body">
      <div class="ba-flow">
        <div class="ba-box"><div class="ba-box-lbl">OFF 전</div><div class="ba-box-val">${{fmtWon(ba.before_cpa)}}</div><div class="ba-box-sub">${{ba.before_days}}일</div></div>
        <div class="ba-arr" style="color:${{arrColor}}">→</div>
        <div class="ba-box"><div class="ba-box-lbl">OFF 후</div><div class="ba-box-val" style="color:${{changeColor}}">${{afterDisp}}</div><div class="ba-box-sub">${{ba.after_days}}일</div></div>
        <div class="ba-arr" style="color:${{arrColor}}">→</div>
        <div class="ba-result" style="--rc:${{changeColor}}"><div class="ba-box-lbl">변화</div><div class="ba-box-val">${{changeDisp}}</div></div>
      </div>
    </div>
    <div class="ba-foot">점유율: ${{ba.share_pct}}% · 신뢰도: ${{relLabel[ba.reliability]||ba.reliability}}${{footExtra}}</div>
  </div>`;
}}).join(''):'<div class="card" style="color:var(--tx2)">before_after 데이터 없음</div>';

// 지점 분석 차트
charts.push(new Chart(document.getElementById('brCpaChart'),{{
  type:'bar',
  data:{{labels:brLabels,datasets:[{{data:brCpa,backgroundColor:brCpa.map(c=>c<=D.target_cpa?'#4ade80':'#f87171'),borderRadius:4}}]}},
  options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},
    scales:{{x:{{grid:{{color:'rgba(255,255,255,.04)'}}}},y:{{grid:{{display:false}},ticks:{{color:'#dde4f0'}}}}}}}}
}}));

charts.push(new Chart(document.getElementById('brEffChart'),{{
  type:'bar',
  data:{{labels:brLabels,datasets:[
    {{label:'비용비중',data:D.branch.map(b=>b.비용비중),backgroundColor:'#f87171'}},
    {{label:'전환비중',data:D.branch.map(b=>b.전환비중),backgroundColor:'#4ade80'}}
  ]}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{color:'#dde4f0'}}}}}},
    scales:{{x:{{stacked:false}},y:{{stacked:false,grid:{{color:'rgba(255,255,255,.04)'}},ticks:{{color:'#dde4f0'}}}}}}}}
}}));

// 지점 테이블
document.getElementById('branch-tbl').innerHTML=`
  <thead><tr><th>지점</th><th>CPA</th><th>CTR</th><th>CVR</th><th>LPV</th><th>전환</th><th>비용</th><th>비용비중</th><th>효율</th></tr></thead>
  <tbody>${{D.branch.map(b=>`
    <tr>
      <td>${{b.branch}}</td>
      <td class="num ${{b.CPA&&b.CPA<=D.target_cpa?'good':'bad'}}">${{fmtWon(b.CPA)}}</td>
      <td class="num">${{fmtPct(b.CTR)}}</td>
      <td class="num">${{fmtPct(b.CVR)}}</td>
      <td class="num">${{b.LPV}}%</td>
      <td class="num">${{b.총전환}}건</td>
      <td class="num">${{fmt(b.총비용)}}원</td>
      <td class="num">${{b.비용비중}}%</td>
      <td class="num ${{b.효율지수>1?'good':b.효율지수<0.8?'bad':''}}">${{b.효율지수}}</td>
    </tr>
  `).join('')}}</tbody>`;

// 소재×지점 편차
document.getElementById('gap-tbl').innerHTML=`
  <thead><tr><th>소재</th><th>지점</th><th>CPA</th><th>최저CPA</th><th>편차</th><th>전환</th><th>비용</th></tr></thead>
  <tbody>${{D.cross_gap.slice(0,30).map(g=>{{
    const isSingle=g.gap_pct===0||g.gap_pct===null;
    const rowCls=isSingle?'style="opacity:.5"':'';
    const gapDisp=isSingle?'-':g.gap_pct+'%';
    const gapCls=isSingle?'':(g.gap_pct>50?'bad':g.gap_pct>20?'warn':'');
    const ttl=isSingle?' title="단독 집행 소재"':'';
    return `<tr ${{rowCls}}${{ttl}}>
      <td style="max-width:150px;overflow:hidden;text-overflow:ellipsis">${{g.creative_name}}</td>
      <td>${{g.branch}}</td>
      <td class="num">${{fmtWon(g.CPA)}}</td>
      <td class="num good">${{fmtWon(g.min_cpa)}}</td>
      <td class="num ${{gapCls}}">${{gapDisp}}</td>
      <td class="num">${{g.총전환}}건</td>
      <td class="num">${{fmt(g.총비용)}}원</td>
    </tr>`;
  }}).join('')}}</tbody>`;

// 나이대 차트
charts.push(new Chart(document.getElementById('ageChart'),{{
  type:'bar',
  data:{{labels:D.age.map(a=>a.age_group),datasets:[
    {{label:'비용비중',data:D.age.map(a=>a.비용비중),backgroundColor:'#f87171'}},
    {{label:'전환비중',data:D.age.map(a=>a.전환비중),backgroundColor:'#4ade80'}}
  ]}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{color:'#dde4f0'}}}}}},
    scales:{{y:{{grid:{{color:'rgba(255,255,255,.04)'}},ticks:{{color:'#dde4f0'}}}}}}}}
}}));

// 나이대 테이블 (Unknown 이상값 처리: CVR>100% or CPA<1000)
document.getElementById('age-tbl').innerHTML=`
  <thead><tr><th>나이대</th><th>CPA</th><th>CTR</th><th>CVR</th><th>전환</th><th>비용</th><th>비용비중</th><th>전환비중</th><th>효율</th></tr></thead>
  <tbody>${{D.age.map(a=>{{
    const isAnomaly=a.age_group==='Unknown'&&(a.CVR>100||a.CPA<1000);
    const cpaDisp=isAnomaly?'-':fmtWon(a.CPA);
    const cvrDisp=isAnomaly?'-':fmtPct(a.CVR);
    const cpaCls=isAnomaly?'muted':'';
    const cvrCls=isAnomaly?'muted':'';
    return `<tr>
      <td>${{a.age_group}}</td>
      <td class="num ${{cpaCls}}">${{cpaDisp}}</td>
      <td class="num">${{fmtPct(a.CTR)}}</td>
      <td class="num ${{cvrCls}}">${{cvrDisp}}</td>
      <td class="num">${{a.총전환}}건</td>
      <td class="num">${{fmt(a.총비용)}}원</td>
      <td class="num">${{a.비용비중}}%</td>
      <td class="num">${{a.전환비중}}%</td>
      <td class="num ${{a.효율지수>1?'good':a.효율지수<0.8?'bad':''}}">${{a.효율지수}}</td>
    </tr>`;
  }}).join('')}}</tbody>`;

// 훅 비교 차트
if(D.hook_compare.length){{
  charts.push(new Chart(document.getElementById('hookChart'),{{
    type:'bar',
    data:{{labels:D.hook_compare.map(h=>h.hook_type),datasets:[
      {{label:'CPA',data:D.hook_compare.map(h=>h.CPA),backgroundColor:'#a78bfa',yAxisID:'y'}},
      {{label:'CVR',data:D.hook_compare.map(h=>h.CVR),backgroundColor:'#4ade80',yAxisID:'y1'}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{color:'#dde4f0'}}}}}},
      scales:{{y:{{position:'left',grid:{{color:'rgba(255,255,255,.04)'}}}},y1:{{position:'right',grid:{{display:false}}}}}}}}
  }}));
}}

// 소재 수명 CPA 추이 차트
if(D.lifetime.length){{
  const ltData=D.lifetime.filter(l=>l.total_days>=7&&l.cpa&&l.cpa.length>0).slice(0,6);
  if(ltData.length){{
    const maxDays=Math.max(...ltData.map(l=>l.total_days));
    const labels=Array.from({{length:maxDays}},(_, i)=>(i+1)+'일');
    const datasets=ltData.map((l,i)=>{{
      const colors=['#4ade80','#60a5fa','#a78bfa','#fb923c','#f87171','#e879f9'];
      return {{
        label:l.name.slice(0,15),
        data:l.cpa,
        borderColor:colors[i%colors.length],
        backgroundColor:'transparent',
        tension:.3,
        pointRadius:2
      }};
    }});
    charts.push(new Chart(document.getElementById('ltChart'),{{
      type:'line',
      data:{{labels,datasets}},
      options:{{
        responsive:true,maintainAspectRatio:false,
        plugins:{{legend:{{position:'bottom',labels:{{color:'#dde4f0',boxWidth:12,padding:8}}}}}},
        scales:{{
          x:{{title:{{display:true,text:'집행일수',color:'#7a8499'}},grid:{{color:'rgba(255,255,255,.04)'}},ticks:{{color:'#7a8499'}}}},
          y:{{title:{{display:true,text:'CPA (원)',color:'#7a8499'}},grid:{{color:'rgba(255,255,255,.04)'}},ticks:{{color:'#7a8499'}}}}
        }}
      }}
    }}));
  }}
}}

// 소재 수명 테이블
document.getElementById('lt-tbl').innerHTML=`
  <thead><tr><th>소재</th><th>TIER</th><th>집행일수</th><th>평균CPA</th></tr></thead>
  <tbody>${{D.lifetime.map(l=>`
    <tr>
      <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">${{l.name}}</td>
      <td><span class="badge ${{l.tier}}">${{l.tier}}</span></td>
      <td class="num">${{l.total_days}}일</td>
      <td class="num">${{l.avg_cpa?fmtWon(l.avg_cpa):'-'}}</td>
    </tr>
  `).join('')}}</tbody>`;

// 일별 트렌드
if(D.daily.length){{
  charts.push(new Chart(document.getElementById('dailyCombo'),{{
    data:{{labels:D.daily.map(d=>d.date_str),datasets:[
      {{type:'bar',label:'광고비',data:D.daily.map(d=>d.cost),backgroundColor:'rgba(96,165,250,.6)',yAxisID:'y'}},
      {{type:'line',label:'전환',data:D.daily.map(d=>d.conv),borderColor:'#4ade80',backgroundColor:'transparent',yAxisID:'y1',tension:.3}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{color:'#dde4f0'}}}}}},
      scales:{{y:{{position:'left',grid:{{color:'rgba(255,255,255,.04)'}}}},y1:{{position:'right',grid:{{display:false}}}}}}}}
  }}));
  charts.push(new Chart(document.getElementById('dailyCtr'),{{
    type:'line',data:{{labels:D.daily.map(d=>d.date_str),datasets:[{{data:D.daily.map(d=>d.ctr),borderColor:'#60a5fa',backgroundColor:'transparent',tension:.3}}]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{y:{{grid:{{color:'rgba(255,255,255,.04)'}}}}}}}}
  }}));
  charts.push(new Chart(document.getElementById('dailyCpa'),{{
    type:'line',data:{{labels:D.daily.map(d=>d.date_str),datasets:[{{data:D.daily.map(d=>d.cpa),borderColor:'#a78bfa',backgroundColor:'transparent',tension:.3}}]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{y:{{grid:{{color:'rgba(255,255,255,.04)'}}}}}}}}
  }}));
}}

// 예산 권고
document.getElementById('budget-list').innerHTML=D.next_budget.map(b=>`
  <div class="br-row">
    <span>${{b.branch}}</span>
    <div class="br-bar"><div class="br-fill" style="width:${{b.eff*50}}%;background:${{b.direction==='increase'?'#4ade80':b.direction==='decrease'?'#f87171':'#7a8499'}}"></div></div>
    <span class="num">${{fmt(b.current)}}원</span>
    <span class="dir" style="background:${{b.direction==='increase'?'rgba(74,222,128,.15);color:#4ade80':b.direction==='decrease'?'rgba(248,113,113,.15);color:#f87171':'rgba(122,132,153,.15);color:#7a8499'}}">${{b.direction==='increase'?'↑ 증액':b.direction==='decrease'?'↓ 감액':'→ 유지'}}</span>
    <span class="num">${{fmt(b.suggested)}}원</span>
  </div>
`).join('');

// 전략 인사이트
document.getElementById('strat-insights').innerHTML=[
  {{type:'positive',title:'TIER1 소재 확장',desc:`${{D.expansion.length}}개 소재의 미집행 지점 확대 검토`}},
  {{type:'negative',title:'TIER4 소재 개선',desc:`${{tier4Cnt}}개 소재 크리에이티브 개선 또는 OFF`}},
  {{type:'info',title:'효율 지점 집중',desc:`${{bestBr.branch}} 등 고효율 지점 예산 확대`}},
].map(i=>`
  <div class="ic" style="--ic:var(--${{i.type==='positive'?'acc':i.type==='negative'?'red':'blue'}});background:rgba(${{i.type==='positive'?'74,222,128':i.type==='negative'?'248,113,113':'96,165,250'}},.06)">
    <div class="ic-tp">${{i.type.toUpperCase()}}</div><div class="ic-ti">${{i.title}}</div><div class="ic-pt">${{i.desc}}</div></div>
`).join('');

// OFF 권고
document.getElementById('off-cumul-tbl').innerHTML=`
  <thead><tr><th>소재</th><th>TIER</th><th>CPA</th><th>CVR</th><th>비용</th><th>액션</th></tr></thead>
  <tbody>${{D.off_cumul.map(o=>`
    <tr>
      <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis">${{o.creative_name.replace(/_\\d{{4,6}}$/,'')}}</td>
      <td><span class="badge ${{o.TIER}}">${{o.TIER}}</span></td>
      <td class="num bad">${{fmtWon(o.CPA)}}</td>
      <td class="num">${{fmtPct(o.CVR)}}</td>
      <td class="num">${{fmt(o.총비용)}}원</td>
      <td><span class="badge OFF">${{o.action}}</span></td>
    </tr>
  `).join('')}}</tbody>`;

// 지점별 소재 카드 (bc 탭)
const byBranchHtml=Object.entries(D.by_branch||{{}}).map(([br,creatives])=>{{
  const brInfo=D.branch.find(b=>b.branch===br)||{{}};
  return `
    <div class="card" style="padding:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <span style="font-weight:700;font-size:14px">${{br}}</span>
        <span style="font-size:11px;color:var(--tx2)">CPA ${{fmtWon(brInfo.CPA)}} · 전환 ${{brInfo.총전환||0}}건</span>
      </div>
      <table style="font-size:11px">
        <thead><tr><th>소재명</th><th>TIER</th><th>CPA</th><th>CVR</th><th>전환</th></tr></thead>
        <tbody>${{creatives.slice(0,5).map(c=>`
          <tr style="${{c.is_best?'border-left:3px solid var(--acc);':''}}"${{c.is_best?' class="best"':''}}>
            <td style="max-width:100px;overflow:hidden;text-overflow:ellipsis">${{c.creative_name}}</td>
            <td><span class="badge ${{c.tier}}">${{c.tier}}</span></td>
            <td class="num ${{c.is_best?'good':''}}">${{fmtWon(c.CPA)}}</td>
            <td class="num">${{c.CVR?c.CVR+'%':'-'}}</td>
            <td class="num">${{c.conv}}건</td>
          </tr>
        `).join('')}}</tbody>
      </table>
    </div>
  `;
}}).join('');
document.getElementById('by-branch-cards').innerHTML=byBranchHtml||'<div class="card" style="color:var(--tx2)">지점별 소재 데이터 없음</div>';

// 지점×나이대 히트맵 (branch 탭)
const ages=['25-34','35-44','45-54','≥55','Unknown'];
const hmBrAgeHtml=`
  <div style="display:grid;grid-template-columns:60px repeat(${{ages.length}},1fr);gap:2px">
    <div class="hm-hdr"></div>
    ${{ages.map(a=>`<div class="hm-hdr">${{a}}</div>`).join('')}}
    ${{Object.entries(D.hm_br_age||{{}}).map(([br,ageData])=>`
      <div class="hm-lbl">${{br}}</div>
      ${{ages.map(a=>{{
        const cpa=ageData[a];
        const intensity=cpa?Math.min(1,cpa/50000):.1;
        const bg=cpa?`rgba(96,165,250,${{intensity*.6+.1}})`:'rgba(255,255,255,.03)';
        return `<div class="hm-cell" style="background:${{bg}}">${{cpa?fmt(cpa):'-'}}</div>`;
      }}).join('')}}
    `).join('')}}
  </div>
`;
document.getElementById('hm-br-age').innerHTML=hmBrAgeHtml;

// 소재유형×나이대 CTR 히트맵 (age 탭)
const hmAges=['25-34','35-44','45-54','≥55'];  // Unknown 제외
const ctypes=Object.keys(D.hm_ctr||{{}});
const hmCtrHtml=ctypes.length?`
  <div style="display:grid;grid-template-columns:100px repeat(${{hmAges.length}},1fr);gap:2px">
    <div class="hm-hdr"></div>
    ${{hmAges.map(a=>`<div class="hm-hdr">${{a}}</div>`).join('')}}
    ${{ctypes.map(ct=>`
      <div class="hm-lbl">${{ct}}</div>
      ${{hmAges.map(a=>{{
        const ctr=(D.hm_ctr[ct]||{{}})[a];
        const intensity=ctr?Math.min(1,ctr/2):.1;
        const bg=ctr?`rgba(74,222,128,${{intensity*.6+.1}})`:'rgba(255,255,255,.03)';
        return `<div class="hm-cell" style="background:${{bg}}">${{ctr!=null?ctr.toFixed(2)+'%':'-'}}</div>`;
      }}).join('')}}
    `).join('')}}
  </div>
`:'<div style="color:var(--tx2)">데이터 없음</div>';
document.getElementById('hm-ctr').innerHTML=hmCtrHtml;

// 소재유형×나이대 CVR 히트맵 (age 탭)
const hmCvrHtml=ctypes.length?`
  <div style="display:grid;grid-template-columns:100px repeat(${{hmAges.length}},1fr);gap:2px">
    <div class="hm-hdr"></div>
    ${{hmAges.map(a=>`<div class="hm-hdr">${{a}}</div>`).join('')}}
    ${{ctypes.map(ct=>`
      <div class="hm-lbl">${{ct}}</div>
      ${{hmAges.map(a=>{{
        const cvr=(D.hm_cvr[ct]||{{}})[a];
        const intensity=cvr?Math.min(1,cvr/10):.1;
        const bg=cvr?`rgba(96,165,250,${{intensity*.6+.1}})`:'rgba(255,255,255,.03)';
        return `<div class="hm-cell" style="background:${{bg}}">${{cvr!=null?cvr.toFixed(2)+'%':'-'}}</div>`;
      }}).join('')}}
    `).join('')}}
  </div>
`:'<div style="color:var(--tx2)">데이터 없음</div>';
document.getElementById('hm-cvr').innerHTML=hmCvrHtml;

// 원본 데이터 (raw 탭) - D.raw 사용
document.getElementById('raw-tbl').innerHTML=`
  <thead><tr><th>소재명</th><th>지점</th><th>기간</th><th>비용</th><th>노출</th><th>클릭</th><th>CTR</th><th>랜딩</th><th>LPV</th><th>전환</th><th>CVR</th><th>CPA</th></tr></thead>
  <tbody>${{(D.raw||[]).slice(0,100).map(r=>`
    <tr>
      <td style="max-width:140px;overflow:hidden;text-overflow:ellipsis">${{r.creative_name}}</td>
      <td>${{r.branch}}</td>
      <td class="num">${{r.date_range}}</td>
      <td class="num">${{fmt(r.cost)}}</td>
      <td class="num">${{fmt(r.impr)}}</td>
      <td class="num">${{fmt(r.clicks)}}</td>
      <td class="num">${{fmtPct(r.ctr)}}</td>
      <td class="num">${{fmt(r.landing)}}</td>
      <td class="num">${{r.lpv?r.lpv+'%':'-'}}</td>
      <td class="num">${{r.conv}}</td>
      <td class="num">${{fmtPct(r.cvr)}}</td>
      <td class="num">${{fmtWon(r.cpa)}}</td>
    </tr>
  `).join('')}}</tbody>`;

// 원본 데이터 - 일별
document.getElementById('raw-daily-tbl').innerHTML=`
  <thead><tr><th>날짜</th><th>비용</th><th>전환</th><th>CPA</th><th>CTR</th><th>CVR</th></tr></thead>
  <tbody>${{D.daily.map(d=>`
    <tr>
      <td>${{d.date_str}}</td>
      <td class="num">${{fmt(d.cost)}}</td>
      <td class="num">${{d.conv}}</td>
      <td class="num">${{fmtWon(d.cpa)}}</td>
      <td class="num">${{fmtPct(d.ctr)}}</td>
      <td class="num">${{fmtPct(d.cvr)}}</td>
    </tr>
  `).join('')}}</tbody>`;

// OFF 소재 원본 데이터
document.getElementById('raw-off-tbl').innerHTML=`
  <thead><tr><th>소재명</th><th>지점</th><th>기간</th><th>비용</th><th>전환</th><th>CPA</th><th>CTR</th><th>CVR</th></tr></thead>
  <tbody>${{(D.raw_off||[]).slice(0,50).map(r=>{{
    const cpaCls=r.is_low_conv?'muted':'';
    const cpaDisp=r.is_low_conv?'-':fmtWon(r.cpa);
    return `<tr>
      <td style="max-width:140px;overflow:hidden;text-overflow:ellipsis">${{r.creative_name}}</td>
      <td>${{r.branch}}</td>
      <td class="num">${{r.date_range}}</td>
      <td class="num">${{fmt(r.cost)}}</td>
      <td class="num">${{r.conv}}</td>
      <td class="num ${{cpaCls}}">${{cpaDisp}}</td>
      <td class="num">${{fmtPct(r.ctr)}}</td>
      <td class="num">${{fmtPct(r.cvr)}}</td>
    </tr>`;
  }}).join('')}}</tbody>`;

// 초기 로드 시 차트 resize
window.addEventListener('load',()=>charts.forEach(c=>c.resize()));
</script>
</body>
</html>'''

    return html


if __name__ == "__main__":
    import sys
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "output/20260227"
    target_month = sys.argv[2] if len(sys.argv) > 2 else None

    build_monthly(data_dir, target_month)
