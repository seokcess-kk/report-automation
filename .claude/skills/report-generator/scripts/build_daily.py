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
):
    """데일리 리포트 카카오톡 친화 텍스트 생성"""

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
        total_target = kpi_cum.get('cpa') or 25000
        for branch in VALID_BRANCHES:
            target_cpa_dict[branch] = total_target

    # 스냅샷 로드
    daily_dir = os.path.join(output_dir, "daily")
    snapshot_path = os.path.join(daily_dir, "daily_snapshot.json")
    snapshot = load_snapshot(snapshot_path)
    prev_data = snapshot.get(day_before_str, {})
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

    # 💰 전체 성과 (어제 | 누적)
    lines.append("💰 전체 성과 (어제 | 누적)")
    lines.append(f"• 광고비: {fmt_man(kpi_daily['cost'])} | {fmt_man(kpi_cum['cost'])}")
    lines.append(f"• 전환수: {kpi_daily['conv']}건 | {kpi_cum['conv']}건")
    lines.append(f"• CPA: {fmt_man(kpi_daily['cpa'])} | {fmt_man(kpi_cum['cpa'])}")
    lines.append(f"• CTR: {fmt_pct(kpi_daily['ctr'])} | {fmt_pct(kpi_cum['ctr'])}")
    lines.append(f"• CVR: {fmt_pct(kpi_daily['cvr'])} | {fmt_pct(kpi_cum['cvr'])} (전환 효율)")
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

    lines.append("")
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

    print(f"[OK] Daily report -> {txt_path}")
    print(f"[OK] Snapshot updated -> {snapshot_path}")

    return txt_path


# 하위 호환성을 위한 별칭
def build_daily_md(*args, **kwargs):
    """하위 호환성 유지 (build_daily_txt로 위임)"""
    return build_daily_txt(*args, **kwargs)


if __name__ == "__main__":
    import sys

    csv_path = sys.argv[1] if len(sys.argv) > 1 else "input/tiktok_raw.csv"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    target_date = sys.argv[3] if len(sys.argv) > 3 else None

    build_daily_txt(csv_path=csv_path, output_dir=output_dir, target_date=target_date)
