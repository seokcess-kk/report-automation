"""
위클리 리포트 생성 (HTML)
클라이언트용 - 매주 월요일 발행

레퍼런스: output/tiktok_weekly_dayt_20260224.html
- JS 클라이언트 사이드 렌더링
- TIER 전주 비교 + 변동 표시
- 지점별 차트 2개 (CPA, CTR/CVR)
- 상세 인사이트 구조
- OFF/ON 액션플랜 분리
"""
import pandas as pd
import numpy as np
import os
import re
import json
from datetime import datetime, timedelta


MONTHLY_TARGET_CONV = 600

VALID_BRANCHES = ['부평', '서울', '수원', '대구', '창원', '천안', '일산']
VALID_AD_TYPES = ['인플방문후기', '진료셀프캠', '의료진정보']


def strip_date_code(name: str) -> str:
    """소재명에서 날짜코드 제거 (_YYMM, _YYMMDD 등 4~6자리)"""
    if not name or pd.isna(name):
        return name
    return re.sub(r'_\d{4,6}$', '', str(name))


def load_and_parse_data(csv_path: str) -> pd.DataFrame:
    """CSV 로드 및 파싱"""
    df = pd.read_csv(csv_path, dtype={'광고 ID': str}, encoding='utf-8-sig')

    col_map = {
        '클릭수(목적지)': 'clicks',
        '노출수': 'impressions',
        '전환수': 'conversions',
        '비용': 'cost',
        '랜딩 페이지 조회(웹사이트)': 'landing_views',
        '일별': 'date',
        '나이': 'age_group',
        '광고 이름': 'ad_name',
        '광고 ID': 'ad_id',
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    for col in ['clicks', 'impressions', 'conversions', 'cost', 'landing_views']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['is_off'] = df['ad_name'].str.lower().str.endswith('_off')

    def parse_ad(name):
        if pd.isna(name):
            return None, None, None, None
        name = str(name).strip()
        is_off = name.lower().endswith('_off')
        clean = name[:-4] if is_off else name
        parts = clean.split('_')
        if len(parts) < 4:
            return None, None, None, None

        hook_type = '재가공' if '재' in parts[0] else ('신규' if '신' in parts[0] else '일반')
        branch = parts[1] if parts[1] in VALID_BRANCHES else None
        ad_type = parts[2] if parts[2] in VALID_AD_TYPES else '기타'
        creative = '_'.join(parts[3:])

        return branch, ad_type, hook_type, creative

    parsed = df['ad_name'].apply(parse_ad)
    df['branch'] = parsed.apply(lambda x: x[0])
    df['ad_type'] = parsed.apply(lambda x: x[1])
    df['hook_type'] = parsed.apply(lambda x: x[2])
    df['creative_name'] = parsed.apply(lambda x: x[3])

    return df


def filter_week_data(df: pd.DataFrame, end_date: datetime = None):
    """이번 주 / 전주 데이터 분리"""
    if end_date is None:
        end_date = df['date'].max()

    this_start = end_date - timedelta(days=6)
    df_this = df[(df['date'] >= this_start) & (df['date'] <= end_date)]

    prev_end = this_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=6)
    df_prev = df[(df['date'] >= prev_start) & (df['date'] <= prev_end)]

    return df_this, df_prev, this_start, end_date, prev_start, prev_end


def calc_kpi(df: pd.DataFrame) -> dict:
    """KPI 계산"""
    df_on = df[~df['is_off']]
    cost = df_on['cost'].sum()
    conv = df_on['conversions'].sum()
    clicks = df_on['clicks'].sum()
    impr = df_on['impressions'].sum()

    return {
        'cost': int(cost),
        'conv': int(conv),
        'cpa': int(cost / conv) if conv > 0 else 0,
        'ctr': round(clicks / impr * 100, 2) if impr > 0 else 0,
        'cvr': round(conv / clicks * 100, 2) if clicks > 0 else 0,
    }


def classify_tier_weekly(df: pd.DataFrame, target_cpa: float) -> pd.DataFrame:
    """위클리 TIER 분류"""
    df_on = df[~df['is_off']].copy()

    creative = df_on.groupby('creative_name').agg(
        branches=('branch', lambda x: list(x.dropna().unique())),
        ad_type=('ad_type', 'first'),
        cost=('cost', 'sum'),
        conv=('conversions', 'sum'),
        clicks=('clicks', 'sum'),
        impr=('impressions', 'sum'),
        landing=('landing_views', 'sum'),
        days=('date', 'nunique'),
    ).reset_index()

    creative['cpa'] = (creative['cost'] / creative['conv'].replace(0, np.nan)).round(0)
    creative['ctr'] = (creative['clicks'] / creative['impr'].replace(0, np.nan) * 100).round(2)
    creative['cvr'] = (creative['conv'] / creative['clicks'].replace(0, np.nan) * 100).round(2)
    creative['lpv'] = (creative['landing'] / creative['clicks'].replace(0, np.nan) * 100).round(1)

    def _tier(row):
        if row['days'] < 3:
            return 'UNCLASSIFIED'
        if row['clicks'] < 50 and row['cost'] < 50000:
            return 'LOW_VOLUME'

        cpa_ok = pd.notna(row['cpa']) and row['cpa'] <= target_cpa
        cvr_ok = pd.notna(row['cvr']) and row['cvr'] >= 5.0

        if cpa_ok and cvr_ok:
            return 'TIER1'
        elif cpa_ok and not cvr_ok:
            return 'TIER2'
        elif not cpa_ok and cvr_ok:
            return 'TIER3'
        else:
            return 'TIER4'

    creative['tier'] = creative.apply(_tier, axis=1)
    return creative


def calc_branch_summary(df: pd.DataFrame) -> pd.DataFrame:
    """지점별 요약"""
    df_on = df[~df['is_off']]
    branch = df_on.groupby('branch').agg(
        cost=('cost', 'sum'),
        conv=('conversions', 'sum'),
        clicks=('clicks', 'sum'),
        impr=('impressions', 'sum'),
    ).reset_index()

    branch['cpa'] = (branch['cost'] / branch['conv'].replace(0, np.nan)).round(0)
    branch['ctr'] = (branch['clicks'] / branch['impr'].replace(0, np.nan) * 100).round(2)
    branch['cvr'] = (branch['conv'] / branch['clicks'].replace(0, np.nan) * 100).round(2)

    return branch.sort_values('cpa')


def make_unique_names(tier_df: pd.DataFrame) -> dict:
    """중복 소재명에 지점 정보 추가하여 고유 이름 생성
    Returns: {original_creative_name: display_name}
    """
    # strip_date_code 적용 후 이름 매핑
    name_map = {}
    stripped_names = {}

    for _, row in tier_df.iterrows():
        orig = row['creative_name']
        stripped = strip_date_code(orig)
        branches = row['branches'] if row['branches'] else []

        if stripped not in stripped_names:
            stripped_names[stripped] = []
        stripped_names[stripped].append((orig, branches))

    # 중복 이름 처리
    for stripped, items in stripped_names.items():
        if len(items) == 1:
            # 중복 없음 - 그대로 사용
            name_map[items[0][0]] = stripped
        else:
            # 중복 있음 - 지점 정보 추가
            for orig, branches in items:
                if len(branches) == 0:
                    suffix = ""
                elif len(branches) == 1:
                    suffix = f" ({branches[0]})"
                else:
                    suffix = f" ({branches[0]} 외 {len(branches)-1}개)"
                name_map[orig] = stripped + suffix

    return name_map


def generate_tier_comparison(tier_this: pd.DataFrame, tier_prev: pd.DataFrame) -> list:
    """TIER 전주 대비 비교 생성"""
    prev_dict = {}
    if len(tier_prev) > 0:
        prev_dict = tier_prev.set_index('creative_name')['tier'].to_dict()

    # 중복 소재명 처리
    name_map = make_unique_names(tier_this)

    result = []
    for _, row in tier_this.iterrows():
        display_name = name_map.get(row['creative_name'], strip_date_code(row['creative_name']))
        tier_now = row['tier']
        tier_before = prev_dict.get(row['creative_name'])

        if tier_before is None:
            change = '신규'
        elif tier_now == tier_before:
            change = '—'
        else:
            tier_order = {'TIER1': 1, 'TIER2': 2, 'TIER3': 3, 'TIER4': 4, 'LOW_VOLUME': 5, 'UNCLASSIFIED': 6}
            diff = tier_order.get(tier_now, 9) - tier_order.get(tier_before, 9)
            arrow = '↑' if diff < 0 else '↓'
            change = f"{tier_before}→{tier_now} {arrow}"

        result.append({
            'creative_name': display_name,
            'tier_this': tier_now,
            'tier_prev': tier_before,
            'change': change
        })

    return result


def generate_tier_detail(tier_this: pd.DataFrame) -> list:
    """TIER 상세 데이터"""
    # 중복 소재명 처리
    name_map = make_unique_names(tier_this)

    result = []
    for _, row in tier_this.iterrows():
        display_name = name_map.get(row['creative_name'], strip_date_code(row['creative_name']))
        result.append({
            'creative_name': display_name,
            '총비용': int(row['cost']),
            '총전환': int(row['conv']),
            '총클릭': int(row['clicks']),
            '총노출': int(row['impr']),
            '총랜딩': int(row.get('landing', 0)),
            '집행일수': int(row['days']),
            '지점목록': row['branches'],
            '소재유형': row.get('ad_type', '-'),
            'CPA': row['cpa'] if pd.notna(row['cpa']) else None,
            'CTR': row['ctr'] if pd.notna(row['ctr']) else None,
            'CVR': row['cvr'] if pd.notna(row['cvr']) else None,
            'LPV': row.get('lpv') if pd.notna(row.get('lpv')) else None,
            'TIER': row['tier']
        })
    return result


def generate_branch_comparison(branch_this: pd.DataFrame, branch_prev: pd.DataFrame) -> list:
    """지점별 전주 대비"""
    prev_dict = {}
    if len(branch_prev) > 0:
        prev_dict = branch_prev.set_index('branch')[['cpa', 'ctr', 'cvr']].to_dict('index')

    result = []
    for _, row in branch_this.iterrows():
        b = row['branch']
        prev = prev_dict.get(b, {})

        cpa_prev = prev.get('cpa')
        ctr_prev = prev.get('ctr')
        cvr_prev = prev.get('cvr')

        cpa_diff = row['cpa'] - cpa_prev if pd.notna(row['cpa']) and pd.notna(cpa_prev) else None
        ctr_diff = row['ctr'] - ctr_prev if pd.notna(row['ctr']) and pd.notna(ctr_prev) else None
        cvr_diff = row['cvr'] - cvr_prev if pd.notna(row['cvr']) and pd.notna(cvr_prev) else None

        result.append({
            'branch': b,
            '총비용': int(row['cost']),
            '총전환': int(row['conv']),
            '총클릭': int(row['clicks']),
            '총노출': int(row['impr']),
            'CPA': int(row['cpa']) if pd.notna(row['cpa']) else None,
            'CTR': round(row['ctr'], 2) if pd.notna(row['ctr']) else None,
            'CVR': round(row['cvr'], 2) if pd.notna(row['cvr']) else None,
            'CPA_prev': int(cpa_prev) if pd.notna(cpa_prev) else None,
            'CTR_prev': round(ctr_prev, 2) if pd.notna(ctr_prev) else None,
            'CVR_prev': round(cvr_prev, 2) if pd.notna(cvr_prev) else None,
            'CPA_diff': int(cpa_diff) if cpa_diff is not None else None,
            'CTR_diff': round(ctr_diff, 2) if ctr_diff is not None else None,
            'CVR_diff': round(cvr_diff, 2) if cvr_diff is not None else None,
        })

    return sorted(result, key=lambda x: x['CPA'] or 999999)


def generate_insights(kpi_this, kpi_prev, tier_list, branch_data) -> list:
    """인사이트 생성"""
    insights = []

    # 지점 CPA 악화 체크
    bad_branches = [b for b in branch_data if b.get('CPA_diff') and b['CPA_diff'] > 3000]
    if bad_branches:
        b = bad_branches[0]
        insights.append({
            'type': '악화',
            'color': '#f87171',
            'title': f"{b['branch']} CPA 동반 상승",
            'points': [
                f"{b['branch']} CPA 각 +{b['CPA_diff']:,}원 전주 대비 상승",
                "원인 1: 소재 피로도 의심 - CTR/CVR 동반 하락 추세",
                "원인 2: 경쟁 심화로 단가 상승 가능성"
            ]
        })

    # TIER 상승 소재
    tier_up = [t for t in tier_list if '↑' in t['change'] and 'TIER1' in t['tier_this']]
    if tier_up:
        t = tier_up[0]
        insights.append({
            'type': '개선',
            'color': '#4ade80',
            'title': f"'{t['creative_name']}' {t['change']}",
            'points': [
                "CTR/CVR 전주 대비 개선",
                "미집행 지점 추가 등록 검토"
            ]
        })

    # TIER 하락 소재
    tier_down = [t for t in tier_list if '↓' in t['change']]
    if tier_down and len(insights) < 3:
        t = tier_down[0]
        insights.append({
            'type': '변동',
            'color': '#f59e0b',
            'title': f"'{t['creative_name']}' {t['change']}",
            'points': [
                "이번 주 성과 하락",
                "지속 모니터링 필요"
            ]
        })

    return insights[:3]


def generate_off_list(tier_this: pd.DataFrame, branch_data: list, target_cpa: float) -> list:
    """OFF 권고 리스트
    조건: CPA > 지점평균 × 1.5 AND CVR < 3.0% 동시 충족
    """
    off_list = []

    # 지점별 평균 CPA
    branch_cpa = {b['branch']: b['CPA'] for b in branch_data if b.get('CPA')}

    tier4 = tier_this[tier_this['tier'] == 'TIER4']
    for _, row in tier4.iterrows():
        if pd.isna(row['cpa']):
            continue

        # CVR < 3.0% 조건 체크
        cvr = row['cvr'] if pd.notna(row['cvr']) else 0
        if cvr >= 3.0:
            continue

        for branch in row['branches']:
            avg_cpa = branch_cpa.get(branch, target_cpa)
            # CPA > 지점평균 × 1.5 조건 체크
            if row['cpa'] > avg_cpa * 1.5:
                off_list.append({
                    'branch': branch,
                    'creative_name': strip_date_code(row['creative_name']),
                    'CPA': int(row['cpa']),
                    'CVR': round(cvr, 2),
                    'avg_cpa': int(avg_cpa),
                    'ratio': round(row['cpa'] / avg_cpa, 1),
                    'cost': int(row['cost'])
                })

    return sorted(off_list, key=lambda x: -x['ratio'])[:5]


def generate_on_list(tier_this: pd.DataFrame) -> list:
    """ON 권고 리스트 (TIER1 확장)"""
    on_list = []
    tier1 = tier_this[tier_this['tier'] == 'TIER1']
    all_branches = set(VALID_BRANCHES)

    for _, row in tier1.iterrows():
        current = set(row['branches']) if row['branches'] else set()
        missing = all_branches - current
        if len(missing) >= 2:
            on_list.append({
                'creative_name': strip_date_code(row['creative_name']),
                'missing': sorted(list(missing)),
                'CPA': int(row['cpa']) if pd.notna(row['cpa']) else 0
            })

    return sorted(on_list, key=lambda x: x['CPA'])[:5]


def generate_branch_creative(df_this: pd.DataFrame) -> list:
    """소재×지점 성과 데이터 생성"""
    df_on = df_this[~df_this['is_off']].copy()

    # 소재명 × 지점 단위 집계
    agg = df_on.groupby(['creative_name', 'branch']).agg(
        cost=('cost', 'sum'),
        conv=('conversions', 'sum'),
        clicks=('clicks', 'sum'),
        impr=('impressions', 'sum'),
        days=('date', 'nunique'),
    ).reset_index()

    agg['cpa'] = (agg['cost'] / agg['conv'].replace(0, np.nan)).round(0)
    agg['ctr'] = (agg['clicks'] / agg['impr'].replace(0, np.nan) * 100).round(2)
    agg['cvr'] = (agg['conv'] / agg['clicks'].replace(0, np.nan) * 100).round(2)

    # 소재별 최저 CPA 계산 (색상 판단용)
    min_cpa_by_creative = agg.groupby('creative_name')['cpa'].min().to_dict()

    result = []
    for _, row in agg.iterrows():
        creative = strip_date_code(row['creative_name'])
        min_cpa = min_cpa_by_creative.get(row['creative_name'])

        # CPA 색상 판단
        cpa_color = 'normal'
        if pd.notna(row['cpa']) and pd.notna(min_cpa) and min_cpa > 0:
            ratio = row['cpa'] / min_cpa
            if ratio > 1.5:
                cpa_color = 'danger'
            elif ratio <= 1.2:
                cpa_color = 'good'

        result.append({
            'creative_name': creative,
            'branch': row['branch'],
            'CPA': int(row['cpa']) if pd.notna(row['cpa']) else None,
            'CTR': round(row['ctr'], 2) if pd.notna(row['ctr']) else None,
            'CVR': round(row['cvr'], 2) if pd.notna(row['cvr']) else None,
            '총전환': int(row['conv']),
            '총비용': int(row['cost']),
            '집행일수': int(row['days']),
            'cpa_color': cpa_color,
        })

    # 소재명 기준 정렬, 같은 소재명이면 CPA 오름차순
    result = sorted(result, key=lambda x: (x['creative_name'], x['CPA'] or 999999))
    return result


def calc_daily_trend(df: pd.DataFrame, week_start, week_end) -> list:
    """일별 추이 (이번 주 7일만)"""
    df_week = df[(df['date'] >= week_start) & (df['date'] <= week_end) & (~df['is_off'])]

    daily = df_week.groupby('date').agg(
        cost=('cost', 'sum'),
        conv=('conversions', 'sum'),
        clicks=('clicks', 'sum'),
        impr=('impressions', 'sum'),
    ).reset_index()

    daily['cpa'] = (daily['cost'] / daily['conv'].replace(0, np.nan)).round(0)
    daily['ctr'] = (daily['clicks'] / daily['impr'].replace(0, np.nan) * 100).round(2)
    daily['date_str'] = daily['date'].dt.strftime('%m/%d')

    result = []
    for _, row in daily.iterrows():
        result.append({
            'date_str': row['date_str'],
            'cost': int(row['cost']),
            'conv': int(row['conv']),
            'cpa': int(row['cpa']) if pd.notna(row['cpa']) else 0,
            'ctr': round(row['ctr'], 2) if pd.notna(row['ctr']) else 0
        })

    return result


def build_weekly_html(output_dir: str, csv_path: str, target_date: str = None):
    """위클리 HTML 생성"""

    df = load_and_parse_data(csv_path)
    end_date = pd.to_datetime(target_date) if target_date else df['date'].max()
    df_this, df_prev, this_start, this_end, prev_start, prev_end = filter_week_data(df, end_date)

    kpi_this = calc_kpi(df_this)
    kpi_prev = calc_kpi(df_prev)

    df_on = df_this[~df_this['is_off']]
    target_cpa = int(df_on['cost'].sum() / df_on['conversions'].sum()) if df_on['conversions'].sum() > 0 else 30000

    tier_this = classify_tier_weekly(df_this, target_cpa)
    tier_prev = classify_tier_weekly(df_prev, target_cpa) if len(df_prev) > 0 else pd.DataFrame()

    tier_list = generate_tier_comparison(tier_this, tier_prev)
    tier_detail = generate_tier_detail(tier_this)

    branch_this = calc_branch_summary(df_this)
    branch_prev = calc_branch_summary(df_prev) if len(df_prev) > 0 else pd.DataFrame()
    branch_data = generate_branch_comparison(branch_this, branch_prev)

    insights = generate_insights(kpi_this, kpi_prev, tier_list, branch_data)
    off_list = generate_off_list(tier_this, branch_data, target_cpa)
    on_list = generate_on_list(tier_this)

    # 소재×지점 성과
    branch_creative = generate_branch_creative(df_this)

    # 전환 예상
    month_start = pd.Timestamp(this_end.year, this_end.month, 1)
    df_month = df[(df['date'] >= month_start) & (df['date'] <= this_end) & (~df['is_off'])]
    conv_so_far = int(df_month['conversions'].sum())
    days_so_far = (this_end - month_start).days + 1
    proj_conv = int(conv_so_far / days_so_far * 28) if days_so_far > 0 else 0
    conv_pct = round(conv_so_far / MONTHLY_TARGET_CONV * 100, 1)
    proj_pct = round(proj_conv / MONTHLY_TARGET_CONV * 100, 1)

    # 일별 추이 (이번 주 7일만)
    daily = calc_daily_trend(df, this_start, this_end)

    # 요일 계산
    weekday_kr = ['월', '화', '수', '목', '금', '토', '일']

    data = {
        'period_this': f"{this_start.strftime('%m/%d')}~{this_end.strftime('%m/%d')}",
        'period_this_full': f"{this_start.strftime('%Y.%m.%d')}({weekday_kr[this_start.weekday()]}) ~ {this_end.strftime('%m.%d')}({weekday_kr[this_end.weekday()]})",
        'period_prev': f"{prev_start.strftime('%m/%d')}({weekday_kr[prev_start.weekday()]}) ~ {prev_end.strftime('%m/%d')}({weekday_kr[prev_end.weekday()]})",
        'issue_date': f"{datetime.now().strftime('%Y.%m.%d')}({weekday_kr[datetime.now().weekday()]})",
        'kpi_this': kpi_this,
        'kpi_prev': kpi_prev,
        'target_cpa': target_cpa,
        'tier_list': tier_list,
        'tier_this': tier_detail,
        'branch': branch_data,
        'off_list': off_list,
        'on_list': on_list,
        'branch_creative': branch_creative,
        'monthly_target_conv': MONTHLY_TARGET_CONV,
        'conv_so_far': conv_so_far,
        'proj_conv': proj_conv,
        'conv_pct': conv_pct,
        'proj_pct': proj_pct,
        'insights': insights,
        'daily': daily,
        'end_date_str': this_end.strftime('%m/%d'),
    }

    html = generate_html(data)

    os.makedirs(output_dir, exist_ok=True)
    filename = f"tiktok_weekly_dayt_{this_end.strftime('%Y%m%d')}.html"
    output_path = os.path.join(output_dir, filename)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"[OK] Weekly report -> {output_path}")
    return output_path


def generate_html(D: dict) -> str:
    """HTML 생성 (JS 클라이언트 사이드 렌더링)"""

    data_json = json.dumps(D, ensure_ascii=False, default=str)

    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>다이트한의원 TikTok 위클리 리포트 · {D['period_this']}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{
  --bg:#0d0f14; --surface:#13161e; --surface2:#191d28;
  --border:#1f2535; --accent:#4ade80; --accent2:#60a5fa;
  --danger:#f87171; --warn:#fb923c; --purple:#a78bfa;
  --text:#dde4f0; --text2:#7a8499; --text3:#3d4559;
  --t1:#4ade80; --t2:#60a5fa; --t3:#a78bfa; --t4:#f87171;
  --lv:#6b7280; --uc:#8b5cf6;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:'Noto Sans KR',sans-serif;font-size:14px;line-height:1.6}}
.mono{{font-family:'DM Mono',monospace}}

.report-header{{
  background:linear-gradient(135deg,#0d0f14 0%,#13161e 100%);
  border-bottom:1px solid var(--border);
  padding:36px 32px 28px;
}}
.header-inner{{max-width:1080px;margin:0 auto}}
.header-top{{display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px}}
.brand{{font-size:11px;font-weight:700;letter-spacing:.15em;color:var(--accent);text-transform:uppercase;margin-bottom:10px}}
.header-title{{font-size:26px;font-weight:900;letter-spacing:-.02em;color:var(--text)}}
.header-period{{margin-top:6px;display:flex;gap:16px;flex-wrap:wrap}}
.period-chip{{background:var(--surface2);border:1px solid var(--border);border-radius:6px;
  padding:4px 12px;font-size:12px;color:var(--text2)}}
.period-chip span{{color:var(--text);font-weight:600}}
.issue-badge{{background:rgba(74,222,128,.08);border:1px solid rgba(74,222,128,.2);
  border-radius:6px;padding:4px 14px;font-size:11px;color:var(--accent);font-weight:600;white-space:nowrap}}

.container{{max-width:1080px;margin:0 auto;padding:32px 24px}}
.section{{margin-bottom:40px}}
.section-label{{font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;
  color:var(--text3);margin-bottom:16px;display:flex;align-items:center;gap:10px}}
.section-label::after{{content:'';flex:1;height:1px;background:var(--border)}}

.kpi-strip{{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;
  background:var(--border);border-radius:10px;overflow:hidden}}
@media(max-width:700px){{.kpi-strip{{grid-template-columns:repeat(2,1fr)}}}}
.kpi-cell{{background:var(--surface);padding:18px 20px}}
.kpi-cell-label{{font-size:10px;font-weight:700;letter-spacing:.08em;color:var(--text2);
  text-transform:uppercase;margin-bottom:8px}}
.kpi-val{{font-size:20px;font-weight:900;font-family:'DM Mono',monospace;color:var(--text)}}
.kpi-diff{{margin-top:5px;font-size:11px;font-family:'DM Mono',monospace}}
.kpi-diff.good{{color:var(--accent)}} .kpi-diff.bad{{color:var(--danger)}} .kpi-diff.neutral{{color:var(--text2)}}

.card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:22px 24px}}
.card-title{{font-size:13px;font-weight:700;color:var(--text);margin-bottom:4px}}
.card-desc{{font-size:11px;color:var(--text2);margin-bottom:18px}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media(max-width:680px){{.two-col{{grid-template-columns:1fr}}}}

.insight-list{{display:flex;flex-direction:column;gap:12px}}
.insight-card{{border-radius:10px;padding:18px 20px;border-left:3px solid var(--ic)}}
.ic-type{{font-size:10px;font-weight:700;letter-spacing:.1em;color:var(--ic);margin-bottom:6px}}
.ic-title{{font-size:14px;font-weight:700;color:var(--text);margin-bottom:8px}}
.ic-point{{font-size:12px;color:var(--text2);padding:3px 0 3px 12px;border-left:2px solid var(--border);margin:3px 0}}

.tbl-wrap{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:var(--surface2);color:var(--text2);font-weight:600;font-size:10px;
  letter-spacing:.06em;text-transform:uppercase;padding:9px 14px;text-align:left;
  border-bottom:1px solid var(--border);white-space:nowrap}}
td{{padding:10px 14px;border-bottom:1px solid var(--border);color:var(--text);vertical-align:middle;white-space:nowrap}}
.td-name{{max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:rgba(255,255,255,.015)}}
.tier-badge{{display:inline-block;font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px}}
.TIER1{{background:rgba(74,222,128,.12);color:var(--t1)}}
.TIER2{{background:rgba(96,165,250,.12);color:var(--t2)}}
.TIER3{{background:rgba(167,139,250,.12);color:var(--t3)}}
.TIER4{{background:rgba(248,113,113,.12);color:var(--t4)}}
.LOW_VOLUME{{background:rgba(107,114,128,.12);color:var(--lv)}}
.UNCLASSIFIED{{background:rgba(139,92,246,.12);color:var(--uc)}}
.change-up{{color:var(--accent);font-weight:700}}
.change-down{{color:var(--danger);font-weight:700}}
.change-new{{color:var(--warn)}}

.collapsible-header{{display:flex;justify-content:space-between;align-items:center;cursor:pointer;padding:12px 16px;background:var(--surface);border:1px solid var(--border);border-radius:10px;margin-bottom:0;transition:all .2s}}
.collapsible-header:hover{{background:var(--surface2)}}
.collapsible-header .section-label{{margin-bottom:0}}
.collapsible-header .section-label::after{{display:none}}
.collapsible-toggle{{font-size:11px;color:var(--text2);display:flex;align-items:center;gap:6px}}
.collapsible-body{{display:none;margin-top:12px}}
.collapsible-body.open{{display:block}}
.collapsible-header.open{{border-radius:10px 10px 0 0;margin-bottom:0}}
.collapsible-header.open + .collapsible-body{{border:1px solid var(--border);border-top:none;border-radius:0 0 10px 10px;padding:16px}}

.branch-cards{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}}
@media(max-width:768px){{.branch-cards{{grid-template-columns:1fr}}}}
.branch-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden}}
.branch-card-header{{background:var(--surface2);padding:12px 16px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border)}}
.branch-card-name{{font-size:14px;font-weight:700}}
.branch-card-stats{{font-size:11px;color:var(--text2)}}
.branch-card-stats .num{{color:var(--text);font-weight:600}}
.branch-card table{{font-size:11px}}
.branch-card th,.branch-card td{{padding:8px 10px}}
.row-best{{border-left:3px solid var(--accent)}}

.action-section{{display:flex;flex-direction:column;gap:10px}}
.action-row{{background:var(--surface2);border-radius:8px;padding:14px 16px;border-left:3px solid var(--ab)}}
.action-type{{font-size:10px;font-weight:700;letter-spacing:.1em;color:var(--ab);margin-bottom:5px}}
.action-creative{{font-size:13px;font-weight:700;color:var(--text)}}
.action-branch{{font-size:11px;color:var(--accent2);margin-top:2px}}
.action-reason{{font-size:11px;color:var(--text2);margin-top:4px}}
.action-guide{{font-size:11px;color:var(--ab);margin-top:6px;font-weight:600}}

.proj-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
@media(max-width:500px){{.proj-grid{{grid-template-columns:1fr}}}}
.proj-card{{background:var(--surface2);border-radius:8px;padding:16px 18px}}
.proj-label{{font-size:10px;font-weight:700;letter-spacing:.08em;color:var(--text2);margin-bottom:6px;text-transform:uppercase}}
.proj-val{{font-size:22px;font-weight:900;font-family:'DM Mono',monospace}}
.proj-sub{{font-size:11px;color:var(--text2);margin-top:4px}}
.progress-wrap{{background:var(--border);border-radius:4px;height:6px;margin-top:8px;overflow:hidden}}
.progress-fill{{height:100%;border-radius:4px;background:var(--accent)}}

::-webkit-scrollbar{{width:5px;height:5px}}
::-webkit-scrollbar-thumb{{background:var(--border);border-radius:3px}}
.num{{font-family:'DM Mono',monospace}}
.text-good{{color:var(--accent)}} .text-bad{{color:var(--danger)}} .text-warn{{color:var(--warn)}} .text-muted{{color:var(--text2)}}
</style>
</head>
<body>

<div class="report-header">
  <div class="header-inner">
    <div class="brand">다이트한의원 · TikTok 광고 분석</div>
    <div class="header-top">
      <div>
        <div class="header-title">위클리 리포트</div>
        <div class="header-period">
          <div class="period-chip">분석 기간 <span id="period-this"></span></div>
          <div class="period-chip">비교 기간 <span id="period-prev"></span></div>
        </div>
      </div>
      <div class="issue-badge">발행 <span id="issue-date"></span></div>
    </div>
  </div>
</div>

<div class="container">

  <div class="section">
    <div class="section-label">이번 주 KPI — 전주 대비</div>
    <div class="kpi-strip" id="kpi-strip"></div>
  </div>

  <div class="section">
    <div class="section-label">핵심 인사이트 — 변화 원인 분석</div>
    <div class="insight-list" id="insight-list"></div>
  </div>

  <div class="section">
    <div class="section-label">소재 TIER 현황 (이번 주 기준 · 전주 대비)</div>
    <div class="card">
      <div class="tbl-wrap"><table id="tier-table"></table></div>
    </div>
  </div>

  <div class="section">
    <div class="collapsible-header" onclick="toggleCollapse(this)">
      <div class="section-label">소재 × 지점 성과 — 이번 주</div>
      <div class="collapsible-toggle"><span class="toggle-icon">▶</span> 펼치기</div>
    </div>
    <div class="collapsible-body">
      <div class="tbl-wrap"><table id="branch-creative-table"></table></div>
    </div>
  </div>

  <div class="section">
    <div class="collapsible-header" onclick="toggleCollapse(this)">
      <div class="section-label">지점별 소재 반응 — 이번 주</div>
      <div class="collapsible-toggle"><span class="toggle-icon">▶</span> 펼치기</div>
    </div>
    <div class="collapsible-body">
      <div class="branch-cards" id="branch-cards"></div>
    </div>
  </div>

  <div class="section">
    <div class="section-label">지점별 성과 — 전주 대비</div>
    <div class="two-col">
      <div class="card">
        <div class="card-title">CPA 전주 대비</div>
        <div class="card-desc">기준선: 주간 목표 CPA <span class="num" id="target-cpa-label"></span>원</div>
        <div style="position:relative;height:220px"><canvas id="branchCpaChart"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">CTR / CVR 전주 대비</div>
        <div class="card-desc">막대: CVR(%) 좌축 · 선: CTR(%) 우축</div>
        <div style="position:relative;height:220px"><canvas id="branchCvrChart"></canvas></div>
      </div>
    </div>
    <div class="card" style="margin-top:16px">
      <div class="tbl-wrap"><table id="branch-table"></table></div>
    </div>
  </div>

  <div class="section">
    <div class="section-label">소재 ON/OFF 액션플랜</div>
    <div class="action-section" id="action-list"></div>
  </div>

  <div class="section">
    <div class="section-label">이번 달 전환 목표 달성 예상</div>
    <div class="card">
      <div class="proj-grid" id="proj-grid"></div>
      <div style="margin-top:20px;position:relative;height:180px">
        <canvas id="dailyChart"></canvas>
      </div>
    </div>
  </div>

</div>

<script>
const D = {data_json};

const fmt = n => n==null||n===0 ? '-' : Math.round(n).toLocaleString('ko-KR');
const fmtp = n => n==null ? '-' : parseFloat(n).toFixed(2)+'%';
const TIER_COLOR = {{TIER1:'#4ade80',TIER2:'#60a5fa',TIER3:'#a78bfa',TIER4:'#f87171',LOW_VOLUME:'#6b7280',UNCLASSIFIED:'#8b5cf6'}};
const axisStyle = {{grid:{{color:'rgba(255,255,255,.04)'}},ticks:{{color:'#3d4559',font:{{size:10}}}}}};
const tooltipStyle = {{backgroundColor:'#13161e',titleColor:'#dde4f0',bodyColor:'#7a8499',borderColor:'#1f2535',borderWidth:1}};

// Header
document.getElementById('period-this').textContent = D.period_this_full;
document.getElementById('period-prev').textContent = D.period_prev;
document.getElementById('issue-date').textContent = D.issue_date;

// KPI
function buildKpi(){{
  const t=D.kpi_this, p=D.kpi_prev;
  const items=[
    {{label:'광고비', val:fmt(t.cost)+'원', diff:t.cost-p.cost, pct:((t.cost-p.cost)/p.cost*100).toFixed(1), unit:'원', good:'neutral'}},
    {{label:'전환수', val:fmt(t.conv)+'건', diff:t.conv-p.conv, pct:((t.conv-p.conv)/p.conv*100).toFixed(1), unit:'건', good:'up'}},
    {{label:'평균 CPA', val:fmt(t.cpa)+'원', diff:t.cpa-p.cpa, pct:((t.cpa-p.cpa)/p.cpa*100).toFixed(1), unit:'원', good:'down'}},
    {{label:'CTR', val:fmtp(t.ctr), diff:+(t.ctr-p.ctr).toFixed(2), pct:((t.ctr-p.ctr)/p.ctr*100).toFixed(1), unit:'%p', good:'up'}},
    {{label:'CVR', val:fmtp(t.cvr), diff:+(t.cvr-p.cvr).toFixed(2), pct:((t.cvr-p.cvr)/p.cvr*100).toFixed(1), unit:'%p', good:'up'}},
  ];
  document.getElementById('kpi-strip').innerHTML = items.map(item=>{{
    const isGood = item.good==='down' ? item.diff<0 : item.diff>0;
    const cls = item.good==='neutral' ? 'neutral' : (item.diff===0 ? 'neutral' : isGood ? 'good' : 'bad');
    const arrow = item.diff>0 ? '▲' : '▼';
    const sign = item.diff>0 ? '+' : '';
    const diffStr = item.unit==='%p'
      ? `${{arrow}} ${{sign}}${{item.diff}}%p (${{sign}}${{item.pct}}%)`
      : `${{arrow}} ${{sign}}${{Math.round(item.diff).toLocaleString()}}${{item.unit}} (${{sign}}${{item.pct}}%)`;
    return `<div class="kpi-cell">
      <div class="kpi-cell-label">${{item.label}}</div>
      <div class="kpi-val">${{item.val}}</div>
      <div class="kpi-diff ${{cls}}">${{diffStr}}</div>
    </div>`;
  }}).join('');
}}

// Insights
function buildInsights(){{
  if(!D.insights || D.insights.length===0){{
    document.getElementById('insight-list').innerHTML = '<div class="insight-card" style="--ic:#7a8499;background:#7a849908"><div class="ic-title">이번 주 특이사항 없음</div></div>';
    return;
  }}
  document.getElementById('insight-list').innerHTML = D.insights.map(ins=>`
    <div class="insight-card" style="--ic:${{ins.color}};background:${{ins.color}}08">
      <div class="ic-type">${{ins.type}}</div>
      <div class="ic-title">${{ins.title}}</div>
      ${{ins.points.map(p=>`<div class="ic-point">${{p}}</div>`).join('')}}
    </div>`).join('');
}}

// TIER Table
function buildTierTable(){{
  const torder={{TIER1:1,TIER2:2,TIER3:3,TIER4:4,LOW_VOLUME:5,UNCLASSIFIED:6}};
  const sorted=[...D.tier_list].sort((a,b)=>(torder[a.tier_this]||9)-(torder[b.tier_this]||9));
  const tierData = Object.fromEntries(D.tier_this.map(c=>[c.creative_name,c]));
  document.getElementById('tier-table').innerHTML=`
    <thead><tr><th>소재명</th><th>이번 주 TIER</th><th>전주</th><th>변동</th>
      <th>CPA</th><th>CTR</th><th>CVR</th><th>전환</th><th>집행지점</th></tr></thead>
    <tbody>${{sorted.map(t=>{{
      const d=tierData[t.creative_name]||{{}};
      const chgClass = t.change.includes('↑') ? 'change-up' : t.change.includes('↓') ? 'change-down' : t.change==='신규' ? 'change-new' : 'text-muted';
      return `<tr>
        <td class="td-name" title="${{t.creative_name}}">${{t.creative_name}}</td>
        <td><span class="tier-badge ${{t.tier_this}}">${{t.tier_this}}</span></td>
        <td>${{t.tier_prev?`<span class="tier-badge ${{t.tier_prev}}" style="opacity:.6">${{t.tier_prev}}</span>`:'<span class="text-muted">—</span>'}}</td>
        <td class="${{chgClass}}">${{t.change}}</td>
        <td class="num">${{d.CPA?fmt(d.CPA)+'원':'-'}}</td>
        <td class="num">${{d.CTR!=null?d.CTR.toFixed(2)+'%':'-'}}</td>
        <td class="num">${{d.CVR!=null?d.CVR.toFixed(2)+'%':'-'}}</td>
        <td class="num">${{d.총전환||0}}건</td>
        <td style="font-size:11px;color:var(--text2)">${{(d.지점목록||[]).join(', ')}}</td>
      </tr>`;
    }}).join('')}}</tbody>`;
}}

// Branch Creative Table (소재×지점)
function buildBranchCreativeTable(){{
  const data = D.branch_creative || [];
  if(data.length === 0){{
    document.getElementById('branch-creative-table').innerHTML = '<tbody><tr><td colspan="7" style="text-align:center;color:var(--text2)">데이터 없음</td></tr></tbody>';
    return;
  }}

  // rowspan 계산을 위해 소재명별 그룹핑
  const groups = {{}};
  data.forEach(r => {{
    if(!groups[r.creative_name]) groups[r.creative_name] = [];
    groups[r.creative_name].push(r);
  }});

  let rows = '';
  let prevName = '';
  data.forEach((r, idx) => {{
    const isFirst = r.creative_name !== prevName;
    const rowspan = isFirst ? groups[r.creative_name].length : 0;
    prevName = r.creative_name;

    const cpaColor = r.cpa_color === 'danger' ? 'text-bad' : r.cpa_color === 'good' ? 'text-good' : '';
    const cpaVal = r.CPA != null ? fmt(r.CPA) + '원' : '-';
    const shortTag = r.집행일수 < 3 ? ' <span style="color:var(--warn);font-size:10px">(단기)</span>' : '';

    rows += '<tr>';
    if(isFirst){{
      rows += `<td class="td-name" rowspan="${{rowspan}}" title="${{r.creative_name}}">${{r.creative_name}}</td>`;
    }}
    rows += `<td>${{r.branch}}${{shortTag}}</td>`;
    rows += `<td class="num ${{cpaColor}}">${{cpaVal}}</td>`;
    rows += `<td class="num">${{r.CTR != null ? r.CTR.toFixed(2) + '%' : '-'}}</td>`;
    rows += `<td class="num">${{r.CVR != null ? r.CVR.toFixed(2) + '%' : '-'}}</td>`;
    rows += `<td class="num">${{r.총전환}}건</td>`;
    rows += `<td class="num">${{(r.총비용/10000).toFixed(1)}}만</td>`;
    rows += '</tr>';
  }});

  document.getElementById('branch-creative-table').innerHTML = `
    <thead><tr><th>소재명</th><th>지점</th><th>CPA</th><th>CTR</th><th>CVR</th><th>전환</th><th>비용</th></tr></thead>
    <tbody>${{rows}}</tbody>`;
}}

// Toggle collapsible sections
function toggleCollapse(header){{
  const body = header.nextElementSibling;
  const toggle = header.querySelector('.collapsible-toggle');
  const icon = header.querySelector('.toggle-icon');
  const isOpen = body.classList.contains('open');

  if(isOpen){{
    body.classList.remove('open');
    header.classList.remove('open');
    toggle.innerHTML = '<span class="toggle-icon">▶</span> 펼치기';
  }} else {{
    body.classList.add('open');
    header.classList.add('open');
    toggle.innerHTML = '<span class="toggle-icon">▼</span> 접기';
  }}
}}

// Branch Cards (지점별 소재 반응)
function buildBranchCards(){{
  const data = D.branch_creative || [];
  if(data.length === 0){{
    document.getElementById('branch-cards').innerHTML = '<div style="color:var(--text2);text-align:center;padding:20px">데이터 없음</div>';
    return;
  }}

  // TIER 데이터 매핑
  const tierMap = {{}};
  (D.tier_this || []).forEach(t => {{ tierMap[t.creative_name] = t.TIER; }});

  // 지점별 그룹핑
  const byBranch = {{}};
  data.forEach(r => {{
    if(!byBranch[r.branch]) byBranch[r.branch] = [];
    byBranch[r.branch].push(r);
  }});

  // 지점별 CPA 오름차순 정렬
  Object.keys(byBranch).forEach(b => {{
    byBranch[b].sort((a,c) => (a.CPA || 999999) - (c.CPA || 999999));
  }});

  // 지점 순서 (VALID_BRANCHES 순)
  const branchOrder = ['서울', '일산', '대구', '천안', '부평', '창원', '수원'];
  const sortedBranches = branchOrder.filter(b => byBranch[b]);

  // 지점별 요약 (D.branch에서)
  const branchSummary = {{}};
  (D.branch || []).forEach(b => {{ branchSummary[b.branch] = b; }});

  let cards = '';
  sortedBranches.forEach(branch => {{
    const items = byBranch[branch];
    const summary = branchSummary[branch] || {{}};
    const branchCpa = summary.CPA ? fmt(summary.CPA) + '원' : '-';
    const branchConv = summary.총전환 || 0;

    let rows = '';
    items.forEach((r, idx) => {{
      const tier = tierMap[r.creative_name] || '-';
      const isBest = idx === 0 && r.CPA != null;
      const rowClass = isBest ? 'row-best' : '';
      const cpaVal = r.CPA != null ? fmt(r.CPA) + '원' : '-';
      const cvrVal = r.CVR != null ? r.CVR.toFixed(1) + '%' : '-';

      rows += `<tr class="${{rowClass}}">
        <td class="td-name" title="${{r.creative_name}}">${{r.creative_name}}</td>
        <td><span class="tier-badge ${{tier}}">${{tier}}</span></td>
        <td class="num">${{cpaVal}}</td>
        <td class="num">${{cvrVal}}</td>
        <td class="num">${{r.총전환}}건</td>
      </tr>`;
    }});

    cards += `<div class="branch-card">
      <div class="branch-card-header">
        <div class="branch-card-name">${{branch}}</div>
        <div class="branch-card-stats">CPA <span class="num">${{branchCpa}}</span> · 전환 <span class="num">${{branchConv}}건</span></div>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead><tr><th>소재명</th><th>TIER</th><th>CPA</th><th>CVR</th><th>전환</th></tr></thead>
          <tbody>${{rows}}</tbody>
        </table>
      </div>
    </div>`;
  }});

  document.getElementById('branch-cards').innerHTML = cards;
}}

// Branch Charts
function buildBranchCharts(){{
  document.getElementById('target-cpa-label').textContent = fmt(D.target_cpa);
  const br=[...D.branch].sort((a,b)=>(a.CPA||999999)-(b.CPA||999999));
  const labels=br.map(b=>b.branch);

  new Chart(document.getElementById('branchCpaChart'),{{
    type:'bar',
    data:{{labels,datasets:[
      {{label:'이번 주 CPA',data:br.map(b=>Math.round(b.CPA||0)),
        backgroundColor:br.map(b=>(b.CPA||0)<=D.target_cpa?'#4ade8033':'#f8717133'),
        borderColor:br.map(b=>(b.CPA||0)<=D.target_cpa?'#4ade80':'#f87171'),
        borderWidth:1.5,borderRadius:3}},
      {{label:'전주 CPA',data:br.map(b=>Math.round(b.CPA_prev||0)),
        backgroundColor:'rgba(255,255,255,.04)',borderColor:'#3d4559',
        borderWidth:1,borderRadius:3}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{labels:{{color:'#7a8499',font:{{size:10}}}}}},
        tooltip:{{...tooltipStyle,callbacks:{{label:ctx=>`${{ctx.dataset.label}}: ${{Math.round(ctx.parsed.y).toLocaleString('ko-KR')}}원`}}}}}},
      scales:{{x:{{...axisStyle}},y:{{...axisStyle,ticks:{{...axisStyle.ticks,callback:v=>Math.round(v/1000)+'천원'}}}}}}}}
  }});

  new Chart(document.getElementById('branchCvrChart'),{{
    type:'bar',
    data:{{labels,datasets:[
      {{label:'CVR 이번 주',data:br.map(b=>b.CVR||0),
        backgroundColor:'#60a5fa33',borderColor:'#60a5fa',borderWidth:1.5,borderRadius:3,yAxisID:'y'}},
      {{label:'CVR 전주',data:br.map(b=>b.CVR_prev||0),
        backgroundColor:'rgba(255,255,255,.04)',borderColor:'#3d4559',borderWidth:1,borderRadius:3,yAxisID:'y'}},
      {{label:'CTR 이번 주',data:br.map(b=>b.CTR||0),
        type:'line',borderColor:'#4ade80',pointBackgroundColor:'#4ade80',
        borderWidth:2,tension:.3,pointRadius:4,yAxisID:'y2'}},
      {{label:'CTR 전주',data:br.map(b=>b.CTR_prev||0),
        type:'line',borderColor:'#4ade8055',borderDash:[4,3],
        borderWidth:1.5,tension:.3,pointRadius:3,pointStyle:'circle',yAxisID:'y2'}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{labels:{{color:'#7a8499',font:{{size:10}},boxWidth:12}}}},
        tooltip:{{...tooltipStyle,callbacks:{{label:ctx=>`${{ctx.dataset.label}}: ${{ctx.parsed.y.toFixed(2)}}%`}}}}}},
      scales:{{
        x:{{...axisStyle}},
        y:{{...axisStyle,position:'left',title:{{display:true,text:'CVR (%)',color:'#3d4559',font:{{size:10}}}},
          ticks:{{...axisStyle.ticks,callback:v=>v+'%'}}}},
        y2:{{...axisStyle,position:'right',grid:{{display:false}},
          title:{{display:true,text:'CTR (%)',color:'#3d4559',font:{{size:10}}}},
          ticks:{{...axisStyle.ticks,callback:v=>v+'%'}}}}
      }}}}
  }});

  document.getElementById('branch-table').innerHTML=`
    <thead><tr><th>지점</th><th>CPA</th><th>전주대비CPA</th><th>CTR</th><th>전주대비CTR</th>
      <th>CVR</th><th>전주대비CVR</th><th>전환</th></tr></thead>
    <tbody>${{br.map(b=>{{
      const cd=b.CPA_diff||0, ctd=b.CTR_diff||0, cvd=b.CVR_diff||0;
      const cpaCls=cd<0?'text-good':cd>3000?'text-bad':'';
      const ctrCls=ctd>0?'text-good':ctd<-0.1?'text-bad':'';
      const cvrCls=cvd>0?'text-good':cvd<-0.5?'text-bad':'';
      return `<tr>
        <td style="font-weight:700">${{b.branch}}</td>
        <td class="num">${{fmt(b.CPA)}}원</td>
        <td class="num ${{cpaCls}}">${{cd>=0?'▲ +':'▼ '}}${{fmt(Math.abs(cd))}}원${{Math.abs(cd)>3000?' ⚠️':''}}</td>
        <td class="num">${{(b.CTR||0).toFixed(2)}}%</td>
        <td class="num ${{ctrCls}}">${{ctd>=0?'▲ +':'▼ '}}${{Math.abs(ctd).toFixed(2)}}%p</td>
        <td class="num">${{(b.CVR||0).toFixed(2)}}%</td>
        <td class="num ${{cvrCls}}">${{cvd>=0?'▲ +':'▼ '}}${{Math.abs(cvd).toFixed(2)}}%p${{Math.abs(cvd)>=0.5?' ⚠️':''}}</td>
        <td class="num">${{b.총전환||0}}건</td>
      </tr>`;
    }}).join('')}}</tbody>`;
}}

// Action
function buildAction(){{
  const items=[
    ...D.off_list.map(o=>({{
      type:'OFF 권고', color:'#f87171',
      creative: o.creative_name, branch: o.branch,
      reason: `CPA ${{fmt(o.CPA)}}원 — 지점 평균 ${{fmt(o.avg_cpa)}}원의 ${{o.ratio}}배 / CVR ${{o.CVR.toFixed(2)}}%`,
      guide: '해당 소재 OFF 전환 검토 (권고, 최종 결정은 클라이언트)'
    }})),
    ...D.on_list.map(o=>({{
      type:'ON 권고', color:'#4ade80',
      creative: o.creative_name, branch: o.missing.join(', '),
      reason: `이번 주 TIER1 · CPA ${{fmt(o.CPA)}}원 — 현재 미집행 지점에서 효과 기대`,
      guide: '해당 지점에 소재 추가 등록 검토 (권고, 최종 결정은 클라이언트)'
    }}))
  ];
  document.getElementById('action-list').innerHTML = items.length ? items.map(a=>`
    <div class="action-row" style="--ab:${{a.color}};background:${{a.color}}06">
      <div class="action-type">${{a.type}}</div>
      <div class="action-creative">${{a.creative}}</div>
      <div class="action-branch">${{a.type.includes('OFF')?'대상 지점: ':'대상 지점: '}}${{a.branch}}</div>
      <div class="action-reason">${{a.reason}}</div>
      <div class="action-guide">→ ${{a.guide}}</div>
    </div>`).join('')
  : '<div style="color:var(--text2);font-size:13px;padding:12px">이번 주 ON/OFF 권고 대상 없음</div>';
}}

// Projection
function buildProjection(){{
  const pct = Math.min(D.conv_pct, 100);
  const ppct = Math.min(D.proj_pct, 100);
  document.getElementById('proj-grid').innerHTML=`
    <div class="proj-card">
      <div class="proj-label">현재 누적 전환 (${{D.end_date_str}} 기준)</div>
      <div class="proj-val" style="color:${{D.conv_pct>=80?'#4ade80':'#fb923c'}}">${{fmt(D.conv_so_far)}}건</div>
      <div class="proj-sub">목표 ${{fmt(D.monthly_target_conv)}}건 대비 ${{D.conv_pct}}%</div>
      <div class="progress-wrap"><div class="progress-fill" style="width:${{pct}}%;background:${{D.conv_pct>=80?'#4ade80':'#fb923c'}}"></div></div>
    </div>
    <div class="proj-card">
      <div class="proj-label">현재 페이스 기준 월말 예상</div>
      <div class="proj-val" style="color:${{D.proj_pct>=100?'#4ade80':'#f87171'}}">${{fmt(D.proj_conv)}}건</div>
      <div class="proj-sub">목표 ${{fmt(D.monthly_target_conv)}}건 대비 ${{D.proj_pct}}% ${{D.proj_pct>=100?'달성 예상':'미달 예상'}}</div>
      <div class="progress-wrap"><div class="progress-fill" style="width:${{ppct}}%;background:${{D.proj_pct>=100?'#4ade80':'#f87171'}}"></div></div>
    </div>`;

  const labels=D.daily.map(d=>d.date_str);
  new Chart(document.getElementById('dailyChart'),{{
    type:'line',
    data:{{labels,datasets:[
      {{label:'일별 전환',data:D.daily.map(d=>d.conv),borderColor:'#4ade80',
        backgroundColor:'#4ade8011',fill:true,tension:.3,pointRadius:2,borderWidth:2}},
      {{label:'일별 CPA (÷1000)',data:D.daily.map(d=>Math.round((d.cpa||0)/1000)),
        borderColor:'#60a5fa',tension:.3,pointRadius:2,borderWidth:1.5,borderDash:[]}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{labels:{{color:'#7a8499',font:{{size:10}}}}}},tooltip:tooltipStyle}},
      scales:{{x:{{...axisStyle}},y:{{...axisStyle}}}}}}
  }});
}}

buildKpi(); buildInsights(); buildTierTable(); buildBranchCreativeTable(); buildBranchCards();
buildBranchCharts(); buildAction(); buildProjection();
</script>
</body>
</html>'''

    return html


if __name__ == "__main__":
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "input/tiktok_raw.csv"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    target_date = sys.argv[3] if len(sys.argv) > 3 else None
    build_weekly_html(output_dir, csv_path, target_date)
