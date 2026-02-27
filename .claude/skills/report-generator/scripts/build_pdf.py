"""
PDF 리포트 생성
설계서 섹션 8 기준

PDF 요약 (2페이지):
[Page 1]
  - 분석 기간 / 총 광고비 / 총 전환(상담신청) / 평균 CPA
  - TIER 분포 요약
  - 지점별 성과 요약 테이블
  - 핵심 인사이트 3줄

[Page 2]
  - 소재 TIER 분류 결과 (상위/하위 소재)
  - 훅 개선 효과 하이라이트
  - 이번 주 추천 액션 플랜
  - 이상 감지 알림 + 데이터 참고 사항
"""
import pandas as pd
import numpy as np
import os
from datetime import datetime

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("[WARNING] reportlab not installed -> pip install reportlab")


def register_korean_font():
    """한글 폰트 등록 (시스템에 있는 경우)"""
    font_paths = [
        'C:/Windows/Fonts/malgun.ttf',  # Windows
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',  # Linux
        '/System/Library/Fonts/AppleGothic.ttf',  # Mac
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('Korean', font_path))
                return 'Korean'
            except:
                pass

    return None


def create_table_style(font_name=None):
    """테이블 스타일 생성 (한글 폰트 지원)"""
    style_list = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F2F2F2')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#E8E8E8')]),
    ]
    # 한글 폰트 적용
    if font_name:
        style_list.append(('FONTNAME', (0, 0), (-1, -1), font_name))
    return TableStyle(style_list)


def build_pdf(output_dir: str, creative_df: pd.DataFrame, age_df: pd.DataFrame,
              df_valid: pd.DataFrame, off_df: pd.DataFrame = None,
              hook_type_df: pd.DataFrame = None, anomalies_df: pd.DataFrame = None):
    """
    PDF 리포트 생성 (2페이지)
    """
    if not REPORTLAB_AVAILABLE:
        print("[ERROR] reportlab not installed. pip install reportlab")
        return None

    # 출력 경로 설정
    os.makedirs(output_dir, exist_ok=True)
    today = datetime.now().strftime('%Y%m%d')
    output_path = os.path.join(output_dir, f"tiktok_summary_{today}.pdf")

    # PDF 문서 생성
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )

    # 스타일 설정
    styles = getSampleStyleSheet()
    korean_font = register_korean_font()

    if korean_font:
        title_style = ParagraphStyle(
            'TitleKorean',
            parent=styles['Heading1'],
            fontName=korean_font,
            fontSize=18,
            spaceAfter=10
        )
        normal_style = ParagraphStyle(
            'NormalKorean',
            parent=styles['Normal'],
            fontName=korean_font,
            fontSize=10,
            spaceAfter=5
        )
        heading_style = ParagraphStyle(
            'HeadingKorean',
            parent=styles['Heading2'],
            fontName=korean_font,
            fontSize=14,
            spaceAfter=8
        )
    else:
        title_style = styles['Heading1']
        normal_style = styles['Normal']
        heading_style = styles['Heading2']

    # 컨텐츠 빌드
    content = []

    # ===== PAGE 1 =====
    # 제목
    content.append(Paragraph("TikTok 광고 분석 리포트", title_style))
    content.append(Spacer(1, 5*mm))

    # 기본 정보
    date_min = df_valid['date'].min().strftime('%Y-%m-%d')
    date_max = df_valid['date'].max().strftime('%Y-%m-%d')
    total_cost = df_valid['cost'].sum()
    total_conv = df_valid['conversions'].sum()
    avg_cpa = total_cost / total_conv if total_conv > 0 else 0

    info_text = f"""
    <b>분석 기간:</b> {date_min} ~ {date_max}<br/>
    <b>생성일:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/>
    """
    content.append(Paragraph(info_text, normal_style))
    content.append(Spacer(1, 5*mm))

    # KPI 요약 테이블
    content.append(Paragraph("1. 전체 KPI 요약", heading_style))

    kpi_data = [
        ['지표', '값'],
        ['총 광고비', f'{total_cost:,.0f}원'],
        ['총 전환수', f'{total_conv:,.0f}건'],
        ['평균 CPA', f'{avg_cpa:,.0f}원'],
        ['평균 CTR', f'{df_valid["clicks"].sum() / df_valid["impressions"].sum() * 100:.2f}%'],
        ['평균 CVR', f'{total_conv / df_valid["clicks"].sum() * 100:.2f}%'],
    ]

    kpi_table = Table(kpi_data, colWidths=[80*mm, 80*mm])
    kpi_table.setStyle(create_table_style(korean_font))
    content.append(kpi_table)
    content.append(Spacer(1, 8*mm))

    # TIER 분포
    content.append(Paragraph("2. TIER 분포", heading_style))

    tier_dist = creative_df['TIER'].value_counts()
    tier_data = [['TIER', '소재수', '설명']]
    tier_desc = {
        'TIER1': 'CPA 달성 + CVR 5% 이상 (최우수)',
        'TIER2': 'CTR 우수 / CPA 초과',
        'TIER3': '랜딩률 우수 / CVR 저조',
        'TIER4': '전 지표 평균 이하',
        'LOW_VOLUME': '표본 부족 (클릭<100, 비용<10만)',
        'UNCLASSIFIED': '집행일수 7일 미만'
    }
    for tier in ['TIER1', 'TIER2', 'TIER3', 'TIER4', 'LOW_VOLUME', 'UNCLASSIFIED']:
        if tier in tier_dist.index:
            tier_data.append([tier, str(tier_dist[tier]), tier_desc.get(tier, '')])

    tier_table = Table(tier_data, colWidths=[30*mm, 25*mm, 105*mm])
    tier_table.setStyle(create_table_style(korean_font))
    content.append(tier_table)
    content.append(Spacer(1, 8*mm))

    # 지점별 성과 요약
    content.append(Paragraph("3. 지점별 성과 요약", heading_style))

    branch_summary = df_valid.groupby('지점').agg(
        Cost=('cost', 'sum'),
        Conv=('conversions', 'sum'),
    ).reset_index()
    branch_summary['CPA'] = (branch_summary['Cost'] / branch_summary['Conv'].replace(0, np.nan)).round(0)
    branch_summary = branch_summary.sort_values('CPA')

    branch_data = [['지점', '비용', '전환수', 'CPA']]
    for _, row in branch_summary.iterrows():
        branch_data.append([
            row['지점'],
            f"{row['Cost']:,.0f}원",
            f"{row['Conv']:.0f}건",
            f"{row['CPA']:,.0f}원" if pd.notna(row['CPA']) else 'N/A'
        ])

    branch_table = Table(branch_data, colWidths=[35*mm, 45*mm, 35*mm, 45*mm])
    branch_table.setStyle(create_table_style(korean_font))
    content.append(branch_table)

    # ===== PAGE 2 =====
    content.append(PageBreak())

    # Top/Bottom 소재
    content.append(Paragraph("4. 최우수 성과 소재 (TIER1)", heading_style))

    tier1 = creative_df[creative_df['TIER'] == 'TIER1'].nsmallest(5, 'CPA')
    if len(tier1) > 0:
        top_data = [['소재명', 'CPA', 'CVR', 'CTR']]
        for _, row in tier1.iterrows():
            name = row['소재명'][:25] + '...' if len(row['소재명']) > 25 else row['소재명']
            top_data.append([
                name,
                f"{row['CPA']:,.0f}원" if pd.notna(row['CPA']) else 'N/A',
                f"{row['CVR']:.2f}%" if pd.notna(row['CVR']) else 'N/A',
                f"{row['CTR']:.2f}%" if pd.notna(row['CTR']) else 'N/A',
            ])

        top_table = Table(top_data, colWidths=[80*mm, 30*mm, 25*mm, 25*mm])
        top_table.setStyle(create_table_style(korean_font))
        content.append(top_table)
    else:
        content.append(Paragraph("TIER1 소재가 없습니다.", normal_style))

    content.append(Spacer(1, 8*mm))

    # 훅 개선 효과
    content.append(Paragraph("5. 훅 개선 효과 요약", heading_style))

    if hook_type_df is not None and len(hook_type_df) > 0:
        hook_data = [['소재유형', '신규 CTR', '재가공 CTR', '변화율', '판정']]
        for _, row in hook_type_df.iterrows():
            hook_data.append([
                row.get('소재유형', 'N/A'),
                f"{row.get('신규_CTR', 0):.2f}%" if pd.notna(row.get('신규_CTR')) else 'N/A',
                f"{row.get('재가공_CTR', 0):.2f}%" if pd.notna(row.get('재가공_CTR')) else 'N/A',
                f"{row.get('CTR_변화율', 0):+.1f}%" if pd.notna(row.get('CTR_변화율')) else 'N/A',
                str(row.get('훅판정', 'N/A'))[:30]
            ])

        hook_table = Table(hook_data, colWidths=[35*mm, 30*mm, 30*mm, 25*mm, 40*mm])
        hook_table.setStyle(create_table_style(korean_font))
        content.append(hook_table)
    else:
        content.append(Paragraph("훅 비교 데이터가 없습니다.", normal_style))

    content.append(Spacer(1, 8*mm))

    # 이상 감지 알림
    content.append(Paragraph("6. 이상 감지 알림", heading_style))

    if anomalies_df is not None and len(anomalies_df) > 0:
        alert_count = len(anomalies_df)
        content.append(Paragraph(f"총 {alert_count}건의 이상치가 감지되었습니다. 상세 내용은 Excel 리포트를 확인하세요.", normal_style))

        # 주요 이상치 유형별 카운트
        if '감지유형' in anomalies_df.columns:
            type_counts = anomalies_df['감지유형'].value_counts()
            for atype, count in type_counts.items():
                content.append(Paragraph(f"  - {atype}: {count}건", normal_style))
    else:
        content.append(Paragraph("감지된 이상치가 없습니다.", normal_style))

    content.append(Spacer(1, 8*mm))

    # 데이터 참고 사항
    content.append(Paragraph("7. 데이터 참고 사항", heading_style))

    notes = []
    if 'attribution_caution' in df_valid.columns:
        caution_count = df_valid['attribution_caution'].sum()
        if caution_count > 0:
            notes.append(f"- 귀속 주의: {caution_count}건 (클릭=0, 전환>0)")

    if off_df is not None and len(off_df) > 0:
        notes.append(f"- OFF 소재: {len(off_df)}개 (TIER 분석에서 제외됨)")

    low_vol = creative_df[creative_df['TIER'] == 'LOW_VOLUME']
    if len(low_vol) > 0:
        notes.append(f"- 표본 부족 소재: {len(low_vol)}개 (추가 데이터 필요)")

    if notes:
        for note in notes:
            content.append(Paragraph(note, normal_style))
    else:
        content.append(Paragraph("특이사항 없음", normal_style))

    # PDF 빌드
    doc.build(content)
    print(f"[OK] PDF report generated -> {output_path}")

    return output_path


def main(data_dir: str = "output", output_dir: str = None):
    """
    메인 실행 함수
    """
    if output_dir is None:
        today = datetime.now().strftime('%Y%m%d')
        output_dir = os.path.join(data_dir, today)

    # 데이터 로드
    creative_df = pd.read_parquet(os.path.join(data_dir, "creative_tier.parquet"))
    print(f"[Load] Creative TIER: {len(creative_df)}")

    try:
        age_df = pd.read_parquet(os.path.join(data_dir, "age_analysis.parquet"))
    except FileNotFoundError:
        age_df = pd.DataFrame()

    try:
        off_df = pd.read_parquet(os.path.join(data_dir, "creative_off.parquet"))
    except FileNotFoundError:
        off_df = pd.DataFrame()

    try:
        df_valid = pd.read_parquet(os.path.join(data_dir, "parsed.parquet"))
        df_valid = df_valid[df_valid['parse_status'] == 'OK']
    except FileNotFoundError:
        print("[ERROR] parsed.parquet not found")
        return None

    try:
        hook_type_df = pd.read_parquet(os.path.join(data_dir, "hook_type_comparison.parquet"))
    except FileNotFoundError:
        hook_type_df = None

    try:
        anomalies_df = pd.read_csv(os.path.join(data_dir, "anomalies.csv"))
    except FileNotFoundError:
        anomalies_df = None

    return build_pdf(output_dir, creative_df, age_df, df_valid, off_df, hook_type_df, anomalies_df)


if __name__ == "__main__":
    import sys
    data_directory = sys.argv[1] if len(sys.argv) > 1 else "output"
    output_directory = sys.argv[2] if len(sys.argv) > 2 else None
    main(data_directory, output_directory)
