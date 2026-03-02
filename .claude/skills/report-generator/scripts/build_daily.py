"""
데일리 리포트 생성 (Markdown)
내부용 - 매일 아침 발행

입력: input/tiktok_raw.csv 또는 output/data/YYYYMMDD/parsed.parquet
출력: output/daily/YYYYMMDD/tiktok_daily_YYYYMMDD.md
스냅샷: output/daily/daily_snapshot.json
"""
import pandas as pd
import numpy as np
import os
import json
import re
from datetime import datetime, timedelta
from pathlib import Path


MONTHLY_TARGET_CONV = 600
VALID_BRANCHES = ['서울', '부평', '수원', '일산', '대구', '창원', '천안']


def strip_date_code(name: str) -> str:
    """소재명에서 날짜코드 제거 (_YYMM, _YYMMDD 등 4~6자리)"""
    if not name or pd.isna(name):
        return name
    return re.sub(r'_\d{4,6}$', '', str(name))


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

        def parse_branch(name):
            if pd.isna(name):
                return None
            name = str(name)
            for b in VALID_BRANCHES:
                if b in name:
                    return b
            return None

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


def load_target_cpa(target_cpa_path: str = "input/target_cpa.csv") -> dict:
    """목표 CPA 로드"""
    if os.path.exists(target_cpa_path):
        target_df = pd.read_csv(target_cpa_path, encoding='utf-8-sig')
        return dict(zip(target_df['지점'], target_df['목표CPA']))
    return {}


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
        'cpa': round(cost / conv, 0) if conv > 0 else None,
        'ctr': round(clicks / impr * 100, 2) if impr > 0 else 0,
    }


def calc_branch_kpi(df: pd.DataFrame) -> dict:
    """지점별 KPI 계산 (daily용)"""
    df_on = df[~df['is_off']]
    result = {}

    for branch in VALID_BRANCHES:
        branch_df = df_on[df_on['branch'] == branch]
        if len(branch_df) == 0:
            continue

        cost = branch_df['cost'].sum()
        conv = branch_df['conversions'].sum()

        result[branch] = {
            'cost': int(cost),
            'conv': int(conv),
            'cpa': round(cost / conv, 0) if conv > 0 else None,
        }

    return result


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


def fmt(n, unit=''):
    """숫자 포맷"""
    if n is None:
        return '-'
    return f"{int(n):,}{unit}"


def fmt_pct(n):
    """퍼센트 포맷"""
    if n is None:
        return '-'
    return f"{n:.2f}%"


def fmt_diff(curr, prev, unit='', is_pct=False):
    """전일 대비 포맷 (항상 화살표 표시)"""
    if curr is None or prev is None:
        return "이전 데이터 없음"
    diff = curr - prev
    arrow = '▲' if diff > 0 else '▼' if diff < 0 else '→'
    sign = '+' if diff > 0 else ''
    if is_pct:
        return f"{arrow} {sign}{diff:.2f}%p"
    return f"{arrow} {sign}{int(diff):,}{unit}"


def build_daily_md(
    csv_path: str = "input/tiktok_raw.csv",
    parquet_path: str = None,
    output_dir: str = "output",
    target_date: str = None,
):
    """데일리 리포트 Markdown 생성"""

    df = load_data(csv_path, parquet_path)

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
        # 전체 누적 CPA를 모든 지점에 동일하게 적용
        total_target = kpi_cum.get('cpa') or 25000
        for branch in VALID_BRANCHES:
            target_cpa_dict[branch] = total_target

    # 스냅샷 로드 (output/daily/daily_snapshot.json)
    daily_dir = os.path.join(output_dir, "daily")
    snapshot_path = os.path.join(daily_dir, "daily_snapshot.json")
    snapshot = load_snapshot(snapshot_path)
    prev_data = snapshot.get(day_before_str, {})
    prev_cum = prev_data.get('cumulative', {})
    prev_branch_cum = {b: d.get('cumulative', {}) for b, d in prev_data.get('branch', {}).items()}

    # 이상 감지
    anomalies = detect_anomalies(df_yesterday, branch_cum, prev_branch_cum, target_cpa_dict)
    actions = generate_actions(anomalies)

    # Markdown 생성
    md_lines = []

    # 헤더
    md_lines.append(f"# {yesterday.strftime('%m/%d')} 다이트한의원 TikTok 전일 성과\n")
    md_lines.append(f"> 기준일: {yesterday.strftime('%Y-%m-%d')} | 발행: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # 섹션 1: 어제 실적 (하루치 + 누적 + 누적 전일비)
    md_lines.append("\n## 1. 어제 실적\n")
    md_lines.append("| 지표 | 어제 하루 | 누적 | 누적 전일비 |")
    md_lines.append("|------|---------|------|-----------|")

    # 광고비
    md_lines.append(f"| 광고비 | {fmt(kpi_daily['cost'], '원')} | {fmt(kpi_cum['cost'], '원')} | - |")

    # 전환
    conv_target_str = f"{kpi_cum['conv']}건 (목표 {round(kpi_cum['conv']/MONTHLY_TARGET_CONV*100, 1)}%)"
    md_lines.append(f"| 전환 | {fmt(kpi_daily['conv'], '건')} | {conv_target_str} | - |")

    # CPA
    cpa_diff = fmt_diff(kpi_cum['cpa'], prev_cum.get('cpa'), '원')
    md_lines.append(f"| CPA | {fmt(kpi_daily['cpa'], '원')} | {fmt(kpi_cum['cpa'], '원')} | {cpa_diff} |")

    # CTR
    ctr_diff = fmt_diff(kpi_cum['ctr'], prev_cum.get('ctr'), '', is_pct=True)
    md_lines.append(f"| CTR | {fmt_pct(kpi_daily['ctr'])} | {fmt_pct(kpi_cum['ctr'])} | {ctr_diff} |")

    # 섹션 2: 지점별 성과
    md_lines.append("\n## 2. 지점별 성과\n")
    md_lines.append("| 지점 | 어제전환 | 어제CPA | 누적CPA | 누적전일비 | 상태 |")
    md_lines.append("|------|---------|---------|---------|-----------|------|")

    for branch in VALID_BRANCHES:
        daily = branch_daily.get(branch, {'cost': 0, 'conv': 0, 'cpa': None})
        cum = branch_cum.get(branch, {'cost': 0, 'conv': 0, 'cpa': None})
        prev_c = prev_branch_cum.get(branch, {})
        target = target_cpa_dict.get(branch, 25000)

        # 어제 CPA (전환 < 5건이면 "(소량)" 표시)
        if daily['conv'] < 5:
            daily_cpa_str = "(소량)"
        else:
            daily_cpa_str = fmt(daily['cpa'], '원')

        # 누적 전일비
        cum_diff = fmt_diff(cum.get('cpa'), prev_c.get('cpa'), '원')

        # 상태 판정 (누적CPA 기준, 전환<5면 보류)
        cum_cpa = cum.get('cpa')
        if daily['conv'] < 5:
            status = "-"  # 보류 (소량)
        elif cum_cpa is None:
            status = "⚠️"
        elif cum_cpa > target * 1.8:
            status = "🚨"
        elif cum_cpa > target * 1.3:
            status = "⚠️"
        else:
            status = "✅"

        md_lines.append(f"| {branch} | {daily['conv']}건 | {daily_cpa_str} | {fmt(cum_cpa, '원')} | {cum_diff} | {status} |")

    # 섹션 3: 이상 감지
    md_lines.append("\n## 3. 이상 감지\n")

    if anomalies:
        for a in anomalies:
            icon = "🚨" if a['severity'] == 'alert' else "⚠️"
            if a['creative']:
                md_lines.append(f"- {icon} [{a['branch']}] {a['creative']} — {a['message']}")
            else:
                md_lines.append(f"- {icon} [{a['branch']}] {a['message']}")
    else:
        md_lines.append("✅ 특이사항 없음\n")

    # 섹션 4: 오늘 체크 액션
    md_lines.append("\n## 4. 오늘 체크 액션\n")

    if actions:
        for i, action in enumerate(actions, 1):
            md_lines.append(f"{i}. {action}")
    else:
        md_lines.append("- 특별 액션 없음 (정상 운영)\n")

    # 파일 저장 (output/daily/YYYYMMDD/)
    date_folder = yesterday.strftime('%Y%m%d')
    output_folder = os.path.join(output_dir, "daily", date_folder)
    os.makedirs(output_folder, exist_ok=True)

    md_filename = f"tiktok_daily_{date_folder}.md"
    md_path = os.path.join(output_folder, md_filename)

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

    # 스냅샷 저장 (새 구조)
    branch_snapshot = {}
    for branch in VALID_BRANCHES:
        daily = branch_daily.get(branch, {'cost': 0, 'conv': 0})
        cum = branch_cum.get(branch, {'cost': 0, 'conv': 0, 'cpa': None})
        branch_snapshot[branch] = {
            'daily': {'cost': daily['cost'], 'conv': daily['conv']},
            'cumulative': {'cost': cum['cost'], 'conv': cum['conv'], 'cpa': cum.get('cpa')}
        }

    today_snapshot = {
        'daily': {
            'cost': kpi_daily['cost'],
            'conv': kpi_daily['conv'],
            'cpa': kpi_daily['cpa'],
            'ctr': kpi_daily['ctr'],
        },
        'cumulative': {
            'cost': kpi_cum['cost'],
            'conv': kpi_cum['conv'],
            'cpa': kpi_cum['cpa'],
            'ctr': kpi_cum['ctr'],
        },
        'branch': branch_snapshot
    }
    save_snapshot(snapshot_path, snapshot, yesterday_str, today_snapshot)

    print(f"[OK] Daily report -> {md_path}")
    print(f"[OK] Snapshot updated -> {snapshot_path}")

    return md_path


if __name__ == "__main__":
    import sys

    csv_path = sys.argv[1] if len(sys.argv) > 1 else "input/tiktok_raw.csv"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    target_date = sys.argv[3] if len(sys.argv) > 3 else None

    build_daily_md(csv_path=csv_path, output_dir=output_dir, target_date=target_date)
