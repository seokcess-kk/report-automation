"""
데일리 리포트 생성 (카카오톡 친화 이모지+리스트 형식)
내부용 - 매일 아침 발행

입력: input/tiktok_raw.csv 또는 output/data/YYYYMMDD/parsed.parquet
출력: output/daily/YYYYMMDD/tiktok_daily_YYYYMMDD.txt
스냅샷: output/daily/daily_snapshot.json
"""
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import calendar
import sys

# 공용 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import (
    VALID_BRANCHES, MONTHLY_BUDGET, MONTHLY_TARGET_CONV, TOTAL_MONTHLY_BUDGET,
    strip_date_code, load_target_cpa, parse_branch,
    calc_kpi, calc_branch_kpi,
    fmt, fmt_man, fmt_pct,
)


def load_data(csv_path: str = None, parquet_path: str = None) -> pd.DataFrame:
    """데이터 로드 (parquet 우선, 없으면 CSV)"""

    if parquet_path and os.path.exists(parquet_path):
        df = pd.read_parquet(parquet_path)
        if 'stat_date' in df.columns:
            df['date'] = pd.to_datetime(df['stat_date'])
        elif 'date' not in df.columns:
            raise ValueError("parquet에 date 또는 stat_date 컬럼 필요")
        return df

    if csv_path and os.path.exists(csv_path):
        df = pd.read_csv(csv_path, dtype={'광고 ID': str}, encoding='utf-8-sig')

        col_map = {
            # 한글 헤더
            '클릭수(목적지)': 'clicks',
            '노출수': 'impressions',
            '전환수': 'conversions',
            '비용': 'cost',
            '랜딩 페이지 조회(웹사이트)': 'landing_views',
            '일별': 'date',
            '나이': 'age_group',
            '광고 이름': 'ad_name',
            '광고 ID': 'ad_id',
            # 영문 헤더
            'Clicks (destination)': 'clicks',
            'Impressions': 'impressions',
            'Conversions': 'conversions',
            'Cost': 'cost',
            'By Day': 'date',
            'Ad name': 'ad_name',
            'Ad ID': 'ad_id',
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        for col in ['clicks', 'impressions', 'conversions', 'cost', 'landing_views']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['is_off'] = df['ad_name'].str.lower().str.endswith('_off')

        # parse_branch 공용 함수 사용
        df['branch'] = df['ad_name'].apply(parse_branch)

        def parse_creative(name):
            if pd.isna(name):
                return None
            name = str(name).strip()
            is_off = name.lower().endswith('_off')
            clean = name[:-4] if is_off else name
            parts = clean.split('_')
            if len(parts) >= 4:
                return '_'.join(parts[3:])
            return clean

        df['creative_name'] = df['ad_name'].apply(parse_creative)

        return df

    raise FileNotFoundError("CSV 또는 parquet 파일을 찾을 수 없습니다")


def load_snapshot(snapshot_path: str) -> dict:
    """스냅샷 로드"""
    if os.path.exists(snapshot_path):
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_snapshot(snapshot_path: str, snapshot: dict, today_str: str, today_data: dict):
    """스냅샷 저장 (최근 30일만 유지)"""
    snapshot[today_str] = today_data

    cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    snapshot = {k: v for k, v in snapshot.items() if k >= cutoff}

    os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
    with open(snapshot_path, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def calc_week_ago_kpi(df: pd.DataFrame, target_date) -> dict:
    """7일 전 KPI 계산"""
    week_ago = target_date - timedelta(days=7)
    df_week_ago = df[df['date'] == week_ago]
    if len(df_week_ago) == 0:
        return None
    return calc_kpi(df_week_ago)


def detect_anomalies(df_daily: pd.DataFrame, branch_cum: dict, prev_branch_cum: dict, target_cpa: dict) -> list:
    """이상 감지 (누적 CPA 기준)"""
    anomalies = []
    df_on = df_daily[~df_daily['is_off']]

    # 1. 전환 0건 AND 어제 비용 > 50,000원 소재 (하루치 예외)
    creative_stats = df_on.groupby(['branch', 'creative_name']).agg(
        cost=('cost', 'sum'),
        conv=('conversions', 'sum'),
    ).reset_index()

    for _, row in creative_stats.iterrows():
        if row['conv'] == 0 and row['cost'] >= 50000:
            creative_display = strip_date_code(row['creative_name'])[:30] if row['creative_name'] else '-'
            anomalies.append({
                'type': 'no_conv',
                'branch': row['branch'],
                'creative': creative_display,
                'message': f"어제 전환 0건, 비용 {int(row['cost']):,}원",
                'severity': 'alert'
            })

    # 2. 지점 누적 CPA > 목표CPA × 1.8 → 🚨
    for branch, kpi in branch_cum.items():
        if kpi.get('cpa') is None:
            continue
        target = target_cpa.get(branch, 25000)
        if kpi['cpa'] > target * 1.8:
            anomalies.append({
                'type': 'branch_high_cpa',
                'branch': branch,
                'creative': None,
                'message': f"누적CPA {int(kpi['cpa']):,}원 (목표 {int(target):,}원의 {round(kpi['cpa']/target, 1)}배)",
                'severity': 'alert'
            })
        elif kpi['cpa'] > target * 1.3:
            anomalies.append({
                'type': 'branch_warn_cpa',
                'branch': branch,
                'creative': None,
                'message': f"누적CPA {int(kpi['cpa']):,}원 (목표 {int(target):,}원의 {round(kpi['cpa']/target, 1)}배)",
                'severity': 'warn'
            })

    # 3. 누적 CPA 전일 대비 10% 이상 급등 → ⚠️
    if prev_branch_cum:
        for branch, kpi in branch_cum.items():
            prev = prev_branch_cum.get(branch, {})
            prev_cpa = prev.get('cpa')
            curr_cpa = kpi.get('cpa')
            if prev_cpa and curr_cpa and prev_cpa > 0:
                change_pct = (curr_cpa - prev_cpa) / prev_cpa * 100
                if change_pct >= 10:
                    anomalies.append({
                        'type': 'cum_cpa_spike',
                        'branch': branch,
                        'creative': None,
                        'message': f"누적CPA 전일비 +{change_pct:.1f}% ({int(prev_cpa):,}원 → {int(curr_cpa):,}원)",
                        'severity': 'warn'
                    })

    return anomalies[:10]


def analyze_dod_anomaly(df: pd.DataFrame, yesterday, day_before) -> list:
    """전일비 이상치 감지 시 지점별/소재별 원인 분석

    이상치 기준: 전환 감소 30% 이상 AND 5건 이상 감소
    """
    df_today = df[df['date'] == yesterday]
    df_prev = df[df['date'] == day_before]

    if len(df_today) == 0 or len(df_prev) == 0:
        return []

    conv_today = df_today['conversions'].sum()
    conv_prev = df_prev['conversions'].sum()
    cost_today = df_today['cost'].sum()
    cost_prev = df_prev['cost'].sum()

    if conv_prev == 0:
        return []

    conv_diff = conv_today - conv_prev
    conv_pct = conv_diff / conv_prev * 100

    # 이상치 기준: 30% 이상 감소 AND 5건 이상 차이
    if conv_diff >= 0 or abs(conv_pct) < 30 or abs(conv_diff) < 5:
        return []

    lines = []
    lines.append("📉 전일비 이상 감지")
    lines.append(f"• 전환: {int(conv_prev)}건 -> {int(conv_today)}건 ({int(conv_diff):+d}건, {conv_pct:+.0f}%)")
    lines.append(f"• 광고비: {fmt_man(cost_prev)} -> {fmt_man(cost_today)}")
    lines.append("")

    # 지점별 원인 분석
    b_prev = df_prev.groupby('branch')['conversions'].sum()
    b_today = df_today.groupby('branch')['conversions'].sum()
    b_cost_prev = df_prev.groupby('branch')['cost'].sum()
    b_cost_today = df_today.groupby('branch')['cost'].sum()

    branch_diffs = []
    for branch in VALID_BRANCHES:
        prev_c = b_prev.get(branch, 0)
        today_c = b_today.get(branch, 0)
        diff = today_c - prev_c
        prev_cost = b_cost_prev.get(branch, 0)
        today_cost = b_cost_today.get(branch, 0)
        if diff != 0 or prev_c > 0 or today_c > 0:
            branch_diffs.append((branch, int(prev_c), int(today_c), int(diff), prev_cost, today_cost))

    branch_diffs.sort(key=lambda x: x[3])

    lines.append("[지점별 변화]")
    for branch, prev_c, today_c, diff, prev_cost, today_cost in branch_diffs:
        sign = f"{diff:+d}"
        cpa_prev = f"{prev_cost/prev_c/10000:.1f}만" if prev_c > 0 else "-"
        cpa_today = f"{today_cost/today_c/10000:.1f}만" if today_c > 0 else "-"
        marker = " ⚠" if diff <= -3 or (diff == 0 and today_cost > prev_cost * 1.5) else ""
        lines.append(f"  {branch}: {prev_c} -> {today_c}건 ({sign}) | CPA: {cpa_prev} -> {cpa_today}{marker}")
    lines.append("")

    # 소재별 원인 분석
    def _creative_agg(d):
        return d.groupby('creative_name').agg(
            conv=('conversions', 'sum'),
            clicks=('clicks', 'sum'),
            cost=('cost', 'sum'),
        ).reset_index()

    c_prev = _creative_agg(df_prev)
    c_today = _creative_agg(df_today)
    merged = c_prev.merge(c_today, on='creative_name', suffixes=('_prev', '_today'), how='outer').fillna(0)
    merged['conv_diff'] = merged['conv_today'] - merged['conv_prev']

    down = merged[merged['conv_diff'] < 0].sort_values('conv_diff')
    if len(down) > 0:
        lines.append("[감소 소재]")
        for _, r in down.head(5).iterrows():
            name = strip_date_code(r['creative_name'])[:35] if r['creative_name'] else '-'
            cvr_prev = r['conv_prev'] / r['clicks_prev'] * 100 if r['clicks_prev'] > 0 else 0
            cvr_today = r['conv_today'] / r['clicks_today'] * 100 if r['clicks_today'] > 0 else 0
            lines.append(f"  {name}: {int(r['conv_prev'])} -> {int(r['conv_today'])}건 ({int(r['conv_diff']):+d}) | CVR: {cvr_prev:.0f}% -> {cvr_today:.0f}%")
        lines.append("")

    up = merged[merged['conv_diff'] > 0].sort_values('conv_diff', ascending=False)
    if len(up) > 0:
        lines.append("[증가 소재]")
        for _, r in up.head(3).iterrows():
            name = strip_date_code(r['creative_name'])[:35] if r['creative_name'] else '-'
            lines.append(f"  {name}: {int(r['conv_prev'])} -> {int(r['conv_today'])}건 ({int(r['conv_diff']):+d})")
        lines.append("")

    # 인사이트 생성
    insights = _generate_anomaly_insights(
        conv_diff, conv_pct, cost_today, cost_prev,
        branch_diffs, down, up, df, yesterday,
    )
    if insights:
        lines.append("[분석 인사이트]")
        for insight in insights:
            lines.append(f"  {insight}")
        lines.append("")

    return lines


def _generate_anomaly_insights(
    conv_diff, conv_pct, cost_today, cost_prev,
    branch_diffs, down_creatives, up_creatives, df, yesterday,
) -> list:
    """이상치 패턴을 분석하여 원인 추정 및 액션 인사이트 생성"""
    insights = []

    # --- 1. 감소 집중도 분석 ---
    # 지점: 감소분의 대부분이 소수 지점에 집중되었는지
    total_drop = sum(abs(d[3]) for d in branch_diffs if d[3] < 0)
    worst_branches = [(b, abs(d)) for b, _, _, d, _, _ in branch_diffs if d < 0]
    worst_branches.sort(key=lambda x: x[1], reverse=True)

    if total_drop > 0 and len(worst_branches) >= 1:
        top_branch_drop = sum(x[1] for x in worst_branches[:2])
        top_pct = top_branch_drop / total_drop * 100
        if top_pct >= 70:
            names = ', '.join(x[0] for x in worst_branches[:2])
            insights.append(f"-> {names} 지점에서 감소분의 {top_pct:.0f}% 집중 발생")

    # 소재: 특정 소재군이 감소를 주도했는지
    if len(down_creatives) > 0:
        top_creative = down_creatives.iloc[0]
        top_name = strip_date_code(top_creative['creative_name'])[:30] if top_creative['creative_name'] else '-'
        top_drop = abs(int(top_creative['conv_diff']))
        top_share = top_drop / abs(conv_diff) * 100 if conv_diff != 0 else 0

        # 같은 소재 시리즈 감지 (앞 10글자 동일)
        if len(down_creatives) >= 2:
            prefix = str(down_creatives.iloc[0]['creative_name'])[:10]
            series = down_creatives[down_creatives['creative_name'].str[:10] == prefix]
            if len(series) >= 2:
                series_drop = abs(int(series['conv_diff'].sum()))
                series_share = series_drop / abs(conv_diff) * 100 if conv_diff != 0 else 0
                series_name = strip_date_code(prefix)[:20]
                insights.append(f"-> '{series_name}' 시리즈 {len(series)}개 소재에서 -{series_drop}건 ({series_share:.0f}%) 집중")

                # 소재 피로도 판단: 클릭은 유지되는데 CVR만 하락
                clicks_prev = series['clicks_prev'].sum()
                clicks_today = series['clicks_today'].sum()
                if clicks_prev > 0:
                    click_change = (clicks_today - clicks_prev) / clicks_prev * 100
                    if abs(click_change) < 20:
                        # 소재 코드에서 날짜 추출하여 운영 기간 추정
                        raw_name = str(down_creatives.iloc[0]['creative_name'])
                        parts = raw_name.rsplit('_', 1)
                        if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 6:
                            code = parts[1]
                            try:
                                created = pd.to_datetime(f"20{code[:2]}-{code[2:4]}-{code[4:6]}")
                                days_running = (yesterday - created).days
                                if days_running >= 30:
                                    insights.append(f"-> 클릭 유지 + CVR 급락 패턴 -> 소재 피로도 의심 (운영 약 {days_running}일)")
                                else:
                                    insights.append(f"-> 클릭 유지 + CVR 급락 -> 랜딩페이지/외부요인 점검 필요")
                            except Exception:
                                insights.append(f"-> 클릭 유지 + CVR 급락 패턴 -> 소재 피로도 또는 랜딩페이지 점검 필요")
                        else:
                            insights.append(f"-> 클릭 유지 + CVR 급락 패턴 -> 소재 피로도 또는 랜딩페이지 점검 필요")
                    elif click_change < -20:
                        insights.append(f"-> 클릭도 {click_change:+.0f}% 감소 -> 노출 축소/경쟁 심화 가능성")
            elif top_share >= 40:
                insights.append(f"-> '{top_name}' 단일 소재에서 -{top_drop}건 ({top_share:.0f}%) 발생")

    # --- 2. 비용 효율 분석 ---
    cost_change_pct = (cost_today - cost_prev) / cost_prev * 100 if cost_prev > 0 else 0
    if cost_change_pct > 10 and conv_pct < -30:
        insights.append(f"-> 비용 증가(+{cost_change_pct:.0f}%) 대비 전환 급감 -> 전체 효율 악화")
    elif abs(cost_change_pct) <= 10 and conv_pct < -30:
        insights.append(f"-> 비용 유사 수준에서 전환만 급감 -> 소재/랜딩 측 이슈 가능성")

    # --- 3. 비용 증가 대비 전환 없는 지점 (창원 같은 케이스) ---
    for branch, prev_c, today_c, diff, prev_cost, today_cost in branch_diffs:
        if diff == 0 and today_c > 0 and prev_cost > 0 and today_cost > prev_cost * 1.4:
            cost_up = (today_cost - prev_cost) / prev_cost * 100
            insights.append(f"-> {branch}: 비용 +{cost_up:.0f}% 증가했으나 전환 동일 -> 비효율 소재 예산 점검")

    # --- 4. 긍정 신호 ---
    if len(up_creatives) > 0:
        best = up_creatives.iloc[0]
        best_name = strip_date_code(best['creative_name'])[:25] if best['creative_name'] else '-'
        best_gain = int(best['conv_diff'])
        # 증가 소재가 어느 지점에서 잘 되었는지
        insights.append(f"-> '{best_name}' 소재 선전(+{best_gain}건) -> 타 지점 확산 테스트 검토")

    return insights[:6]


def analyze_zero_conv_branches(
    branch_daily: dict, prev_branch_data: dict,
    df: pd.DataFrame, yesterday, day_before,
) -> list:
    """전환 0건 지점에 대해 전일 대비 변화 코멘트 생성"""
    lines = []
    zero_branches = []

    for branch in VALID_BRANCHES:
        daily = branch_daily.get(branch, {})
        if daily.get('conv', 0) == 0 and daily.get('cost', 0) > 0:
            zero_branches.append(branch)

    if not zero_branches:
        return []

    lines.append("🔍 전환 0건 지점 분석")

    # 전일 지점 데이터: 스냅샷 우선, 없으면 CSV fallback
    for branch in zero_branches:
        today_cost = branch_daily.get(branch, {}).get('cost', 0)

        # 전일 데이터 조회
        prev_b = prev_branch_data.get(branch, {})
        prev_daily = prev_b.get('daily', {})
        prev_conv = prev_daily.get('conv', 0)
        prev_cost = prev_daily.get('cost', 0)
        prev_cvr = prev_daily.get('cvr')

        # 스냅샷에 전일 데이터 없으면 CSV fallback
        if not prev_daily:
            df_prev_branch = df[(df['date'] == day_before) & (df['branch'] == branch)]
            if len(df_prev_branch) > 0:
                prev_conv = int(df_prev_branch['conversions'].sum())
                prev_cost = df_prev_branch['cost'].sum()
                clicks = df_prev_branch['clicks'].sum()
                prev_cvr = (prev_conv / clicks * 100) if clicks > 0 else 0

        # 비용 변화
        if prev_cost > 0:
            cost_change_pct = (today_cost - prev_cost) / prev_cost * 100
            cost_arrow = '▲' if cost_change_pct > 0 else '▼'
            cost_str = f"비용 {fmt_man(prev_cost)}→{fmt_man(today_cost)} ({cost_arrow}{abs(cost_change_pct):.0f}%)"
        else:
            cost_str = f"비용 {fmt_man(today_cost)}"

        # 전환 변화
        if prev_conv > 0:
            conv_str = f"전환 {prev_conv}건→0건"
        else:
            conv_str = "전환 0건 (전일도 0건)"

        # CVR 변화
        cvr_str = ""
        if prev_cvr and prev_cvr > 0:
            cvr_str = f" | 전일CVR {prev_cvr:.1f}%→0%"

        lines.append(f"• {branch}: {conv_str} | {cost_str}{cvr_str}")

        # 원인 추정 코멘트
        if prev_cost > 0 and today_cost > prev_cost * 1.2:
            lines.append(f"  → 비용 증가에도 전환 없음 - 소재 효율 점검 필요")
        elif prev_cost > 0 and today_cost < prev_cost * 0.5:
            lines.append(f"  → 비용 대폭 감소 - 노출/예산 제한 확인")
        elif prev_conv >= 2:
            lines.append(f"  → 전일 대비 급감 - 소재 피로도 또는 타겟 이슈 점검")
        elif prev_conv == 1:
            lines.append(f"  → 전일 1건 수준으로 일시적 변동 가능성")
        else:
            lines.append(f"  → 지속적 전환 부진 - 소재 교체 또는 예산 재배분 검토")

    return lines


def analyze_notable_items(df: pd.DataFrame, yesterday, day_before) -> list:
    """특이사항 분석 (내용 없으면 빈 리스트 반환)"""
    lines = []
    df_today = df[df['date'] == yesterday]
    df_prev = df[df['date'] == day_before]
    df_on_today = df_today[~df_today['is_off']]
    df_on_prev = df_prev[~df_prev['is_off']]

    # ── 1. 전일 대비 급변동 소재 (개별 소재 단위) ──
    if len(df_on_today) > 0 and len(df_on_prev) > 0:
        def _agg(d):
            return d.groupby('creative_name').agg(
                cost=('cost', 'sum'), conv=('conversions', 'sum'),
                clicks=('clicks', 'sum'),
            ).reset_index()

        c_today = _agg(df_on_today)
        c_prev = _agg(df_on_prev)
        merged = c_prev.merge(c_today, on='creative_name', suffixes=('_prev', '_today'), how='inner')
        # CPA 계산
        merged['cpa_prev'] = merged.apply(lambda r: r['cost_prev'] / r['conv_prev'] if r['conv_prev'] > 0 else None, axis=1)
        merged['cpa_today'] = merged.apply(lambda r: r['cost_today'] / r['conv_today'] if r['conv_today'] > 0 else None, axis=1)
        # CVR 계산
        merged['cvr_prev'] = merged.apply(lambda r: r['conv_prev'] / r['clicks_prev'] * 100 if r['clicks_prev'] > 0 else 0, axis=1)
        merged['cvr_today'] = merged.apply(lambda r: r['conv_today'] / r['clicks_today'] * 100 if r['clicks_today'] > 0 else 0, axis=1)

        movers = []
        for _, r in merged.iterrows():
            # 전환 2건 이상 변동만
            conv_diff = r['conv_today'] - r['conv_prev']
            if abs(conv_diff) < 2:
                continue
            # CPA 급변 (50% 이상)
            cpa_change = None
            if r['cpa_prev'] and r['cpa_today'] and r['cpa_prev'] > 0:
                cpa_change = (r['cpa_today'] - r['cpa_prev']) / r['cpa_prev'] * 100
            cvr_diff = r['cvr_today'] - r['cvr_prev']
            if (cpa_change and abs(cpa_change) >= 50) or abs(conv_diff) >= 3:
                movers.append({
                    'name': strip_date_code(r['creative_name'])[:30] if r['creative_name'] else '-',
                    'conv_diff': int(conv_diff),
                    'cpa_prev': r['cpa_prev'], 'cpa_today': r['cpa_today'],
                    'cvr_prev': r['cvr_prev'], 'cvr_today': r['cvr_today'],
                    'cpa_change': cpa_change,
                })
        movers.sort(key=lambda x: abs(x['conv_diff']), reverse=True)
        if movers:
            lines.append("⚡ 급변동 소재")
            for m in movers[:3]:
                cpa_str = ""
                has_prev = pd.notna(m['cpa_prev'])
                has_today = pd.notna(m['cpa_today'])
                cpa_prev_s = f"{m['cpa_prev']/10000:.1f}만" if has_prev else "-"
                cpa_today_s = f"{m['cpa_today']/10000:.1f}만" if has_today else "-"
                if has_prev or has_today:
                    cpa_str = f" | CPA {cpa_prev_s}→{cpa_today_s}"
                sign = '+' if m['conv_diff'] > 0 else ''
                lines.append(f"  {m['name']}: 전환 {sign}{m['conv_diff']}건{cpa_str}")

    # ── 1-2. 전환 이상 (지점 + 소재 단위, 전일비 & 평균 대비) ──
    month_start_ts = pd.Timestamp(yesterday.year, yesterday.month, 1)
    df_month_on = df[(df['date'] >= month_start_ts) & (df['date'] <= yesterday) & (~df['is_off'])]
    conv_anomaly_lines = []

    # (A) 지점별 전환 전일비 급변동
    if len(df_on_today) > 0 and len(df_on_prev) > 0:
        b_today = df_today.groupby('branch')['conversions'].sum()
        b_prev = df_prev.groupby('branch')['conversions'].sum()
        branch_moves = []
        for branch in VALID_BRANCHES:
            tc = int(b_today.get(branch, 0))
            pc = int(b_prev.get(branch, 0))
            diff = tc - pc
            # 급증: +5건 이상 또는 전일 대비 3배 이상(전일 2건+)
            if diff >= 5 or (pc >= 2 and tc >= pc * 3):
                branch_moves.append((branch, pc, tc, diff, '↑급증'))
            # 급감: -5건 이상 또는 전일 대비 1/3 이하(전일 3건+)
            elif diff <= -5 or (pc >= 3 and tc <= pc / 3):
                branch_moves.append((branch, pc, tc, diff, '↓급감'))
        branch_moves.sort(key=lambda x: abs(x[3]), reverse=True)
        for branch, pc, tc, diff, tag in branch_moves[:4]:
            sign = '+' if diff > 0 else ''
            conv_anomaly_lines.append(f"  [{branch}] {pc}건→{tc}건 ({sign}{diff}) {tag}")

    # (B) 소재별 누적 평균 대비 급증/공백
    if len(df_month_on) > 0 and len(df_on_today) > 0:
        df_before_today = df_month_on[df_month_on['date'] < yesterday]
        if len(df_before_today) > 0:
            days_count = df_before_today['date'].nunique()
            if days_count >= 3:
                avg_conv = df_before_today.groupby('creative_name')['conversions'].sum().reset_index()
                avg_conv.columns = ['creative_name', 'total_conv']
                avg_conv['daily_avg'] = avg_conv['total_conv'] / days_count

                today_conv = df_on_today.groupby('creative_name')['conversions'].sum().reset_index()
                today_conv.columns = ['creative_name', 'today_conv']

                conv_check = avg_conv.merge(today_conv, on='creative_name', how='outer').fillna(0)

                spikes = []
                blanks = []

                for _, r in conv_check.iterrows():
                    avg = r['daily_avg']
                    today_c = r['today_conv']
                    if avg >= 1 and today_c >= avg * 3 and today_c >= 3:
                        dname = strip_date_code(r['creative_name'])[:30] if r['creative_name'] else '-'
                        spikes.append((dname, avg, int(today_c)))
                    elif avg >= 1 and today_c == 0:
                        dname = strip_date_code(r['creative_name'])[:30] if r['creative_name'] else '-'
                        blanks.append((dname, avg))

                spikes.sort(key=lambda x: x[2], reverse=True)
                blanks.sort(key=lambda x: x[1], reverse=True)

                for name, avg, tc in spikes[:3]:
                    conv_anomaly_lines.append(f"  {name}: 평균 {avg:.1f}건→어제 {tc}건 (↑급증)")
                for name, avg in blanks[:3]:
                    conv_anomaly_lines.append(f"  {name}: 평균 {avg:.1f}건→어제 0건 (공백)")

    if conv_anomaly_lines:
        if lines:
            lines.append("")
        lines.append("🔔 전환 이상")
        lines.extend(conv_anomaly_lines)

    # ── 2. 이상치 소재 (비용 과다 or 효율 극단) ──
    if len(df_on_today) > 0:
        cr = df_on_today.groupby('creative_name').agg(
            cost=('cost', 'sum'), conv=('conversions', 'sum'), clicks=('clicks', 'sum'),
        ).reset_index()
        cr = cr[cr['cost'] >= 30000]  # 최소 비용 필터
        if len(cr) > 0:
            cr['cpa'] = cr.apply(lambda r: r['cost'] / r['conv'] if r['conv'] > 0 else None, axis=1)
            avg_cpa = cr.loc[cr['conv'] > 0, 'cpa'].median() if cr['conv'].sum() > 0 else None

            outliers = []
            for _, r in cr.iterrows():
                # 비용 높은데 전환 0
                if r['conv'] == 0 and r['cost'] >= 80000:
                    outliers.append(('waste', r['creative_name'], r['cost'], 0, None))
                # CPA가 중앙값 대비 2.5배 이상
                elif avg_cpa and r['cpa'] and r['cpa'] > avg_cpa * 2.5:
                    outliers.append(('high_cpa', r['creative_name'], r['cost'], int(r['conv']), r['cpa']))
                # CPA가 중앙값 대비 0.4배 이하 (초고효율)
                elif avg_cpa and r['cpa'] and r['cpa'] < avg_cpa * 0.4 and r['conv'] >= 2:
                    outliers.append(('star', r['creative_name'], r['cost'], int(r['conv']), r['cpa']))

            if outliers:
                if lines:
                    lines.append("")
                lines.append("🎯 이상치 소재")
                for otype, name, cost, conv, cpa in outliers[:3]:
                    dname = strip_date_code(name)[:30] if name else '-'
                    if otype == 'waste':
                        lines.append(f"  {dname}: 비용 {cost/10000:.1f}만 / 전환 0건 ⚠")
                    elif otype == 'high_cpa':
                        lines.append(f"  {dname}: CPA {cpa/10000:.1f}만 (중앙값 {avg_cpa/10000:.1f}만의 {cpa/avg_cpa:.1f}배) ⚠")
                    elif otype == 'star':
                        lines.append(f"  {dname}: CPA {cpa/10000:.1f}만 / {conv}건 ★ 확산 검토")

    # ── 3. 신규 소재 성과 (최근 3일 내 첫 집행) ──
    month_start = pd.Timestamp(yesterday.year, yesterday.month, 1)
    df_month = df[(df['date'] >= month_start) & (df['date'] <= yesterday) & (~df['is_off'])]
    if len(df_month) > 0:
        first_seen = df_month.groupby('creative_name')['date'].min().reset_index()
        first_seen.columns = ['creative_name', 'first_date']
        cutoff = yesterday - timedelta(days=2)
        new_creatives = first_seen[first_seen['first_date'] >= cutoff]['creative_name'].tolist()

        if new_creatives:
            new_data = df_month[df_month['creative_name'].isin(new_creatives)]
            new_agg = new_data.groupby('creative_name').agg(
                cost=('cost', 'sum'), conv=('conversions', 'sum'),
                clicks=('clicks', 'sum'), impr=('impressions', 'sum'),
            ).reset_index()
            new_agg = new_agg[new_agg['cost'] >= 10000]  # 최소 집행 필터
            new_agg['ctr'] = new_agg.apply(lambda r: r['clicks'] / r['impr'] * 100 if r['impr'] > 0 else 0, axis=1)
            new_agg['cvr'] = new_agg.apply(lambda r: r['conv'] / r['clicks'] * 100 if r['clicks'] > 0 else 0, axis=1)
            new_agg['cpa'] = new_agg.apply(lambda r: r['cost'] / r['conv'] if r['conv'] > 0 else None, axis=1)

            if len(new_agg) > 0:
                if lines:
                    lines.append("")
                lines.append("🆕 신규 소재")
                new_agg = new_agg.sort_values('cost', ascending=False)
                for _, r in new_agg.head(3).iterrows():
                    dname = strip_date_code(r['creative_name'])[:30] if r['creative_name'] else '-'
                    cpa_str = f"CPA {r['cpa']/10000:.1f}만" if r['cpa'] else "전환 대기"
                    lines.append(f"  {dname}: CTR {r['ctr']:.1f}% / CVR {r['cvr']:.1f}% / {cpa_str}")

    # ── 4. 지점 간 편차 (동일 소재, 지점별 성과 차이) ──
    df_cum_on = df[(df['date'] >= month_start) & (df['date'] <= yesterday) & (~df['is_off'])]
    if len(df_cum_on) > 0:
        cb = df_cum_on.groupby(['creative_name', 'branch']).agg(
            cost=('cost', 'sum'), conv=('conversions', 'sum'), clicks=('clicks', 'sum'),
        ).reset_index()
        # 2개 이상 지점에서 집행 + 최소 클릭
        cb = cb[cb['clicks'] >= 20]
        multi = cb.groupby('creative_name').filter(lambda x: len(x) >= 2)

        if len(multi) > 0:
            multi['cvr'] = multi.apply(lambda r: r['conv'] / r['clicks'] * 100 if r['clicks'] > 0 else 0, axis=1)
            multi['cpa'] = multi.apply(lambda r: r['cost'] / r['conv'] if r['conv'] > 0 else None, axis=1)

            variances = []
            for cname, grp in multi.groupby('creative_name'):
                grp_with_conv = grp[grp['conv'] > 0]
                if len(grp_with_conv) < 2:
                    continue
                max_cpa = grp_with_conv['cpa'].max()
                min_cpa = grp_with_conv['cpa'].min()
                if min_cpa and min_cpa > 0 and max_cpa / min_cpa >= 2.0:
                    best = grp_with_conv.loc[grp_with_conv['cpa'].idxmin()]
                    worst = grp_with_conv.loc[grp_with_conv['cpa'].idxmax()]
                    variances.append({
                        'name': strip_date_code(cname)[:25] if cname else '-',
                        'best_branch': best['branch'], 'best_cpa': best['cpa'],
                        'worst_branch': worst['branch'], 'worst_cpa': worst['cpa'],
                        'ratio': max_cpa / min_cpa,
                    })

            variances.sort(key=lambda x: x['ratio'], reverse=True)
            if variances:
                if lines:
                    lines.append("")
                lines.append("📊 지점 간 편차")
                for v in variances[:3]:
                    lines.append(f"  {v['name']}: {v['best_branch']} {v['best_cpa']/10000:.1f}만 vs {v['worst_branch']} {v['worst_cpa']/10000:.1f}만 ({v['ratio']:.1f}배)")

    return lines


def generate_actions(anomalies: list) -> list:
    """이상 감지 기반 액션 생성"""
    actions = []

    for a in anomalies[:3]:
        if a['type'] == 'no_conv':
            actions.append(f"[{a['branch']}] '{a['creative']}' OFF 검토 - {a['message']}")
        elif a['type'] == 'branch_high_cpa':
            actions.append(f"[{a['branch']}] 지점 소재 효율 긴급 점검 - {a['message']}")
        elif a['type'] == 'branch_warn_cpa':
            actions.append(f"[{a['branch']}] 지점 소재 효율 점검 - {a['message']}")
        elif a['type'] == 'cum_cpa_spike':
            actions.append(f"[{a['branch']}] 누적 CPA 상승 원인 분석 - {a['message']}")

    return actions


def fmt_diff(curr, prev, unit='', is_pct=False):
    """전일 대비 포맷 (괄호 형식)"""
    if curr is None or prev is None:
        return "(→)"
    diff = curr - prev
    if diff == 0:
        return "(→)"
    arrow = '▲' if diff > 0 else '▼'
    sign = '+' if diff > 0 else ''
    if is_pct:
        return f"({arrow}{sign}{diff:.2f}%p)"
    return f"({arrow}{sign}{int(diff):,}{unit})"


def build_daily_txt(
    csv_path: str = "input/tiktok_raw.csv",
    parquet_path: str = None,
    output_dir: str = "output",
    target_date: str = None,
    campaign_filter: str = None,
):
    """데일리 리포트 카카오톡 친화 텍스트 생성

    Args:
        csv_path: 입력 CSV 경로
        parquet_path: 입력 parquet 경로 (우선)
        output_dir: 출력 디렉토리
        target_date: 대상 날짜 (YYYY-MM-DD)
        campaign_filter: 필터링할 캠페인명 (예: '2603_다이트_전환캠페인')
    """

    df = load_data(csv_path, parquet_path)

    # 캠페인 필터링
    if campaign_filter:
        if '캠페인 이름' in df.columns:
            df = df[df['캠페인 이름'] == campaign_filter]
        elif 'campaign_name' in df.columns:
            df = df[df['campaign_name'] == campaign_filter]
        print(f"[INFO] Campaign filter applied: '{campaign_filter}' -> {len(df)} rows")

    if target_date:
        report_date = pd.to_datetime(target_date)
    else:
        report_date = df['date'].max()

    yesterday = report_date
    day_before = yesterday - timedelta(days=1)
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    day_before_str = day_before.strftime('%Y-%m-%d')

    # 어제 데이터
    df_yesterday = df[df['date'] == yesterday]
    if len(df_yesterday) == 0:
        print(f"[WARN] {yesterday_str} 데이터가 없습니다.")
        return None

    # 이번 달 누적 데이터
    month_start = pd.Timestamp(yesterday.year, yesterday.month, 1)
    df_cumulative = df[(df['date'] >= month_start) & (df['date'] <= yesterday)]

    # KPI 계산
    kpi_daily = calc_kpi(df_yesterday)
    kpi_cum = calc_kpi(df_cumulative)
    branch_daily = calc_branch_kpi(df_yesterday)
    branch_cum = calc_branch_kpi(df_cumulative)

    # 목표 CPA 로드 (없으면 전체 누적 CPA 단일값 사용)
    target_cpa_dict = load_target_cpa()
    if not target_cpa_dict:
        total_target = kpi_cum.get('cpa') or 25000
        for branch in VALID_BRANCHES:
            target_cpa_dict[branch] = total_target

    # 스냅샷 로드
    daily_dir = os.path.join(output_dir, "daily")
    snapshot_path = os.path.join(daily_dir, "daily_snapshot.json")
    snapshot = load_snapshot(snapshot_path)
    prev_data = snapshot.get(day_before_str, {})

    # 스냅샷에 전일 데이터 없으면 CSV에서 직접 계산
    if not prev_data.get('daily'):
        df_day_before = df[df['date'] == day_before]
        if len(df_day_before) > 0:
            prev_kpi = calc_kpi(df_day_before)
            prev_data = {'daily': prev_kpi, 'cumulative': {}, 'branch': {}}
            print(f"[INFO] 스냅샷에 {day_before_str} 없음 - CSV에서 전일 KPI 계산")

    prev_cum = prev_data.get('cumulative', {})
    prev_branch_cum = {b: d.get('cumulative', {}) for b, d in prev_data.get('branch', {}).items()}

    # 이상 감지
    anomalies = detect_anomalies(df_yesterday, branch_cum, prev_branch_cum, target_cpa_dict)

    # 텍스트 생성 (새로운 CVR 포함 형식)
    lines = []
    separator = "━" * 16

    # 헤더
    lines.append(f"📊 [{yesterday.strftime('%m/%d')}] 다이트한의원 TikTok 리포트")
    lines.append(separator)
    lines.append("")

    # 📅 목표 현황 (KPI)
    conv_pct = round(kpi_cum['conv'] / MONTHLY_TARGET_CONV * 100, 1)
    last_day = calendar.monthrange(yesterday.year, yesterday.month)[1]
    remaining_days = last_day - yesterday.day
    budget_pct = round(kpi_cum['cost'] / TOTAL_MONTHLY_BUDGET * 100, 1)

    lines.append("📅 목표 현황 (KPI)")
    lines.append(f"• 전환: {kpi_cum['conv']}건 / {MONTHLY_TARGET_CONV}건 ({conv_pct}%)")
    if remaining_days > 0:
        lines.append(f"• 잔여: {remaining_days}일")
    else:
        lines.append("• 잔여: 0일 (D-Day)")
    lines.append(f"• 예산 소진율: {budget_pct}%")
    lines.append("")

    # 💰 전체 성과 (어제 | 누적 | 전일비)
    prev_daily = prev_data.get('daily', {})
    lines.append("💰 전체 성과 (어제 | 누적 | 전일비)")
    lines.append(f"• 광고비: {fmt_man(kpi_daily['cost'])} | {fmt_man(kpi_cum['cost'])} {fmt_diff(kpi_daily['cost'], prev_daily.get('cost'), '원')}")
    lines.append(f"• 전환수: {kpi_daily['conv']}건 | {kpi_cum['conv']}건 {fmt_diff(kpi_daily['conv'], prev_daily.get('conv'), '건')}")
    lines.append(f"• CPA: {fmt_man(kpi_daily['cpa'])} | {fmt_man(kpi_cum['cpa'])} {fmt_diff(kpi_daily['cpa'], prev_daily.get('cpa'), '원')}")
    lines.append(f"• CTR: {fmt_pct(kpi_daily['ctr'])} | {fmt_pct(kpi_cum['ctr'])} {fmt_diff(kpi_daily['ctr'], prev_daily.get('ctr'), is_pct=True)}")
    lines.append(f"• CVR: {fmt_pct(kpi_daily['cvr'])} | {fmt_pct(kpi_cum['cvr'])} {fmt_diff(kpi_daily['cvr'], prev_daily.get('cvr'), is_pct=True)}")
    lines.append("")

    # 📍 지점별 현황 (전환 | CVR | 누적CPA) - Best vs Focus 분류
    lines.append("📍 지점별 현황 (전환 | CVR | 누적CPA)")

    # 지점 분류: Best (CPA <= 목표) vs Focus (CPA > 목표 * 1.3)
    best_branches = []
    focus_branches = []

    for branch in VALID_BRANCHES:
        daily = branch_daily.get(branch, {'cost': 0, 'conv': 0, 'cpa': None, 'cvr': 0})
        cum = branch_cum.get(branch, {'cost': 0, 'conv': 0, 'cpa': None, 'cvr': 0})
        target = target_cpa_dict.get(branch, 25000)

        cum_cpa = cum.get('cpa')
        cum_cvr = cum.get('cvr', 0)

        branch_info = {
            'name': branch,
            'conv': daily.get('conv', 0),
            'cvr': cum_cvr,
            'cpa': cum_cpa,
            'target': target,
        }

        if cum_cpa is None or cum_cpa <= target:
            best_branches.append(branch_info)
        elif cum_cpa > target * 1.3:
            focus_branches.append(branch_info)
        else:
            best_branches.append(branch_info)

    # Best 섹션
    if best_branches:
        lines.append("✅ Best (효율 우수)")
        for b in best_branches:
            cpa_str = fmt_man(b['cpa']) if b['cpa'] else "-"
            lines.append(f"• {b['name']}: {b['conv']}건 | {b['cvr']:.1f}% | {cpa_str}")

    # Focus 섹션
    if focus_branches:
        lines.append("⚠️ Focus (관측 필요)")
        for b in focus_branches:
            cpa_str = fmt_man(b['cpa']) if b['cpa'] else "-"
            ratio = round(b['cpa'] / b['target'], 1) if b['cpa'] and b['target'] else 0
            lines.append(f"• {b['name']}: {b['conv']}건 | {b['cvr']:.1f}% | {cpa_str} (목표 {ratio}배)")

    # 🔍 전환 0건 지점 코멘트
    zero_conv_lines = analyze_zero_conv_branches(
        branch_daily, prev_data.get('branch', {}), df, yesterday, day_before
    )
    if zero_conv_lines:
        lines.append("")
        lines.extend(zero_conv_lines)

    # 📉 전일비 이상치 분석
    anomaly_lines = analyze_dod_anomaly(df, yesterday, day_before)
    if anomaly_lines:
        lines.append("")
        lines.extend(anomaly_lines)

    # 📋 특이사항 (내용 있을 때만 출력)
    notable_lines = analyze_notable_items(df, yesterday, day_before)
    if notable_lines:
        lines.append("")
        lines.append("📋 특이사항")
        lines.extend(notable_lines)

    lines.append(separator)
    lines.append("")

    # 🛠 오늘의 체크포인트
    lines.append("🛠 오늘의 체크포인트")

    # CVR 분석 체크포인트 생성
    checkpoints = []

    # 1. CTR 높고 CVR 낮은 지점 찾기
    low_cvr_branches = []
    high_cvr_branches = []
    avg_cvr = kpi_cum.get('cvr', 0)

    for branch in VALID_BRANCHES:
        cum = branch_cum.get(branch, {})
        cum_cvr = cum.get('cvr', 0)
        if cum_cvr > 0 and cum_cvr < avg_cvr * 0.7:
            low_cvr_branches.append(branch)
        if cum_cvr > avg_cvr * 1.3:
            high_cvr_branches.append(branch)

    if low_cvr_branches:
        checkpoints.append(f"[CVR 분석] {', '.join(low_cvr_branches)} 지점 CVR 낮음 - 랜딩 페이지 이탈 확인")
    else:
        checkpoints.append("[CVR 분석] 전환율 양호, 클릭 후 이탈률 모니터링")

    # 2. CVR 높은 지점 확산 검토
    if high_cvr_branches:
        checkpoints.append(f"[소재 점검] {', '.join(high_cvr_branches)} 지점 고효율 소재 소구점 분석 및 확산")
    else:
        checkpoints.append("[소재 점검] 상위 CVR 소재 소구점(가격, 비포애프터 등) 분석")

    # 3. 예산 조정 권고
    if best_branches and focus_branches:
        best_names = ', '.join([b['name'] for b in best_branches[:2]])
        checkpoints.append(f"[예산 조정] {best_names} 지점으로 예산 비중 증대 검토")
    elif focus_branches:
        focus_names = ', '.join([b['name'] for b in focus_branches])
        checkpoints.append(f"[예산 조정] {focus_names} 지점 예산 축소 또는 소재 교체 검토")
    else:
        checkpoints.append("[예산 조정] 현 예산 배분 유지, 효율 모니터링")

    for cp in checkpoints:
        lines.append(cp)

    # 파일 저장
    date_folder = yesterday.strftime('%Y%m%d')
    output_folder = os.path.join(output_dir, "daily", date_folder)
    os.makedirs(output_folder, exist_ok=True)

    txt_filename = f"tiktok_daily_{date_folder}.txt"
    txt_path = os.path.join(output_folder, txt_filename)

    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    # 스냅샷 저장 (CVR 포함)
    branch_snapshot = {}
    for branch in VALID_BRANCHES:
        daily = branch_daily.get(branch, {'cost': 0, 'conv': 0, 'cvr': 0})
        cum = branch_cum.get(branch, {'cost': 0, 'conv': 0, 'cpa': None, 'cvr': 0})
        branch_snapshot[branch] = {
            'daily': {'cost': daily['cost'], 'conv': daily['conv'], 'cvr': daily.get('cvr', 0)},
            'cumulative': {'cost': cum['cost'], 'conv': cum['conv'], 'cpa': cum.get('cpa'), 'cvr': cum.get('cvr', 0)}
        }

    today_snapshot = {
        'daily': {
            'cost': kpi_daily['cost'],
            'conv': kpi_daily['conv'],
            'cpa': kpi_daily['cpa'],
            'ctr': kpi_daily['ctr'],
            'cvr': kpi_daily['cvr'],
        },
        'cumulative': {
            'cost': kpi_cum['cost'],
            'conv': kpi_cum['conv'],
            'cpa': kpi_cum['cpa'],
            'ctr': kpi_cum['ctr'],
            'cvr': kpi_cum['cvr'],
        },
        'branch': branch_snapshot
    }
    save_snapshot(snapshot_path, snapshot, yesterday_str, today_snapshot)

    # UI용 구조화 JSON
    daily_data = {
        'date': yesterday_str,
        'date_label': yesterday.strftime('%m/%d'),
        'goal': {
            'conv_current': int(kpi_cum['conv']),
            'conv_target': MONTHLY_TARGET_CONV,
            'conv_pct': conv_pct,
            'remaining_days': max(remaining_days, 0),
            'budget_pct': budget_pct,
            'budget_total': TOTAL_MONTHLY_BUDGET,
        },
        'kpi_daily': kpi_daily,
        'kpi_cum': kpi_cum,
        'kpi_prev': prev_daily,
        'branches': [
            {
                'branch': b['name'],
                'daily_conv': b['conv'],
                'cum_cvr': b['cvr'],
                'cum_cpa': b['cpa'],
                'target': b['target'],
                'tag': 'best',
                'ratio': round(b['cpa'] / b['target'], 2) if b.get('cpa') and b.get('target') else None,
            }
            for b in best_branches
        ] + [
            {
                'branch': b['name'],
                'daily_conv': b['conv'],
                'cum_cvr': b['cvr'],
                'cum_cpa': b['cpa'],
                'target': b['target'],
                'tag': 'focus',
                'ratio': round(b['cpa'] / b['target'], 2) if b.get('cpa') and b.get('target') else None,
            }
            for b in focus_branches
        ],
        'zero_conv_lines': zero_conv_lines,
        'anomaly_lines': anomaly_lines,
        'notable_lines': notable_lines,
        'checkpoints': checkpoints,
    }
    json_path = os.path.join(output_folder, f"tiktok_daily_{date_folder}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(daily_data, f, ensure_ascii=False, default=str, indent=2)

    print(f"[OK] Daily report -> {txt_path}")
    print(f"[OK] Snapshot updated -> {snapshot_path}")

    return txt_path


# 하위 호환성을 위한 별칭
def build_daily_md(*args, **kwargs):
    """하위 호환성 유지 (build_daily_txt로 위임)"""
    return build_daily_txt(*args, **kwargs)


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='데일리 리포트 생성')
    parser.add_argument('csv_path', nargs='?', default='input/tiktok_raw.csv', help='입력 CSV 경로')
    parser.add_argument('output_dir', nargs='?', default='output', help='출력 디렉토리')
    parser.add_argument('target_date', nargs='?', default=None, help='대상 날짜 (YYYY-MM-DD)')
    parser.add_argument('--campaign', type=str, default=None, help='필터링할 캠페인명 (예: 2603_다이트_전환캠페인)')

    args = parser.parse_args()
    build_daily_txt(csv_path=args.csv_path, output_dir=args.output_dir, target_date=args.target_date, campaign_filter=args.campaign)
