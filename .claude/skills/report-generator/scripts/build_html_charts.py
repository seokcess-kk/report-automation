"""
TikTok 광고 분석 - HTML 인터랙티브 차트 생성
v4.0.0 - Excel/HTML 분리

Plotly 기반 인터랙티브 차트를 단일 HTML 파일로 생성
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("[WARNING] plotly not installed. Run: pip install plotly")


# 색상 상수
TIER_COLORS = {
    'TIER1': '#90EE90',
    'TIER2': '#ADD8E6',
    'TIER3': '#FFFFE0',
    'TIER4': '#FFB6C1',
    'LOW_VOLUME': '#D3D3D3',
    'UNCLASSIFIED': '#E8E8E8'
}

TYPE_COLORS = ['#3b82f6', '#10b981', '#f59e0b']
BRANCH_COLORS = px.colors.qualitative.Set2 if PLOTLY_AVAILABLE else []


def build_html_charts(output_dir: str, creative_df: pd.DataFrame, age_df: pd.DataFrame,
                      df_valid: pd.DataFrame, hook_type_df: pd.DataFrame = None,
                      hook_strict_df: pd.DataFrame = None, target_cpa_map: dict = None):
    """
    모든 차트를 단일 HTML 파일로 생성

    Args:
        output_dir: 출력 디렉토리
        creative_df: 소재별 집계 데이터
        age_df: 나이대별 분석 데이터
        df_valid: 일별 원본 데이터
        hook_type_df: 소재유형별 훅 비교
        hook_strict_df: 정확 매칭 훅 쌍
        target_cpa_map: 지점별 목표 CPA

    Returns:
        str: 생성된 HTML 파일 경로
    """
    if not PLOTLY_AVAILABLE:
        print("[ERROR] Plotly not available. Skipping HTML chart generation.")
        return None

    # KPI 계산
    total_cost = df_valid['cost'].sum()
    total_conv = df_valid['conversions'].sum()
    avg_cpa = total_cost / total_conv if total_conv > 0 else 0
    avg_ctr = df_valid['CTR_calc'].mean() if 'CTR_calc' in df_valid.columns else 0
    avg_cvr = df_valid['CVR_calc'].mean() if 'CVR_calc' in df_valid.columns else 0

    # 분석 기간
    date_min = df_valid['date'].min()
    date_max = df_valid['date'].max()

    # 차트 생성
    charts = {}

    # 1. TIER 분포 도넛
    charts['tier_donut'] = create_tier_donut(creative_df)

    # 2. 지점별 CPA 막대
    charts['branch_cpa'] = create_branch_cpa_bar(df_valid, target_cpa_map)

    # 3. 소재유형 레이더
    charts['type_radar'] = create_type_radar(creative_df)

    # 4. 소재 버블 차트
    charts['creative_bubble'] = create_creative_bubble(creative_df)

    # 5. 훅 비교 차트
    if hook_type_df is not None and len(hook_type_df) > 0:
        charts['hook_comparison'] = create_hook_comparison(hook_type_df)

    # 6. 나이대 비용 vs 전환
    charts['age_efficiency'] = create_age_efficiency(age_df)

    # 7. 히트맵 (CTR)
    charts['heatmap_ctr'] = create_heatmap(df_valid, 'CTR_calc', 'CTR')

    # 8. 히트맵 (CVR)
    charts['heatmap_cvr'] = create_heatmap(df_valid, 'CVR_calc', 'CVR')

    # 9. 일별 트렌드
    charts['daily_trend'] = create_daily_trend(df_valid)

    # 10. 피로도 라인
    charts['fatigue_line'] = create_fatigue_line(df_valid, creative_df)

    # 11. 일별 CPA + 목표선
    target_cpa = list(target_cpa_map.values())[0] if target_cpa_map else avg_cpa
    charts['daily_cpa'] = create_daily_cpa_trend(df_valid, target_cpa)

    # HTML 생성
    html_content = generate_html_template(
        charts=charts,
        total_cost=total_cost,
        total_conv=total_conv,
        avg_cpa=avg_cpa,
        avg_ctr=avg_ctr,
        avg_cvr=avg_cvr,
        date_min=date_min,
        date_max=date_max,
        creative_count=len(creative_df),
        tier_dist=creative_df['TIER'].value_counts().to_dict() if 'TIER' in creative_df.columns else {}
    )

    # 파일 저장
    today = datetime.now().strftime('%Y%m%d')
    html_path = os.path.join(output_dir, f'tiktok_charts_{today}.html')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return html_path


def create_tier_donut(creative_df):
    """TIER 분포 도넛 차트"""
    if 'TIER' not in creative_df.columns:
        return None

    tier_counts = creative_df['TIER'].value_counts().reset_index()
    tier_counts.columns = ['TIER', 'count']

    colors = [TIER_COLORS.get(t, '#CCCCCC') for t in tier_counts['TIER']]

    fig = go.Figure(data=[go.Pie(
        labels=tier_counts['TIER'],
        values=tier_counts['count'],
        hole=0.5,
        marker_colors=colors,
        textinfo='label+value',
        textposition='outside'
    )])

    fig.update_layout(
        title='소재 TIER 분포',
        showlegend=True,
        height=400
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def create_branch_cpa_bar(df_valid, target_cpa_map=None):
    """지점별 CPA 가로 막대 차트"""
    branch_col = '지점' if '지점' in df_valid.columns else 'branch'
    if branch_col not in df_valid.columns:
        return None

    branch_summary = df_valid.groupby(branch_col).agg({
        'cost': 'sum',
        'conversions': 'sum'
    }).reset_index()
    branch_summary['CPA'] = branch_summary['cost'] / branch_summary['conversions'].replace(0, np.nan)
    branch_summary = branch_summary.sort_values('CPA', ascending=True)

    fig = go.Figure()

    # CPA 막대
    fig.add_trace(go.Bar(
        y=branch_summary[branch_col],
        x=branch_summary['CPA'],
        orientation='h',
        name='CPA',
        marker_color='#3b82f6',
        text=[f'{v:,.0f}원' for v in branch_summary['CPA']],
        textposition='outside'
    ))

    # 목표선
    if target_cpa_map:
        avg_target = np.mean(list(target_cpa_map.values()))
        fig.add_vline(x=avg_target, line_dash='dash', line_color='red',
                      annotation_text=f'목표 {avg_target:,.0f}원')

    fig.update_layout(
        title='지점별 CPA 비교',
        xaxis_title='CPA (원)',
        height=400
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def create_type_radar(creative_df):
    """소재유형별 4지표 레이더 차트"""
    type_col = '소재유형' if '소재유형' in creative_df.columns else 'ad_type'
    if type_col not in creative_df.columns:
        return None

    # 필요 컬럼 확인
    metrics = []
    if 'CTR' in creative_df.columns:
        metrics.append(('CTR', 'CTR'))
    if 'CVR' in creative_df.columns:
        metrics.append(('CVR', 'CVR'))
    if 'CPA' in creative_df.columns:
        metrics.append(('CPA', 'CPA 효율'))
    if '랜딩률' in creative_df.columns:
        metrics.append(('랜딩률', '랜딩률'))

    if len(metrics) < 2:
        return None

    type_summary = creative_df.groupby(type_col).agg({
        m[0]: 'mean' for m in metrics
    }).reset_index()

    # 정규화 (0-100)
    for col, _ in metrics:
        if col == 'CPA':
            # CPA는 낮을수록 좋으므로 역수
            max_val = type_summary[col].max()
            type_summary[f'{col}_norm'] = (max_val / type_summary[col].replace(0, np.nan)) * 100
            type_summary[f'{col}_norm'] = type_summary[f'{col}_norm'].clip(0, 100)
        else:
            max_val = type_summary[col].max()
            if max_val > 0:
                type_summary[f'{col}_norm'] = (type_summary[col] / max_val) * 100
            else:
                type_summary[f'{col}_norm'] = 0

    fig = go.Figure()

    categories = [m[1] for m in metrics]

    for i, row in type_summary.iterrows():
        values = [row[f'{m[0]}_norm'] for m in metrics]
        values.append(values[0])  # 닫기

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories + [categories[0]],
            fill='toself',
            name=row[type_col],
            line_color=TYPE_COLORS[i % len(TYPE_COLORS)]
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title='소재유형별 지표 비교',
        height=450
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def create_creative_bubble(creative_df):
    """소재 버블 차트 (CTR × CVR × 비용)"""
    if not all(col in creative_df.columns for col in ['CTR', 'CVR', '총비용', 'TIER']):
        return None

    fig = px.scatter(
        creative_df,
        x='CTR',
        y='CVR',
        size='총비용',
        color='TIER',
        hover_name='소재명' if '소재명' in creative_df.columns else None,
        color_discrete_map=TIER_COLORS,
        size_max=60
    )

    # 평균선
    avg_ctr = creative_df['CTR'].mean()
    avg_cvr = creative_df['CVR'].mean()

    fig.add_hline(y=avg_cvr, line_dash='dash', line_color='gray', opacity=0.5)
    fig.add_vline(x=avg_ctr, line_dash='dash', line_color='gray', opacity=0.5)

    fig.update_layout(
        title='소재 효율 버블 차트 (버블 크기 = 광고비)',
        xaxis_title='CTR (%)',
        yaxis_title='CVR (%)',
        height=500
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def create_hook_comparison(hook_type_df):
    """훅 전후 비교 막대 차트"""
    if hook_type_df is None or len(hook_type_df) == 0:
        return None

    # 데이터 구조에 따라 처리
    if '소재구분' in hook_type_df.columns:
        metrics = ['CTR', 'CVR', 'CPA']
        available_metrics = [m for m in metrics if m in hook_type_df.columns]

        if len(available_metrics) == 0:
            return None

        fig = go.Figure()

        for metric in available_metrics:
            new_val = hook_type_df[hook_type_df['소재구분'] == '신규'][metric].values
            re_val = hook_type_df[hook_type_df['소재구분'] == '재가공'][metric].values

            if len(new_val) > 0 and len(re_val) > 0:
                fig.add_trace(go.Bar(name=f'신규 {metric}', x=[metric], y=[new_val[0]]))
                fig.add_trace(go.Bar(name=f'재가공 {metric}', x=[metric], y=[re_val[0]]))

        fig.update_layout(
            title='훅 효과: 신규 vs 재가공',
            barmode='group',
            height=400
        )

        return fig.to_html(full_html=False, include_plotlyjs=False)

    return None


def create_age_efficiency(age_df):
    """나이대별 비용 vs 전환 비중"""
    age_col = '나이대' if '나이대' in age_df.columns else 'age_group'
    if age_col not in age_df.columns:
        return None

    cost_col = '비용비중' if '비용비중' in age_df.columns else 'cost_ratio'
    conv_col = '전환비중' if '전환비중' in age_df.columns else 'conv_ratio'

    if cost_col not in age_df.columns or conv_col not in age_df.columns:
        # 직접 계산
        total_cost = age_df['cost'].sum() if 'cost' in age_df.columns else 1
        total_conv = age_df['conversions'].sum() if 'conversions' in age_df.columns else 1
        age_df = age_df.copy()
        if 'cost' in age_df.columns:
            age_df['비용비중'] = age_df['cost'] / total_cost * 100
        if 'conversions' in age_df.columns:
            age_df['전환비중'] = age_df['conversions'] / total_conv * 100
        cost_col = '비용비중'
        conv_col = '전환비중'

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='비용 비중',
        x=age_df[age_col],
        y=age_df[cost_col],
        marker_color='#ef4444'
    ))

    fig.add_trace(go.Bar(
        name='전환 비중',
        x=age_df[age_col],
        y=age_df[conv_col],
        marker_color='#10b981'
    ))

    fig.update_layout(
        title='나이대별 비용 vs 전환 비중',
        barmode='group',
        xaxis_title='나이대',
        yaxis_title='비중 (%)',
        height=400
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def create_heatmap(df_valid, metric_col, metric_name):
    """소재유형 × 나이대 히트맵"""
    type_col = '소재유형' if '소재유형' in df_valid.columns else 'ad_type'
    age_col = '나이대' if '나이대' in df_valid.columns else 'age_group'

    if type_col not in df_valid.columns or age_col not in df_valid.columns:
        return None
    if metric_col not in df_valid.columns:
        return None

    pivot = df_valid.pivot_table(
        values=metric_col,
        index=type_col,
        columns=age_col,
        aggfunc='mean'
    ).fillna(0)

    fig = px.imshow(
        pivot,
        labels=dict(x='나이대', y='소재유형', color=f'{metric_name} (%)'),
        color_continuous_scale='YlGn',
        text_auto='.2f'
    )

    fig.update_layout(
        title=f'소재유형 × 나이대 {metric_name} 히트맵',
        height=350
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def create_daily_trend(df_valid):
    """일별 비용 vs 전환 트렌드"""
    daily = df_valid.groupby('date').agg({
        'cost': 'sum',
        'conversions': 'sum'
    }).reset_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(x=daily['date'], y=daily['cost'], name='비용', marker_color='#3b82f6', opacity=0.7),
        secondary_y=False
    )

    fig.add_trace(
        go.Scatter(x=daily['date'], y=daily['conversions'], name='전환',
                   mode='lines+markers', line_color='#ef4444'),
        secondary_y=True
    )

    fig.update_layout(
        title='일별 비용 vs 전환 추이',
        height=400
    )
    fig.update_yaxes(title_text='비용 (원)', secondary_y=False)
    fig.update_yaxes(title_text='전환 (건)', secondary_y=True)

    return fig.to_html(full_html=False, include_plotlyjs=False)


def create_fatigue_line(df_valid, creative_df):
    """상위 소재 CVR 추이 (피로도 감지)"""
    name_col = '소재명' if '소재명' in df_valid.columns else 'creative_name'
    if name_col not in df_valid.columns:
        return None

    # 상위 5개 소재
    if 'TIER' in creative_df.columns:
        tier1 = creative_df[creative_df['TIER'] == 'TIER1'][name_col].tolist()[:3]
    else:
        tier1 = []

    cost_col = '총비용' if '총비용' in creative_df.columns else 'cost'
    if cost_col in creative_df.columns:
        top_cost = creative_df.nlargest(5, cost_col)[name_col].tolist()
    else:
        top_cost = creative_df[name_col].head(5).tolist()

    top_creatives = list(dict.fromkeys(tier1 + top_cost))[:5]

    if len(top_creatives) == 0:
        return None

    df_top = df_valid[df_valid[name_col].isin(top_creatives)].copy()

    daily_cvr = df_top.groupby([name_col, 'date']).agg({
        'conversions': 'sum',
        'clicks': 'sum'
    }).reset_index()
    daily_cvr['CVR'] = daily_cvr['conversions'] / daily_cvr['clicks'].replace(0, np.nan) * 100

    fig = px.line(
        daily_cvr,
        x='date',
        y='CVR',
        color=name_col,
        markers=True
    )

    fig.add_hline(y=5.0, line_dash='dash', line_color='gray',
                  annotation_text='CVR 5% 기준선')

    fig.update_layout(
        title='상위 소재 CVR 추이 (피로도 감지)',
        xaxis_title='날짜',
        yaxis_title='CVR (%)',
        height=400
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def create_daily_cpa_trend(df_valid, target_cpa=None):
    """일별 CPA 추이 + 목표선"""
    daily = df_valid.groupby('date').agg({
        'cost': 'sum',
        'conversions': 'sum'
    }).reset_index()
    daily['CPA'] = daily['cost'] / daily['conversions'].replace(0, np.nan)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=daily['date'],
        y=daily['CPA'],
        mode='lines+markers',
        name='CPA',
        line_color='#3b82f6'
    ))

    if target_cpa:
        fig.add_hline(y=target_cpa, line_dash='dash', line_color='red',
                      annotation_text=f'목표 {target_cpa:,.0f}원')

    fig.update_layout(
        title='일별 CPA 추이',
        xaxis_title='날짜',
        yaxis_title='CPA (원)',
        height=400
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def generate_html_template(charts, total_cost, total_conv, avg_cpa, avg_ctr, avg_cvr,
                           date_min, date_max, creative_count, tier_dist):
    """HTML 템플릿 생성"""

    # TIER 분포 텍스트
    tier_text = ' | '.join([f'{k}: {v}개' for k, v in tier_dist.items()])

    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TikTok 광고 분석 차트</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
            background: #f5f7fa;
            color: #333;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; }}

        .kpi-container {{
            display: flex;
            justify-content: center;
            gap: 20px;
            padding: 20px;
            flex-wrap: wrap;
            margin-top: -40px;
        }}
        .kpi-card {{
            background: white;
            border-radius: 12px;
            padding: 20px 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            text-align: center;
            min-width: 180px;
        }}
        .kpi-card .value {{
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .kpi-card .label {{
            font-size: 12px;
            color: #7f8c8d;
            margin-top: 5px;
        }}

        nav {{
            background: white;
            padding: 15px;
            display: flex;
            justify-content: center;
            gap: 10px;
            flex-wrap: wrap;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        nav button {{
            padding: 10px 20px;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
            background: #f0f0f0;
        }}
        nav button:hover, nav button.active {{
            background: #667eea;
            color: white;
        }}

        .section {{
            display: none;
            padding: 30px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        .section.active {{ display: block; }}
        .section h2 {{
            font-size: 22px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}

        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
        }}
        .chart-box {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        .chart-full {{
            grid-column: 1 / -1;
        }}

        .info-box {{
            background: #e8f4fd;
            border-left: 4px solid #3b82f6;
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }}

        footer {{
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>TikTok 광고 분석 리포트</h1>
        <p>분석 기간: {date_min} ~ {date_max} | 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>

    <div class="kpi-container">
        <div class="kpi-card">
            <div class="value">{total_cost:,.0f}원</div>
            <div class="label">총 광고비</div>
        </div>
        <div class="kpi-card">
            <div class="value">{total_conv:,.0f}건</div>
            <div class="label">총 전환수</div>
        </div>
        <div class="kpi-card">
            <div class="value">{avg_cpa:,.0f}원</div>
            <div class="label">평균 CPA</div>
        </div>
        <div class="kpi-card">
            <div class="value">{avg_ctr:.2f}%</div>
            <div class="label">평균 CTR</div>
        </div>
        <div class="kpi-card">
            <div class="value">{avg_cvr:.2f}%</div>
            <div class="label">평균 CVR</div>
        </div>
    </div>

    <nav>
        <button class="active" onclick="showSection('summary')">요약</button>
        <button onclick="showSection('tier')">TIER분석</button>
        <button onclick="showSection('hook')">훅효과</button>
        <button onclick="showSection('age')">나이대</button>
        <button onclick="showSection('daily')">일별트렌드</button>
    </nav>

    <section id="summary" class="section active">
        <h2>요약 대시보드</h2>
        <div class="info-box">
            <strong>분석 소재:</strong> {creative_count}개 | <strong>TIER 분포:</strong> {tier_text}
        </div>
        <div class="chart-grid">
            <div class="chart-box">
                {charts.get('tier_donut', '<p>차트 없음</p>')}
            </div>
            <div class="chart-box">
                {charts.get('branch_cpa', '<p>차트 없음</p>')}
            </div>
            <div class="chart-box chart-full">
                {charts.get('type_radar', '<p>차트 없음</p>')}
            </div>
        </div>
    </section>

    <section id="tier" class="section">
        <h2>소재 TIER 분석</h2>
        <div class="chart-grid">
            <div class="chart-box chart-full">
                {charts.get('creative_bubble', '<p>차트 없음</p>')}
            </div>
        </div>
    </section>

    <section id="hook" class="section">
        <h2>훅 개선 효과</h2>
        <div class="chart-grid">
            <div class="chart-box chart-full">
                {charts.get('hook_comparison', '<p>훅 비교 데이터 없음</p>')}
            </div>
        </div>
    </section>

    <section id="age" class="section">
        <h2>나이대 분석</h2>
        <div class="chart-grid">
            <div class="chart-box">
                {charts.get('age_efficiency', '<p>차트 없음</p>')}
            </div>
            <div class="chart-box">
                {charts.get('heatmap_ctr', '<p>차트 없음</p>')}
            </div>
            <div class="chart-box">
                {charts.get('heatmap_cvr', '<p>차트 없음</p>')}
            </div>
        </div>
    </section>

    <section id="daily" class="section">
        <h2>일별 트렌드</h2>
        <div class="chart-grid">
            <div class="chart-box chart-full">
                {charts.get('daily_trend', '<p>차트 없음</p>')}
            </div>
            <div class="chart-box">
                {charts.get('fatigue_line', '<p>차트 없음</p>')}
            </div>
            <div class="chart-box">
                {charts.get('daily_cpa', '<p>차트 없음</p>')}
            </div>
        </div>
    </section>

    <footer>
        TikTok 광고 분석 자동화 시스템 v4.0.0 | Generated by Claude Code
    </footer>

    <script>
        function showSection(id) {{
            // 모든 섹션 숨기기
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));

            // 선택된 섹션 표시
            document.getElementById(id).classList.add('active');
            event.target.classList.add('active');
        }}
    </script>
</body>
</html>'''

    return html


if __name__ == '__main__':
    print("HTML Chart Builder v4.0.0")
    print("Usage: Import and call build_html_charts()")
