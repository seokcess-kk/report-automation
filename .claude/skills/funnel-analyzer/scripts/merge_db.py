"""
퍼널 분석 - 내부 DB 연결
설계서 기준

입력 파일:
  - db_by_branch.csv: 지점, 날짜, 매체DB, 실제DB, 내원율, ROAS

분석 내용:
  - 매체DB → 실제DB 전환율 (상담실장 역량)
  - ROAS / 내원율 (지점 고객층 / 수납 역량)
  - 지점별 퍼널 효율 비교

주의: 이 영역은 광고로 컨트롤 불가능한 영역
      → 지점 컨텍스트 패널로만 표시 (분석 대상 아님)
"""
import pandas as pd
import numpy as np
import os
from datetime import datetime


def load_db_by_branch(file_path: str) -> pd.DataFrame:
    """
    db_by_branch.csv 로드

    필수 컬럼:
    - 지점
    - 날짜
    - 매체DB (광고를 통해 유입된 DB 수)
    - 실제DB (실제 상담 진행된 DB 수)
    - 내원율 (실제 내원한 비율, %)
    - ROAS (광고비 대비 매출, %)
    """
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        print(f"[Load] db_by_branch.csv: {len(df)} rows")

        # 필수 컬럼 확인
        required_cols = ['지점', '날짜', '매체DB', '실제DB']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            print(f"[WARNING] Missing columns: {missing}")
            return pd.DataFrame()

        # 날짜 파싱
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')

        # 숫자형 변환
        for col in ['매체DB', '실제DB', '내원율', 'ROAS']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df

    except FileNotFoundError:
        print(f"[INFO] db_by_branch.csv not found: {file_path}")
        return pd.DataFrame()


def calculate_funnel_metrics(db_df: pd.DataFrame) -> pd.DataFrame:
    """
    퍼널 지표 계산
    """
    if len(db_df) == 0:
        return pd.DataFrame()

    # 지점별 집계
    funnel = db_df.groupby('지점').agg(
        총매체DB=('매체DB', 'sum'),
        총실제DB=('실제DB', 'sum'),
        평균내원율=('내원율', 'mean') if '내원율' in db_df.columns else ('매체DB', lambda x: np.nan),
        평균ROAS=('ROAS', 'mean') if 'ROAS' in db_df.columns else ('매체DB', lambda x: np.nan),
        집계일수=('날짜', 'nunique'),
    ).reset_index()

    # DB 전환율 계산 (매체DB → 실제DB)
    funnel['DB전환율'] = (funnel['총실제DB'] / funnel['총매체DB'].replace(0, np.nan) * 100).round(1)

    # 효율 등급 부여
    def grade_conversion(rate):
        if pd.isna(rate):
            return None
        if rate >= 80:
            return 'A (Excellent)'
        elif rate >= 60:
            return 'B (Good)'
        elif rate >= 40:
            return 'C (Average)'
        else:
            return 'D (Needs Improvement)'

    funnel['DB전환등급'] = funnel['DB전환율'].apply(grade_conversion)

    return funnel


def merge_with_ad_data(funnel_df: pd.DataFrame, creative_df: pd.DataFrame) -> pd.DataFrame:
    """
    퍼널 데이터와 광고 데이터 병합 (지점 기준)
    """
    if len(funnel_df) == 0 or len(creative_df) == 0:
        return pd.DataFrame()

    # 지점별 광고 성과 집계
    ad_by_branch = []

    for _, row in creative_df.iterrows():
        branches = row.get('집행지점목록', [])
        if isinstance(branches, str):
            branches = [b.strip() for b in branches.split(',')]

        distribution = row.get('집행지점분포', {})
        if isinstance(distribution, str):
            try:
                distribution = eval(distribution)
            except:
                distribution = {}

        for branch in branches:
            if branch in distribution:
                weight = distribution[branch]
                total_weight = sum(distribution.values())
                ratio = weight / total_weight if total_weight > 0 else 0

                ad_by_branch.append({
                    '지점': branch,
                    '소재명': row['소재명'],
                    '비용_배분': row['총비용'] * ratio,
                    '전환_배분': row['총전환'] * ratio,
                })

    if not ad_by_branch:
        return funnel_df

    ad_branch_df = pd.DataFrame(ad_by_branch)
    ad_summary = ad_branch_df.groupby('지점').agg(
        광고비용=('비용_배분', 'sum'),
        광고전환=('전환_배분', 'sum'),
        소재수=('소재명', 'nunique'),
    ).reset_index()

    ad_summary['광고CPA'] = (ad_summary['광고비용'] / ad_summary['광고전환'].replace(0, np.nan)).round(0)

    # 병합
    merged = funnel_df.merge(ad_summary, on='지점', how='outer')

    return merged


def calculate_full_funnel_efficiency(merged_df: pd.DataFrame) -> pd.DataFrame:
    """
    전체 퍼널 효율 계산
    광고 → 매체DB → 실제DB → 내원 → 매출
    """
    if len(merged_df) == 0:
        return pd.DataFrame()

    result = merged_df.copy()

    # 전체 퍼널 효율 점수 (가중 평균)
    # - 광고CPA가 낮을수록 좋음 (역수)
    # - DB전환율이 높을수록 좋음
    # - 내원율이 높을수록 좋음
    # - ROAS가 높을수록 좋음

    # 각 지표 정규화 (0-100)
    if '광고CPA' in result.columns and result['광고CPA'].notna().any():
        max_cpa = result['광고CPA'].max()
        if max_cpa > 0:
            result['CPA점수'] = ((max_cpa - result['광고CPA']) / max_cpa * 100).round(1)

    if 'DB전환율' in result.columns:
        result['DB전환점수'] = result['DB전환율'].fillna(0)

    if '평균내원율' in result.columns:
        result['내원점수'] = result['평균내원율'].fillna(0)

    if '평균ROAS' in result.columns:
        # ROAS 100% 기준 정규화
        result['ROAS점수'] = (result['평균ROAS'] / 100 * 50).clip(0, 100).round(1)

    # 종합 점수 (광고 영역 50% + 지점 영역 50%)
    ad_score_cols = ['CPA점수']
    branch_score_cols = ['DB전환점수', '내원점수', 'ROAS점수']

    ad_available = [c for c in ad_score_cols if c in result.columns]
    branch_available = [c for c in branch_score_cols if c in result.columns]

    if ad_available:
        result['광고영역점수'] = result[ad_available].mean(axis=1).round(1)

    if branch_available:
        result['지점영역점수'] = result[branch_available].mean(axis=1).round(1)

    return result


def generate_funnel_insights(merged_df: pd.DataFrame) -> list:
    """
    퍼널 분석 기반 인사이트 생성
    """
    insights = []

    if len(merged_df) == 0:
        return insights

    # 1. 광고 효율 최고 지점
    if '광고CPA' in merged_df.columns:
        best_ad = merged_df.loc[merged_df['광고CPA'].idxmin()]
        if pd.notna(best_ad['광고CPA']):
            insights.append({
                'type': 'AD_EFFICIENCY',
                'branch': best_ad['지점'],
                'metric': 'CPA',
                'value': best_ad['광고CPA'],
                'insight': f"{best_ad['지점']} 지점이 광고 CPA {best_ad['광고CPA']:,.0f}원으로 가장 효율적"
            })

    # 2. DB 전환율 최고/최저 지점
    if 'DB전환율' in merged_df.columns:
        best_db = merged_df.loc[merged_df['DB전환율'].idxmax()]
        worst_db = merged_df.loc[merged_df['DB전환율'].idxmin()]

        if pd.notna(best_db['DB전환율']):
            insights.append({
                'type': 'DB_CONVERSION',
                'branch': best_db['지점'],
                'metric': 'DB전환율',
                'value': best_db['DB전환율'],
                'insight': f"{best_db['지점']} 지점 DB 전환율 {best_db['DB전환율']:.1f}% (상담실장 역량 우수)"
            })

        if pd.notna(worst_db['DB전환율']) and worst_db['DB전환율'] < 50:
            insights.append({
                'type': 'DB_CONVERSION_WARNING',
                'branch': worst_db['지점'],
                'metric': 'DB전환율',
                'value': worst_db['DB전환율'],
                'insight': f"{worst_db['지점']} 지점 DB 전환율 {worst_db['DB전환율']:.1f}% - 상담 프로세스 점검 필요"
            })

    # 3. 내원율 이상 지점
    if '평균내원율' in merged_df.columns:
        low_visit = merged_df[merged_df['평균내원율'] < 30]
        for _, row in low_visit.iterrows():
            insights.append({
                'type': 'VISIT_RATE_WARNING',
                'branch': row['지점'],
                'metric': '내원율',
                'value': row['평균내원율'],
                'insight': f"{row['지점']} 지점 내원율 {row['평균내원율']:.1f}% - 예약 확정률 개선 필요"
            })

    return insights


def analyze_funnel(db_path: str, creative_df: pd.DataFrame, output_dir: str) -> dict:
    """
    퍼널 분석 메인 함수
    """
    print("\n[Funnel Analysis Start]")

    # DB 로드
    db_df = load_db_by_branch(db_path)

    if len(db_df) == 0:
        print("[INFO] No internal DB data - funnel analysis skipped")
        return {
            'funnel_metrics': pd.DataFrame(),
            'merged': pd.DataFrame(),
            'insights': []
        }

    # 퍼널 지표 계산
    funnel_metrics = calculate_funnel_metrics(db_df)
    print(f"[OK] Funnel metrics calculated for {len(funnel_metrics)} branches")

    # 광고 데이터와 병합
    merged = merge_with_ad_data(funnel_metrics, creative_df)

    # 전체 퍼널 효율 계산
    merged = calculate_full_funnel_efficiency(merged)

    # 인사이트 생성
    insights = generate_funnel_insights(merged)
    print(f"[OK] Generated {len(insights)} funnel insights")

    # 저장
    os.makedirs(output_dir, exist_ok=True)

    if len(funnel_metrics) > 0:
        funnel_metrics.to_csv(
            os.path.join(output_dir, "funnel_metrics.csv"),
            index=False, encoding='utf-8-sig'
        )
        funnel_metrics.to_parquet(
            os.path.join(output_dir, "funnel_metrics.parquet"),
            index=False
        )
        print(f"[OK] Funnel metrics -> {output_dir}/funnel_metrics.csv")

    if len(merged) > 0:
        merged.to_csv(
            os.path.join(output_dir, "funnel_merged.csv"),
            index=False, encoding='utf-8-sig'
        )
        merged.to_parquet(
            os.path.join(output_dir, "funnel_merged.parquet"),
            index=False
        )
        print(f"[OK] Merged funnel -> {output_dir}/funnel_merged.csv")

    return {
        'funnel_metrics': funnel_metrics,
        'merged': merged,
        'insights': insights
    }


if __name__ == "__main__":
    import sys

    db_file = sys.argv[1] if len(sys.argv) > 1 else "input/db_by_branch.csv"
    creative_file = sys.argv[2] if len(sys.argv) > 2 else "output/creative_tier.parquet"
    output_directory = sys.argv[3] if len(sys.argv) > 3 else "output"

    creative_df = pd.read_parquet(creative_file)
    analyze_funnel(db_file, creative_df, output_directory)
