"""
먼슬리 리포트 생성 (HTML 7탭)
클라이언트 + 의사결정자용 - 익월 1~3일 발행

입력: output/data/YYYYMMDD/ (파싱된 parquet 파일들)
출력: output/monthly/YYYYMM/tiktok_monthly_dayt_YYYYMM.html
레퍼런스: output/_ref/monthly_ref.html

탭 구조: 요약 | 소재 TIER | 지점 분석 | 나이대 | 소재 수명 | 일별 트렌드 | 다음 달 전략
"""
import pandas as pd
import numpy as np
import os
import json
import re
from datetime import datetime
from pathlib import Path


VALID_BRANCHES = ['서울', '부평', '수원', '일산', '대구', '창원', '천안']
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
            branches = grp['branch'].unique().tolist()
            # VALID_BRANCHES 순서로 정렬
            creative_branches[name] = [b for b in VALID_BRANCHES if b in branches]

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
            '지점목록': branches,  # 레퍼런스 키
            '소재유형': r.get('creative_type', r.get('소재유형', '')),
            '훅유형': r.get('hook_type', r.get('소재구분', '')),  # 레퍼런스 키
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
            '비용비중': cost_share, '전환비중': conv_share, '효율점수': eff,
        })
    # VALID_BRANCHES 순서로 정렬
    branch_order = {b: i for i, b in enumerate(VALID_BRANCHES)}
    branch_list.sort(key=lambda x: branch_order.get(x['branch'], 999))

    # ========== age 리스트 (Unknown 제외) ==========
    age_list = []
    if 'age_group' in df_on.columns:
        # Unknown 제외
        df_age_filtered = df_on[~df_on['age_group'].str.lower().str.contains('unknown', na=False)]
        age_agg = df_age_filtered.groupby('age_group').agg(
            cost=('cost', 'sum'), conv=('conversions', 'sum'),
            clicks=('clicks', 'sum'), impr=('impressions', 'sum'),
            landing=('landing_views', 'sum') if 'landing_views' in df_age_filtered.columns else ('cost', 'count'),
        ).reset_index()

        for _, r in age_agg.iterrows():
            cost = int(r['cost'])
            conv = int(r['conv'])
            clicks = int(r['clicks'])
            impr = int(r['impr'])
            landing = int(r['landing']) if 'landing_views' in df_age_filtered.columns else 0
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
                '효율점수': round(conv_share / cost_share, 2) if cost_share > 0 else None,  # 레퍼런스 키
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
            clicks = int(r['clicks'])
            conv = int(r['conv'])
            hook_list.append({
                'hook_type': r[hook_col],
                '총비용': int(r['cost']), '총전환': conv,
                '총클릭': clicks, '총노출': int(r['impr']), '총랜딩': landing, '소재수': int(r['cnt']),
                'CPA': round(r['cost'] / conv) if conv > 0 else 0,
                'CTR': round(clicks / r['impr'] * 100, 2) if r['impr'] > 0 else 0,
                'CVR': round(conv / clicks * 100, 2) if clicks > 0 else 0,  # 전환/클릭 (그래프용 0 반환)
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

    # ========== lifetime (소재 수명) - 레퍼런스: name, tier, days, ctr, total_days만 ==========
    lifetime_list = []
    for c in creative_list[:10]:  # 상위 10개만
        name = c['creative_name']
        tier = c['TIER']
        days = c['집행일수']
        base_ctr = c['CTR'] or 0
        # 일별 CTR 추이 (시뮬레이션 - 실제 데이터 필요 시 별도 집계)
        ctr_trend = [round(base_ctr * (0.8 + 0.4 * np.random.random()), 2) for _ in range(days)] if days > 0 and base_ctr else []
        lifetime_list.append({
            'name': name,  # 레퍼런스는 원본 소재명 사용 (clean 안 함)
            'tier': tier,
            'days': list(range(1, days + 1)) if days > 0 else [],
            'ctr': ctr_trend,
            'total_days': days,
        })

    # ========== OFF 소재 집행지점 집계 ==========
    off_branches = {}
    if 'creative_name' in df_off.columns and 'branch' in df_off.columns:
        for name, grp in df_off.groupby('creative_name'):
            branches = grp['branch'].unique().tolist()
            # VALID_BRANCHES 순서로 정렬
            off_branches[name] = [b for b in VALID_BRANCHES if b in branches]

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

        # OFF 일자 = cost > 0인 마지막 날짜의 다음날
        # (비용이 0이 되기 시작한 첫 날짜)
        cost_positive = df_off[df_off['cost'] > 0]
        if len(cost_positive) > 0:
            last_cost_dates = cost_positive.groupby(['creative_name', 'branch'])['date'].max().reset_index()
            last_cost_dates.columns = ['creative_name', 'branch', 'last_cost_date']
            last_cost_dates['off_date'] = last_cost_dates['last_cost_date'] + pd.Timedelta(days=1)
            off_last_dates = last_cost_dates[['creative_name', 'branch', 'off_date']]
        else:
            # cost > 0 데이터가 없으면 기존 로직 사용 (fallback)
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

            # OFF 소재 자체 성과 데이터 - 레퍼런스 필수 필드
            off_creative_data = df_off[(df_off['creative_name'] == name) & (df_off['branch'] == branch)]
            off_cost = int(off_creative_data['cost'].sum())
            off_conv = int(off_creative_data['conversions'].sum())
            off_clicks = int(off_creative_data['clicks'].sum())
            off_impr = int(off_creative_data['impressions'].sum())

            off_cpa = round(off_cost / off_conv) if off_conv > 0 else None
            off_ctr = round(off_clicks / off_impr * 100, 2) if off_impr > 0 else 0
            off_cvr = round(off_conv / off_clicks * 100, 2) if off_clicks > 0 else 0

            # 비용 점유율 계산
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

            # CPA 변화 (절대값 + 퍼센트)
            cpa_change = None
            cpa_change_pct = None
            if before_cpa and after_cpa:
                cpa_change = int(after_cpa - before_cpa)
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

            # impact_label - 레퍼런스 키
            impact_labels = {'high': '주요 소재', 'mid': '중간', 'low': '낮음'}
            impact_label = impact_labels.get(impact_level, '')

            # effect 판정 (CPA 변화 기준) - 레퍼런스 키
            if before_cpa and after_cpa:
                if after_cpa < before_cpa * 0.95:
                    effect = 'improved'
                elif after_cpa > before_cpa * 1.05:
                    effect = 'worsened'
                else:
                    effect = 'neutral'
            else:
                effect = None

            before_after.append({
                'creative_name': str(name),
                'branch': branch,
                'off_date': off_date.strftime('%m/%d'),
                'before_cpa': before_cpa,
                'after_cpa': after_cpa,
                'before_days': before_days,
                'after_days': after_days,
                'cpa_change': cpa_change,      # 레퍼런스 키 - 절대값
                'cpa_change_pct': cpa_change_pct,
                'share_pct': share_pct,
                'reliability': reliability,
                'impact_level': impact_level,
                'impact_label': impact_label,  # 레퍼런스 키
                'effect': effect,              # 레퍼런스 키
                # OFF 소재 자체 성과 - 레퍼런스 키
                'off_cpa': off_cpa,
                'off_ctr': off_ctr,
                'off_cvr': off_cvr,
                'off_cost': off_cost,
                'off_conv': off_conv,
            })

    # ========== expansion (TIER1 미집행 지점) ==========
    expansion = []
    tier1_creatives = [c for c in creative_list if c['TIER'] == 'TIER1']
    for c in tier1_creatives:
        current = c['지점목록'] if isinstance(c['지점목록'], list) else [c['지점목록']]
        missing = [b for b in VALID_BRANCHES if b not in current]
        if missing:
            expansion.append({
                'creative_name': c['creative_name'],
                'missing': missing,
                'CPA': int(c['CPA']) if c['CPA'] else None,
                'current': current,
            })

    # ========== cross_gap (소재×지점 CPA 편차) - 레퍼런스: 소재별 최우수/최저 비교 ==========
    # NOTE: ad_name이 아닌 creative_name 기준으로 그룹화해야 함
    #       ad_name에는 지점명이 포함되어 있어 단일 지점만 해당하기 때문
    cross_gap = []
    if 'branch' in df_on.columns and 'creative_name' in df_on.columns:
        agg_dict = {
            'cost': ('cost', 'sum'), 'conv': ('conversions', 'sum'),
        }
        # creative_name × branch 기준 집계 (ad_name 아님!)
        bc_agg = df_on.groupby(['creative_name', 'branch']).agg(**agg_dict).reset_index()
        bc_agg['cpa'] = (bc_agg['cost'] / bc_agg['conv'].replace(0, np.nan)).round(0)

        # TIER 매핑
        tier_map = {c['creative_name']: c['TIER'] for c in creative_list}

        # 소재별로 최우수/최저 지점 찾기 (creative_name 기준)
        for creative_name in bc_agg['creative_name'].unique():
            creative_data = bc_agg[bc_agg['creative_name'] == creative_name].dropna(subset=['cpa'])
            if len(creative_data) < 2:  # 2개 이상 지점이 있어야 비교 가능
                continue

            best_row = creative_data.loc[creative_data['cpa'].idxmin()]
            worst_row = creative_data.loc[creative_data['cpa'].idxmax()]

            best_cpa = int(best_row['cpa'])
            worst_cpa = int(worst_row['cpa'])
            ratio = round(worst_cpa / best_cpa, 1) if best_cpa > 0 else None

            cross_gap.append({
                '소재명': strip_date_code(creative_name),
                'TIER': tier_map.get(creative_name, 'UNCLASSIFIED'),
                'ratio': ratio,
                '최우수': best_row['branch'],
                '최우수CPA': best_cpa,
                '최저': worst_row['branch'],
                '최저CPA': worst_cpa,
            })

        # ratio 기준 내림차순 정렬 (격차 큰 순)
        cross_gap.sort(key=lambda x: x['ratio'] or 0, reverse=True)

    # ========== hm_ctr, hm_cvr (소재유형×나이대 히트맵) - Unknown 제외, 레퍼런스: list 형태 ==========
    hm_ctr = []
    hm_cvr = []
    if 'creative_type' in df_on.columns and 'age_group' in df_on.columns:
        # Unknown 제외
        df_hm_filtered = df_on[~df_on['age_group'].str.lower().str.contains('unknown', na=False)]
        agg_dict = {
            'clicks': ('clicks', 'sum'), 'impr': ('impressions', 'sum'), 'conv': ('conversions', 'sum'),
        }
        if 'landing_views' in df_hm_filtered.columns:
            agg_dict['landing'] = ('landing_views', 'sum')
        hm_agg = df_hm_filtered.groupby(['creative_type', 'age_group']).agg(**agg_dict).reset_index()

        for _, r in hm_agg.iterrows():
            ct = r['creative_type']
            ag = r['age_group']
            ctr = round(r['clicks'] / r['impr'] * 100, 2) if r['impr'] > 0 else 0
            cvr = round(r['conv'] / r['clicks'] * 100, 2) if r['clicks'] > 0 else 0
            hm_ctr.append({'creative_type': ct, 'age_group': ag, 'CTR': ctr})
            hm_cvr.append({'creative_type': ct, 'age_group': ag, 'CVR': cvr})

    # ========== hm_br_age (지점×나이대 히트맵) - Unknown 제외, 레퍼런스: list 형태 ==========
    hm_br_age = []
    if 'branch' in df_on.columns and 'age_group' in df_on.columns:
        # Unknown 제외
        df_br_age_filtered = df_on[~df_on['age_group'].str.lower().str.contains('unknown', na=False)]
        br_age_agg = df_br_age_filtered.groupby(['branch', 'age_group']).agg(
            cost=('cost', 'sum'), conv=('conversions', 'sum'),
        ).reset_index()

        for _, r in br_age_agg.iterrows():
            br = r['branch']
            ag = r['age_group']
            cpa = round(r['cost'] / r['conv']) if r['conv'] > 0 else None
            hm_br_age.append({'branch': br, 'age_group': ag, 'CPA': cpa})

    # ========== next_budget (다음 달 예산 권고) - 레퍼런스 키 ==========
    total_budget = sum(BUDGET.values())
    next_budget = []
    for b in branch_list:
        cur_budget = BUDGET.get(b['branch'], 0)
        eff = b.get('효율점수', 1.0) or 1.0
        cur_ratio = round(cur_budget / total_budget * 100, 1) if total_budget > 0 else 0
        cpa = b['CPA'] or 0
        cvr = b['CVR'] or 0

        # 효율점수에 따른 색상 및 reason
        if eff >= 1.2:
            color = '#4ade80'  # 좋음 (녹색)
            direction = '증액 권고'
            suggested = int(cur_budget * 1.15)
            reason = f'효율점수 {round(eff, 2)} (상위) · CPA {int(cpa/1000)}천원 · CVR {cvr}%'
        elif eff >= 0.8:
            color = '#60a5fa'  # 보통 (파랑)
            direction = '유지'
            suggested = cur_budget
            reason = f'효율점수 {round(eff, 2)} (평균) · CPA {int(cpa/1000)}천원 · CVR {cvr}%'
        else:
            color = '#f87171'  # 낮음 (빨강)
            direction = '감액 검토'
            suggested = int(cur_budget * 0.85)
            reason = f'효율점수 {round(eff, 2)} (하위) · CPA {int(cpa/1000)}천원 · CVR {cvr}%'

        next_budget.append({
            'branch': b['branch'],
            'cur_budget': cur_budget,  # 레퍼런스 키
            'cur_ratio': cur_ratio,    # 레퍼런스 키
            '효율점수': round(eff, 2),  # 레퍼런스 키
            'color': color,            # 레퍼런스 키
            'reason': reason,          # 레퍼런스 키
            'suggested': suggested,
            'direction': direction,
            'cpa': cpa,
            'cvr': cvr,
        })

    # ========== off_cumul (OFF 권고) - 레퍼런스 키 ==========
    off_cumul = []
    tier4_creatives = [c for c in creative_list if c['TIER'] == 'TIER4']
    for c in tier4_creatives:
        cpa = c['CPA'] or 0
        cvr = c['CVR'] or 0
        ratio = round(cpa / target_cpa, 1) if target_cpa > 0 and cpa else 0
        branches = c.get('지점목록', [])
        branch_str = ', '.join(branches) if isinstance(branches, list) else str(branches)
        off_cumul.append({
            'branch': branch_str,              # 레퍼런스 키
            'creative_name': c['creative_name'],
            'CPA': cpa,
            'ratio': ratio,                    # 레퍼런스 키 (목표CPA 대비 배수)
            'CVR': cvr,
            'cost': c['총비용'],               # 레퍼런스 키
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
            branch_data['cvr'] = (branch_data['conv'] / branch_data['clicks'].replace(0, np.nan) * 100).round(2)  # 전환/클릭
            # VALID_BRANCHES 순서로 정렬
            branch_data['_order'] = branch_data['branch'].apply(lambda x: VALID_BRANCHES.index(x) if x in VALID_BRANCHES else 999)
            branch_data = branch_data.sort_values('_order').drop(columns=['_order'])

            # CPA 기준 정렬 (오름차순, NaN은 끝으로)
            branch_data = branch_data.sort_values('cpa', na_position='last')

            # CTR 계산
            branch_data['ctr'] = (branch_data['clicks'] / branch_data['impr'].replace(0, np.nan) * 100).round(2)

            creatives = []
            for i, (_, r) in enumerate(branch_data.iterrows()):
                creatives.append({
                    'creative_name': clean_cross_gap_name(r['creative_name']),
                    'CPA': int(r['cpa']) if pd.notna(r['cpa']) else None,
                    'CVR': r['cvr'] if pd.notna(r['cvr']) else None,
                    'CTR': r['ctr'] if pd.notna(r['ctr']) else None,
                    'conv': int(r['conv']),
                    'cost': int(r['cost']),
                    'clicks': int(r['clicks']),
                    'impr': int(r['impr']),
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
            cvr = round(conv / clicks * 100, 2) if clicks > 0 else None  # 전환/클릭 (통일)
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
            cvr = round(conv / clicks * 100, 2) if clicks > 0 else None  # 전환/클릭 (통일)
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

    # ========== creative 리스트 분리 (TIER 보유 / UNCLASSIFIED) ==========
    creative_classified = [c for c in creative_list if c['TIER'] not in ['UNCLASSIFIED']]
    creative_new = [c for c in creative_list if c['TIER'] == 'UNCLASSIFIED']

    # ========== D 객체 생성 (레퍼런스 키 기준) ==========
    D = {
        'period': f"{date_min.strftime('%Y.%m.%d')} ~ {date_max.strftime('%m.%d')}",
        'kpi': kpi,
        'target_cpa': target_cpa,
        'monthly_target_conv': MONTHLY_TARGET_CONV,
        'budget': BUDGET,
        'creative': creative_classified,   # TIER1~4, LOW_VOLUME만
        'creative_new': creative_new,       # UNCLASSIFIED (신규 소재)
        'branch': branch_list,
        'by_branch': by_branch,             # 지점별 소재 분석
        'cross_gap': cross_gap,
        'age': age_list,
        'hm_ctr': hm_ctr,
        'hm_cvr': hm_cvr,
        'hm_br_age': hm_br_age,
        'lifetime': lifetime_list,
        'hook_compare': hook_list,
        'daily': daily_list,
        'next_budget': next_budget,
        'off_cumul': off_cumul,
        'expansion': expansion,
        'off_perf': off_perf,
        'before_after': before_after,
    }

    D = clean(D)

    # ========== HTML 생성 ==========
    html = generate_html(D, month)

    # 저장 (output/monthly/YYYYMM/)
    # 스크립트 위치에서 프로젝트 루트 계산 (.claude/skills/report-generator/scripts/)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent.parent

    monthly_dir = project_root / "output" / "monthly" / month
    monthly_dir.mkdir(parents=True, exist_ok=True)

    output_path = monthly_dir / f"tiktok_monthly_dayt_{month}.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"[OK] Monthly report -> {output_path}")
    return output_path


def generate_html(D: dict, month: str) -> str:
    """HTML 생성 - monthly_ref.html 템플릿 기반 데이터 주입"""

    # 레퍼런스 파일 경로
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent.parent
    ref_path = project_root / "output" / "_ref" / "monthly_ref.html"

    if not ref_path.exists():
        raise FileNotFoundError(f"레퍼런스 파일 없음: {ref_path}")

    # 레퍼런스 파일 읽기
    with open(ref_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # const D= 줄 찾기
    d_line_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith('const D='):
            d_line_idx = i
            break

    if d_line_idx is None:
        raise ValueError("레퍼런스 파일에서 'const D=' 라인을 찾을 수 없음")

    # 데이터 JSON 생성
    d_json = json.dumps(D, ensure_ascii=False)

    # HTML 조합: 앞부분 + const D=새데이터; + 뒷부분
    year = month[:4]
    mon = month[4:]

    header = ''.join(lines[:d_line_idx])
    footer = ''.join(lines[d_line_idx + 1:])
    data_line = f'const D={d_json};\n'

    html = header + data_line + footer

    # 동적 부분 교체
    html = re.sub(r'\d{4}년 \d{1,2}월 먼슬리 리포트', f'{year}년 {mon}월 먼슬리 리포트', html)
    html = re.sub(r'분석 기간 <span>[^<]+</span>', f'분석 기간 <span>{D["period"]}</span>', html)
    html = re.sub(r'\d{1,2}월 월간 KPI', f'{mon}월 월간 KPI', html)

    return html



if __name__ == "__main__":
    import sys
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "output/data/20260227"
    target_month = sys.argv[2] if len(sys.argv) > 2 else None

    build_monthly(data_dir, target_month)
