"""
TikTok Ad Analysis - Chart Builder
Based on tiktok-chart-spec.md

Charts:
1. TIER Distribution Donut - Summary Dashboard
2. Branch CPA Bar - Summary Dashboard
3. Creative Bubble Chart - Creative TIER Analysis
4. Hook Comparison Bar - Hook Effect
5. Age Efficiency Bar - Age Analysis
6. Age x Type Heatmap - Age Analysis
7. Daily Combo Chart - Daily Trend
8. Daily CTR Line - Daily Trend
"""
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
import io
import platform

# Korean font setup with fallback
def setup_korean_font():
    """Setup Korean font based on platform"""
    system = platform.system()

    # Try platform-specific fonts
    font_candidates = []
    if system == 'Windows':
        font_candidates = ['Malgun Gothic', 'NanumGothic', 'Gulim']
    elif system == 'Darwin':  # macOS
        font_candidates = ['AppleGothic', 'NanumGothic']
    else:  # Linux
        font_candidates = ['NanumGothic', 'DejaVu Sans']

    # Find available font
    available_fonts = [f.name for f in fm.fontManager.ttflist]

    for font in font_candidates:
        if font in available_fonts:
            plt.rcParams['font.family'] = font
            print(f"[Charts] Using font: {font}")
            break
    else:
        plt.rcParams['font.family'] = 'DejaVu Sans'
        print("[Charts] Korean font not found, using DejaVu Sans")

    plt.rcParams['axes.unicode_minus'] = False

setup_korean_font()

# TIER color scheme (consistent across all charts)
TIER_COLORS = {
    'TIER1': '#10b981',      # Green
    'TIER2': '#3b82f6',      # Blue
    'TIER3': '#f59e0b',      # Orange
    'TIER4': '#ef4444',      # Red
    'LOW_VOLUME': '#9ca3af', # Gray
    'UNCLASSIFIED': '#a78bfa' # Purple
}

TIER_ORDER = ['TIER1', 'TIER2', 'TIER3', 'TIER4', 'LOW_VOLUME', 'UNCLASSIFIED']


def _save_chart_to_excel(ws, fig, anchor_cell, width=900, height=400):
    """Save matplotlib figure to Excel as image"""
    from openpyxl.drawing.image import Image as XLImage

    try:
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        buf.seek(0)
        plt.close(fig)

        img = XLImage(buf)
        img.width = width
        img.height = height
        ws.add_image(img, anchor_cell)
    except Exception as e:
        print(f"[WARNING] 차트 저장 실패: {e}")
        plt.close(fig)


def add_tier_donut(ws, creative_df, anchor_cell="K2"):
    """
    Chart 1: TIER Distribution Donut Chart
    Sheet: Summary Dashboard
    """
    if creative_df is None or len(creative_df) == 0:
        return

    # Count by TIER
    tier_counts = creative_df['TIER'].value_counts().reindex(TIER_ORDER, fill_value=0)
    tier_counts = tier_counts[tier_counts > 0]  # Remove zero counts

    if len(tier_counts) == 0:
        return

    fig, ax = plt.subplots(figsize=(8, 6))

    colors = [TIER_COLORS.get(tier, '#999') for tier in tier_counts.index]

    wedges, texts, autotexts = ax.pie(
        tier_counts.values,
        labels=tier_counts.index,
        colors=colors,
        autopct=lambda pct: f'{pct:.1f}%\n({int(pct/100*sum(tier_counts.values))})',
        pctdistance=0.75,
        wedgeprops=dict(width=0.5, edgecolor='white', linewidth=2),
        textprops={'fontsize': 9}
    )

    ax.set_title('소재 TIER 분포', fontsize=12, fontweight='bold', pad=20)

    # Add center text
    total = sum(tier_counts.values)
    ax.text(0, 0, f'전체\n{total}', ha='center', va='center', fontsize=14, fontweight='bold')

    plt.tight_layout()
    _save_chart_to_excel(ws, fig, anchor_cell, width=500, height=400)


def add_branch_cpa_bar(ws, branch_df, target_cpa_map=None, anchor_cell="K18"):
    """
    Chart 2: Branch CPA Horizontal Bar Chart (v3.2.0 개선)
    Sheet: Summary Dashboard

    v3.2.0: target_cpa_map 지원 - 지점별 목표 CPA 선 표시

    Args:
        target_cpa_map: dict, 예: {'서울': 20000, '일산': 20000, ...}
                        또는 int/float (전체 목표 CPA)
    """
    if branch_df is None or len(branch_df) == 0:
        return

    # Sort by CPA ascending (best at top)
    sorted_df = branch_df.sort_values('CPA', ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))

    branches = sorted_df['지점'].tolist() if '지점' in sorted_df.columns else sorted_df.index.tolist()
    cpas = sorted_df['CPA'].values

    # Determine target CPA for coloring
    if target_cpa_map is None:
        target_cpa = np.median(cpas)
        target_label = '중앙값'
    elif isinstance(target_cpa_map, (int, float)):
        target_cpa = target_cpa_map
        target_label = '목표'
    else:
        # Dict: use average of targets
        target_cpa = np.mean(list(target_cpa_map.values()))
        target_label = '목표 평균'

    # Color by CPA performance vs target
    colors = []
    for i, cpa in enumerate(cpas):
        # Get branch-specific target if available
        if isinstance(target_cpa_map, dict):
            branch_target = target_cpa_map.get(branches[i], target_cpa)
        else:
            branch_target = target_cpa

        if cpa <= branch_target:
            colors.append('#10b981')  # Good - green (under target)
        elif cpa <= branch_target * 1.2:
            colors.append('#f59e0b')  # Average - orange
        else:
            colors.append('#ef4444')  # Poor - red

    bars = ax.barh(range(len(branches)), cpas, color=colors, alpha=0.8, edgecolor='white')

    # Add value labels
    for i, (bar, cpa) in enumerate(zip(bars, cpas)):
        ax.text(bar.get_width() + 500, bar.get_y() + bar.get_height()/2,
               f'{cpa:,.0f}', va='center', fontsize=9)

    # v3.2.0: 목표 CPA 선 추가
    if isinstance(target_cpa_map, dict):
        # 지점별 개별 목표선 표시
        for i, branch in enumerate(branches):
            if branch in target_cpa_map:
                target = target_cpa_map[branch]
                ax.plot([target, target], [i - 0.4, i + 0.4],
                       color='red', linestyle=':', linewidth=2, alpha=0.8)
        # 범례용 목표선
        ax.axvline(-9999, color='red', linestyle=':', linewidth=2, alpha=0.8, label='목표 CPA')
        ax.legend(loc='lower right', fontsize=9)
    else:
        # 단일 목표/중앙값 선
        ax.axvline(target_cpa, color='red' if target_cpa_map else 'gray',
                  linestyle='--', linewidth=1.5, alpha=0.7)
        ax.text(target_cpa, len(branches)-0.5, f'{target_label}: {target_cpa:,.0f}',
               fontsize=9, color='red' if target_cpa_map else 'gray', fontweight='bold')

    ax.set_yticks(range(len(branches)))
    ax.set_yticklabels(branches, fontsize=10)
    ax.set_xlabel('CPA (원)', fontsize=10)
    ax.set_title('지점별 CPA 비교', fontsize=12, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)
    ax.set_xlim(left=0)

    plt.tight_layout()
    _save_chart_to_excel(ws, fig, anchor_cell, width=600, height=400)


def add_creative_bubble_chart(ws, creative_df, anchor_cell="A35"):
    """
    Chart 3: Creative Bubble Chart (CTR x CVR x Cost)
    Sheet: Creative TIER Analysis

    IMPORTANT: Only TIER1~4 creatives (NO LOW_VOLUME, NO UNCLASSIFIED)
    """
    if creative_df is None or len(creative_df) == 0:
        return

    # Filter: Only evaluable TIER creatives
    eval_tiers = ['TIER1', 'TIER2', 'TIER3', 'TIER4']
    eval_df = creative_df[creative_df['TIER'].isin(eval_tiers)].dropna(subset=['CTR', 'CVR'])

    if len(eval_df) == 0:
        return

    fig, ax = plt.subplots(figsize=(14, 8))

    for tier in eval_tiers:
        group = eval_df[eval_df['TIER'] == tier]
        if len(group) == 0:
            continue

        # Bubble size based on cost
        max_cost = eval_df['총비용'].max()
        sizes = (group['총비용'] / max_cost * 1500).clip(lower=100)

        ax.scatter(
            group['CTR'], group['CVR'],
            s=sizes,
            c=TIER_COLORS.get(tier, '#999'),
            alpha=0.7,
            label=tier,
            edgecolors='white',
            linewidth=0.8
        )

        # Add labels (truncate long names)
        for _, row in group.iterrows():
            name = row['소재명']
            label = name[:10] + '...' if len(str(name)) > 10 else name
            ax.annotate(label, (row['CTR'], row['CVR']),
                       textcoords="offset points", xytext=(5, 5),
                       fontsize=7, alpha=0.8)

    # Reference lines (averages)
    avg_ctr = eval_df['CTR'].mean()
    avg_cvr = eval_df['CVR'].mean()

    ax.axvline(avg_ctr, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    ax.axhline(avg_cvr, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)

    # Quadrant labels
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    ax.text(xlim[1]*0.85, ylim[1]*0.9, '높은 CTR\n높은 CVR',
           fontsize=9, color='#10b981', alpha=0.7, ha='center')
    ax.text(xlim[0]+0.05, ylim[0]+0.3, '낮은 CTR\n낮은 CVR',
           fontsize=9, color='#ef4444', alpha=0.7, ha='left')

    ax.set_xlabel('CTR (%)', fontsize=11)
    ax.set_ylabel('CVR (%)', fontsize=11)
    ax.set_title('소재 효율 버블 차트\n(버블 크기 = 광고비)',
                fontsize=12, fontweight='bold')
    ax.legend(loc='lower right', fontsize=9)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    _save_chart_to_excel(ws, fig, anchor_cell, width=900, height=550)


def add_hook_comparison_chart(ws, hook_type_df, anchor_cell="I3"):
    """
    Chart 4: Hook Comparison Grouped Bar
    Sheet: Hook Effect

    Shows CTR/CVR/CPA change rates between original and reworked
    """
    if hook_type_df is None or len(hook_type_df) == 0:
        return

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    metrics = [
        ('CTR_변화율', 'CTR 변화율 (%)', True),   # Higher is better
        ('CVR_변화율', 'CVR 변화율 (%)', True),
        ('CPA_변화율', 'CPA 변화율 (%)', False),  # Lower is better
    ]

    x_labels = hook_type_df['소재유형'].tolist() if '소재유형' in hook_type_df.columns else list(range(len(hook_type_df)))

    for ax, (col, title, higher_better) in zip(axes, metrics):
        if col not in hook_type_df.columns:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(title, fontsize=10, fontweight='bold')
            continue

        values = hook_type_df[col].fillna(0).values

        # Color based on improvement direction
        colors = []
        for v in values:
            if higher_better:
                colors.append('#10b981' if v > 0 else '#ef4444')
            else:
                colors.append('#10b981' if v < 0 else '#ef4444')

        bars = ax.bar(range(len(values)), values, color=colors, alpha=0.8, edgecolor='white')
        ax.axhline(0, color='black', linewidth=0.8)

        # Value labels
        for bar, val in zip(bars, values):
            y_pos = bar.get_height() + (1 if val >= 0 else -3)
            ax.text(bar.get_x() + bar.get_width()/2, y_pos,
                   f'{val:+.1f}%', ha='center', fontsize=8)

        ax.set_xticks(range(len(x_labels)))
        ax.set_xticklabels(x_labels, rotation=30, ha='right', fontsize=8)
        ax.set_title(title, fontsize=10, fontweight='bold')
        ax.set_ylabel('%', fontsize=9)
        ax.grid(axis='y', alpha=0.3)

    fig.suptitle('훅 효과: 신규 vs 재가공', fontsize=12, fontweight='bold', y=1.02)
    plt.tight_layout()
    _save_chart_to_excel(ws, fig, anchor_cell, width=900, height=350)


def add_age_efficiency_chart(ws, age_df, anchor_cell="I3"):
    """
    Chart 5: Age Group Efficiency Bar
    Sheet: Age Analysis

    Cost ratio vs Conversion ratio comparison
    """
    if age_df is None or len(age_df) == 0:
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    ages = age_df['age_group'].tolist() if 'age_group' in age_df.columns else list(range(len(age_df)))
    x = np.arange(len(ages))
    width = 0.35

    cost_ratio = age_df['비용비중'].values if '비용비중' in age_df.columns else np.zeros(len(ages))
    conv_ratio = age_df['전환비중'].values if '전환비중' in age_df.columns else np.zeros(len(ages))

    bars1 = ax.bar(x - width/2, cost_ratio, width, label='비용 비중 (%)', color='#3b82f6', alpha=0.8)
    bars2 = ax.bar(x + width/2, conv_ratio, width, label='전환 비중 (%)', color='#10b981', alpha=0.8)

    # Add efficiency score labels
    if '예산효율점수' in age_df.columns:
        for i, score in enumerate(age_df['예산효율점수']):
            max_height = max(cost_ratio[i], conv_ratio[i])
            color = '#10b981' if score >= 0.8 else '#ef4444'
            ax.text(i, max_height + 1, f'효율: {score:.2f}',
                   ha='center', fontsize=9, fontweight='bold', color=color)

    ax.set_xticks(x)
    ax.set_xticklabels(ages, fontsize=10)
    ax.set_ylabel('비중 (%)', fontsize=10)
    ax.set_title('나이대별: 비용 vs 전환 비중\n(효율 = 전환비중 / 비용비중)',
                fontsize=11, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(0, color='black', linewidth=0.5)

    plt.tight_layout()
    _save_chart_to_excel(ws, fig, anchor_cell, width=650, height=400)


def add_age_type_heatmap(ws, pivot_df, metric_name, anchor_cell="A20"):
    """
    Chart 6: Ad Type x Age Group Heatmap
    Sheet: Age Analysis

    Shows CTR or CVR patterns across ad types and age groups
    """
    if pivot_df is None or len(pivot_df) == 0:
        return

    import seaborn as sns

    fig, ax = plt.subplots(figsize=(10, 4))

    # Create heatmap
    sns.heatmap(
        pivot_df,
        annot=True,
        fmt='.2f',
        cmap='YlGn',
        linewidths=0.5,
        ax=ax,
        cbar_kws={'label': f'{metric_name} (%)'}
    )

    ax.set_title(f'소재유형 × 나이대: {metric_name}', fontsize=11, fontweight='bold')
    ax.set_xlabel('나이대', fontsize=10)
    ax.set_ylabel('소재유형', fontsize=10)

    plt.tight_layout()
    _save_chart_to_excel(ws, fig, anchor_cell, width=650, height=300)


def add_daily_combo_chart(ws, daily_df, anchor_cell="A25"):
    """
    Chart 7: Daily Cost + Conversions Combo Chart
    Sheet: Daily Trend

    Bar (cost) + Line (conversions) dual axis
    """
    if daily_df is None or len(daily_df) == 0:
        return

    fig, ax1 = plt.subplots(figsize=(14, 5))

    # Prepare data
    if 'date' in daily_df.columns:
        dates = pd.to_datetime(daily_df['date']).dt.strftime('%m-%d')
    else:
        dates = list(range(len(daily_df)))

    x = np.arange(len(dates))

    cost_col = 'cost' if 'cost' in daily_df.columns else '총비용'
    conv_col = 'conversions' if 'conversions' in daily_df.columns else '총전환'

    costs = daily_df[cost_col].values if cost_col in daily_df.columns else np.zeros(len(dates))
    convs = daily_df[conv_col].values if conv_col in daily_df.columns else np.zeros(len(dates))

    # Bar: Cost
    bars = ax1.bar(x, costs, color='#93c5fd', alpha=0.7, label='비용 (원)')
    ax1.set_ylabel('비용 (원)', color='#3b82f6', fontsize=10)
    ax1.tick_params(axis='y', labelcolor='#3b82f6')

    # Line: Conversions (dual axis)
    ax2 = ax1.twinx()
    ax2.plot(x, convs, color='#ef4444', linewidth=2, marker='o', markersize=4, label='전환수')
    ax2.set_ylabel('전환수', color='#ef4444', fontsize=10)
    ax2.tick_params(axis='y', labelcolor='#ef4444')

    ax1.set_xticks(x)
    ax1.set_xticklabels(dates, rotation=45, ha='right', fontsize=8)
    ax1.set_title('일별 비용 vs 전환', fontsize=12, fontweight='bold')

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)

    ax1.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    _save_chart_to_excel(ws, fig, anchor_cell, width=900, height=350)


def add_daily_ctr_line(ws, daily_df, anchor_cell="A45"):
    """
    Chart 8: Daily CTR Line Chart
    Sheet: Daily Trend

    Shows CTR trend with average reference line
    """
    if daily_df is None or len(daily_df) == 0:
        return

    fig, ax = plt.subplots(figsize=(14, 4))

    # Prepare data
    if 'date' in daily_df.columns:
        dates = pd.to_datetime(daily_df['date']).dt.strftime('%m-%d')
    else:
        dates = list(range(len(daily_df)))

    x = np.arange(len(dates))

    # Use CTR_calc if available, otherwise calculate
    if 'CTR' in daily_df.columns:
        ctr = daily_df['CTR'].values
    elif 'CTR_calc' in daily_df.columns:
        ctr = daily_df['CTR_calc'].values
    else:
        ctr = np.zeros(len(dates))

    # Main line
    ax.plot(x, ctr, color='#3b82f6', linewidth=2, marker='o', markersize=4, label='일별 CTR')

    # Average line
    avg_ctr = np.nanmean(ctr)
    ax.axhline(avg_ctr, color='gray', linestyle='--', linewidth=1, alpha=0.7)
    ax.text(len(x)-1, avg_ctr + 0.02, f'평균: {avg_ctr:.2f}%', fontsize=9, color='gray')

    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('CTR (%)', fontsize=10)
    ax.set_title('일별 CTR 추이', fontsize=12, fontweight='bold')
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    _save_chart_to_excel(ws, fig, anchor_cell, width=900, height=280)


# Utility function to get column letter
def get_col_letter(col_num):
    """Convert column number to Excel column letter (1=A, 27=AA, etc.)"""
    result = ""
    while col_num > 0:
        col_num, remainder = divmod(col_num - 1, 26)
        result = chr(65 + remainder) + result
    return result


# ============================================================
# v3.2.0 신규 차트
# ============================================================

def add_type_radar_chart(ws, creative_df, anchor_cell="K2"):
    """
    Chart 9 (v3.2.0): 소재유형별 레이더 차트
    Sheet: Summary Dashboard 또는 Creative TIER Analysis

    소재유형별 4지표(CTR/CVR/CPA효율/랜딩률) 종합 비교
    """
    if creative_df is None or len(creative_df) == 0:
        return

    # 소재유형별 평균 계산 (평가 가능 소재만)
    eval_df = creative_df[creative_df['TIER'].isin(['TIER1', 'TIER2', 'TIER3', 'TIER4'])]
    if len(eval_df) == 0 or '소재유형' not in eval_df.columns:
        return

    type_summary = eval_df.groupby('소재유형').agg({
        'CTR': 'mean',
        'CVR': 'mean',
        'CPA': 'mean',
        '랜딩률': 'mean'
    }).reset_index()

    if len(type_summary) == 0:
        return

    # 정규화 (0-1 범위로)
    def normalize(values, reverse=False):
        min_val, max_val = values.min(), values.max()
        if max_val == min_val:
            return np.ones(len(values)) * 0.5
        if reverse:  # CPA는 낮을수록 좋음
            return (max_val - values) / (max_val - min_val)
        return (values - min_val) / (max_val - min_val)

    type_summary['CTR_norm'] = normalize(type_summary['CTR'])
    type_summary['CVR_norm'] = normalize(type_summary['CVR'])
    type_summary['CPA_norm'] = normalize(type_summary['CPA'], reverse=True)  # 낮을수록 좋음
    type_summary['랜딩률_norm'] = normalize(type_summary['랜딩률'])

    # 레이더 차트 설정
    categories = ['CTR', 'CVR', 'CPA 효율', '랜딩률']
    N = len(categories)

    # 각도 계산
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]  # 닫힌 다각형

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    # 소재유형별 색상
    type_colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

    for idx, (_, row) in enumerate(type_summary.iterrows()):
        values = [
            row['CTR_norm'],
            row['CVR_norm'],
            row['CPA_norm'],
            row['랜딩률_norm']
        ]
        values += values[:1]  # 닫힌 다각형

        color = type_colors[idx % len(type_colors)]

        ax.plot(angles, values, 'o-', linewidth=2, color=color, label=row['소재유형'])
        ax.fill(angles, values, alpha=0.2, color=color)

    # 카테고리 라벨
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=10)
    ax.set_ylim(0, 1)

    ax.set_title('소재유형별 지표 비교\n(정규화: 외곽일수록 우수)', fontsize=12, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0), fontsize=9)

    plt.tight_layout()
    _save_chart_to_excel(ws, fig, anchor_cell, width=550, height=500)


def add_fatigue_line_chart(ws, df_valid, creative_df, anchor_cell="A60"):
    """
    Chart 10 (v3.2.0): 소재 피로도 라인 차트
    Sheet: Daily Trend 또는 Creative TIER Analysis

    상위 5개 소재의 일별 CVR 추이로 피로도 감지
    - TIER1 소재 우선
    - 비용 상위 소재 보조
    - CVR 5% 기준선 표시
    """
    if df_valid is None or len(df_valid) == 0:
        return
    if creative_df is None or len(creative_df) == 0:
        return

    # 상위 소재 선택: TIER1 우선, 비용 상위 보조
    tier1_creatives = creative_df[creative_df['TIER'] == 'TIER1']['소재명'].tolist()
    top_cost_creatives = creative_df.nlargest(5, '총비용')['소재명'].tolist()

    # 중복 제거하면서 순서 유지
    top_creatives = []
    for c in tier1_creatives + top_cost_creatives:
        if c not in top_creatives and len(top_creatives) < 5:
            top_creatives.append(c)

    if len(top_creatives) == 0:
        return

    # 일별 CVR 계산
    if '소재명' not in df_valid.columns or 'date' not in df_valid.columns:
        return

    daily_data = df_valid[df_valid['소재명'].isin(top_creatives)].copy()
    if len(daily_data) == 0:
        return

    daily_cvr = daily_data.groupby(['소재명', 'date']).agg({
        'conversions': 'sum',
        'clicks': 'sum'
    }).reset_index()

    daily_cvr['CVR'] = (daily_cvr['conversions'] / daily_cvr['clicks'].replace(0, np.nan) * 100)
    daily_cvr = daily_cvr.dropna(subset=['CVR'])

    if len(daily_cvr) == 0:
        return

    fig, ax = plt.subplots(figsize=(14, 6))

    # 소재별 색상
    colors = ['#10b981', '#3b82f6', '#ef4444', '#f59e0b', '#8b5cf6']

    for idx, creative in enumerate(top_creatives):
        creative_data = daily_cvr[daily_cvr['소재명'] == creative].sort_values('date')
        if len(creative_data) < 2:
            continue

        dates = pd.to_datetime(creative_data['date'])
        cvr_values = creative_data['CVR'].values

        # 소재명 줄임
        label = creative[:15] + '...' if len(creative) > 15 else creative

        ax.plot(dates, cvr_values,
               color=colors[idx % len(colors)],
               linewidth=2,
               marker='o',
               markersize=4,
               label=label,
               alpha=0.8)

    # CVR 5% 기준선
    ax.axhline(5.0, color='gray', linestyle='--', linewidth=1.5, alpha=0.7)
    ax.text(ax.get_xlim()[1], 5.2, 'CVR 5% 기준', fontsize=9, color='gray', ha='right')

    # 피로도 감지 주석 (하락 추세 표시)
    for idx, creative in enumerate(top_creatives):
        creative_data = daily_cvr[daily_cvr['소재명'] == creative].sort_values('date')
        if len(creative_data) >= 5:
            # 최근 5일 추세 확인
            recent_cvr = creative_data['CVR'].tail(5).values
            if len(recent_cvr) >= 5:
                trend = np.polyfit(range(len(recent_cvr)), recent_cvr, 1)[0]
                if trend < -0.5:  # 하락 추세
                    last_date = creative_data['date'].iloc[-1]
                    last_cvr = creative_data['CVR'].iloc[-1]
                    ax.annotate('⚠️ 하락',
                               xy=(pd.to_datetime(last_date), last_cvr),
                               xytext=(10, 10), textcoords='offset points',
                               fontsize=8, color='red',
                               arrowprops=dict(arrowstyle='->', color='red', alpha=0.5))

    ax.set_xlabel('날짜', fontsize=10)
    ax.set_ylabel('CVR (%)', fontsize=10)
    ax.set_title('소재 피로도 분석 (상위 소재 일별 CVR 추이)\n⚠️ = 최근 하락 추세 감지',
                fontsize=12, fontweight='bold')
    ax.legend(loc='upper left', fontsize=9, ncol=2)
    ax.grid(True, alpha=0.3)

    # X축 날짜 포맷
    fig.autofmt_xdate(rotation=45)

    plt.tight_layout()
    _save_chart_to_excel(ws, fig, anchor_cell, width=900, height=450)


def add_daily_cpa_trend_with_target(ws, daily_df, target_cpa=None, anchor_cell="A65"):
    """
    Chart 11 (v3.2.0): 일별 CPA 추이 + 목표선
    Sheet: Daily Trend

    일별 CPA 추이와 목표 CPA 비교
    """
    if daily_df is None or len(daily_df) == 0:
        return

    fig, ax = plt.subplots(figsize=(14, 5))

    # 날짜 준비
    if 'date' in daily_df.columns:
        dates = pd.to_datetime(daily_df['date'])
        x_labels = dates.dt.strftime('%m-%d')
    else:
        x_labels = list(range(len(daily_df)))

    x = np.arange(len(x_labels))

    # CPA 계산
    if 'CPA' in daily_df.columns:
        cpa_values = daily_df['CPA'].values
    elif 'cost' in daily_df.columns and 'conversions' in daily_df.columns:
        cpa_values = (daily_df['cost'] / daily_df['conversions'].replace(0, np.nan)).values
    else:
        return

    # 목표 대비 색상
    if target_cpa:
        colors = ['#10b981' if cpa <= target_cpa else '#ef4444' for cpa in cpa_values]
    else:
        colors = '#3b82f6'

    # CPA 막대 차트
    bars = ax.bar(x, cpa_values, color=colors, alpha=0.8, edgecolor='white')

    # 목표 CPA 선
    if target_cpa:
        ax.axhline(target_cpa, color='red', linestyle='--', linewidth=2, label=f'목표 CPA: {target_cpa:,.0f}원')
        ax.legend(loc='upper right', fontsize=10)

    # 평균 CPA 선
    avg_cpa = np.nanmean(cpa_values)
    ax.axhline(avg_cpa, color='gray', linestyle=':', linewidth=1.5, alpha=0.7)
    ax.text(len(x)-1, avg_cpa + 500, f'평균: {avg_cpa:,.0f}', fontsize=9, color='gray', ha='right')

    # 값 라벨 (상위만)
    for bar, cpa in zip(bars, cpa_values):
        if not np.isnan(cpa):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 200,
                   f'{cpa:,.0f}', ha='center', fontsize=7, rotation=90)

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('CPA (원)', fontsize=10)
    ax.set_title('일별 CPA 추이', fontsize=12, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    _save_chart_to_excel(ws, fig, anchor_cell, width=900, height=350)


if __name__ == "__main__":
    print("build_charts.py - Chart functions ready (v3.2.0)")
    print(f"TIER_COLORS: {TIER_COLORS}")
    print(f"TIER_ORDER: {TIER_ORDER}")
    print("New charts: add_type_radar_chart, add_fatigue_line_chart, add_daily_cpa_trend_with_target")
