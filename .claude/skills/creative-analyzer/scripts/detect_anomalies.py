"""
이상치 감지
설계서 기준

감지 대상:
1. 클릭=0 AND 전환>0 (뷰스루/지연 전환 추정)
2. CVR 이상 고점 (평균의 3배 이상)
3. CPA 이상 저점/고점 (평균의 50% 미만 또는 200% 초과)
4. 급격한 성과 변동 (일별 추이)
5. 지점별 성과 편차 (동일 소재, 지점간 CPA 3배 이상 차이)
"""
import pandas as pd
import numpy as np
import os


def detect_attribution_anomaly(df: pd.DataFrame) -> pd.DataFrame:
    """
    클릭=0 AND 전환>0 이상치 감지
    → 뷰스루 전환 또는 지연 전환 추정
    """
    anomalies = df[
        (df['clicks'] == 0) & (df['conversions'] > 0)
    ].copy()

    if len(anomalies) > 0:
        anomalies['이상유형'] = '귀속 주의 (클릭=0, 전환>0)'
        anomalies['심각도'] = 'WARNING'
        anomalies['권장조치'] = '뷰스루/지연 전환 가능성 - CVR 해석 주의'

    return anomalies


def detect_cvr_outliers(creative_df: pd.DataFrame, threshold_multiplier: float = 3.0) -> pd.DataFrame:
    """
    CVR 이상 고점 감지
    평균의 threshold_multiplier배 이상
    """
    avg_cvr = creative_df['CVR'].mean()
    std_cvr = creative_df['CVR'].std()

    if pd.isna(avg_cvr) or avg_cvr == 0:
        return pd.DataFrame()

    outliers = creative_df[
        creative_df['CVR'] >= avg_cvr * threshold_multiplier
    ].copy()

    if len(outliers) > 0:
        outliers['이상유형'] = f'CVR 이상 고점 (평균 {avg_cvr:.2f}%의 {threshold_multiplier}배 이상)'
        outliers['심각도'] = 'INFO'
        outliers['권장조치'] = '표본 크기 확인 - 소량 데이터 과대평가 가능성'
        outliers['기준값'] = f'평균 CVR: {avg_cvr:.2f}%'

    return outliers


def detect_cpa_outliers(creative_df: pd.DataFrame) -> pd.DataFrame:
    """
    CPA 이상 저점/고점 감지
    평균의 50% 미만 또는 200% 초과
    """
    avg_cpa = creative_df['CPA'].mean()

    if pd.isna(avg_cpa) or avg_cpa == 0:
        return pd.DataFrame()

    low_outliers = creative_df[
        (creative_df['CPA'] < avg_cpa * 0.5) & (creative_df['CPA'] > 0)
    ].copy()

    high_outliers = creative_df[
        creative_df['CPA'] > avg_cpa * 2.0
    ].copy()

    if len(low_outliers) > 0:
        low_outliers['이상유형'] = f'CPA 이상 저점 (평균 {avg_cpa:,.0f}원의 50% 미만)'
        low_outliers['심각도'] = 'INFO'
        low_outliers['권장조치'] = '성공 요인 분석 - 스케일업 검토'
        low_outliers['기준값'] = f'평균 CPA: {avg_cpa:,.0f}원'

    if len(high_outliers) > 0:
        high_outliers['이상유형'] = f'CPA 이상 고점 (평균 {avg_cpa:,.0f}원의 200% 초과)'
        high_outliers['심각도'] = 'WARNING'
        high_outliers['권장조치'] = '효율 저하 원인 분석 - 예산 재배분 검토'
        high_outliers['기준값'] = f'평균 CPA: {avg_cpa:,.0f}원'

    return pd.concat([low_outliers, high_outliers], ignore_index=True) if len(low_outliers) > 0 or len(high_outliers) > 0 else pd.DataFrame()


def detect_branch_variance(df_valid: pd.DataFrame, threshold_ratio: float = 3.0) -> pd.DataFrame:
    """
    지점별 성과 편차 감지
    동일 소재인데 지점간 CPA 차이가 threshold_ratio배 이상
    """
    # 소재×지점 집계
    branch_creative = df_valid.groupby(['소재명', '지점']).agg(
        총비용=('cost', 'sum'),
        총전환=('conversions', 'sum'),
    ).reset_index()

    branch_creative['CPA'] = (
        branch_creative['총비용'] / branch_creative['총전환'].replace(0, np.nan)
    ).round(0)

    # 소재별 CPA 최소/최대 비교
    anomalies = []

    for 소재명 in branch_creative['소재명'].unique():
        소재_data = branch_creative[branch_creative['소재명'] == 소재명]
        소재_data = 소재_data[소재_data['CPA'] > 0]  # CPA 계산 가능한 것만

        if len(소재_data) < 2:
            continue

        min_cpa = 소재_data['CPA'].min()
        max_cpa = 소재_data['CPA'].max()

        if min_cpa > 0 and max_cpa / min_cpa >= threshold_ratio:
            min_branch = 소재_data[소재_data['CPA'] == min_cpa]['지점'].values[0]
            max_branch = 소재_data[소재_data['CPA'] == max_cpa]['지점'].values[0]

            anomalies.append({
                '소재명': 소재명,
                '이상유형': f'지점간 CPA 편차 {threshold_ratio}배 이상',
                '심각도': 'WARNING',
                '최저CPA_지점': min_branch,
                '최저CPA': min_cpa,
                '최고CPA_지점': max_branch,
                '최고CPA': max_cpa,
                'CPA_배율': round(max_cpa / min_cpa, 1),
                '권장조치': f'{min_branch} 지점 성공 요인 분석 -> {max_branch} 지점 적용 검토'
            })

    return pd.DataFrame(anomalies) if anomalies else pd.DataFrame()


def detect_daily_trend_anomaly(df_valid: pd.DataFrame, threshold_pct: float = 50.0) -> pd.DataFrame:
    """
    일별 급격한 성과 변동 감지
    전일 대비 threshold_pct% 이상 변동
    """
    # 일별 집계
    daily = df_valid.groupby('date').agg(
        총비용=('cost', 'sum'),
        총전환=('conversions', 'sum'),
        총클릭=('clicks', 'sum'),
    ).reset_index().sort_values('date')

    daily['CPA'] = (daily['총비용'] / daily['총전환'].replace(0, np.nan)).round(0)
    daily['전일CPA'] = daily['CPA'].shift(1)
    daily['CPA_변화율'] = ((daily['CPA'] - daily['전일CPA']) / daily['전일CPA'].replace(0, np.nan) * 100).round(1)

    anomalies = daily[
        (abs(daily['CPA_변화율']) >= threshold_pct) & (daily['전일CPA'] > 0)
    ].copy()

    if len(anomalies) > 0:
        anomalies['이상유형'] = anomalies['CPA_변화율'].apply(
            lambda x: f'CPA 급등 (+{x:.1f}%)' if x > 0 else f'CPA 급락 ({x:.1f}%)'
        )
        anomalies['심각도'] = 'INFO'
        anomalies['권장조치'] = '해당일 소재/지점별 성과 점검'

    return anomalies


def detect_all_anomalies(df_valid: pd.DataFrame, creative_df: pd.DataFrame, output_dir: str) -> dict:
    """
    모든 이상치 감지 실행
    """
    print("\n[이상치 감지 시작]")

    results = {}

    # 1. 귀속 주의 (클릭=0, 전환>0)
    attribution = detect_attribution_anomaly(df_valid)
    results['attribution'] = attribution
    print(f"  - 귀속 주의: {len(attribution)}건")

    # 2. CVR 이상 고점
    cvr_outliers = detect_cvr_outliers(creative_df)
    results['cvr_outliers'] = cvr_outliers
    print(f"  - CVR 이상 고점: {len(cvr_outliers)}건")

    # 3. CPA 이상 저점/고점
    cpa_outliers = detect_cpa_outliers(creative_df)
    results['cpa_outliers'] = cpa_outliers
    print(f"  - CPA 이상치: {len(cpa_outliers)}건")

    # 4. 지점별 성과 편차
    branch_variance = detect_branch_variance(df_valid)
    results['branch_variance'] = branch_variance
    print(f"  - 지점별 편차: {len(branch_variance)}건")

    # 5. 일별 급변동
    daily_anomaly = detect_daily_trend_anomaly(df_valid)
    results['daily_anomaly'] = daily_anomaly
    print(f"  - 일별 급변동: {len(daily_anomaly)}건")

    # 통합 리포트 생성
    all_anomalies = []

    for key, df in results.items():
        if len(df) > 0:
            df_copy = df.copy()
            df_copy['감지유형'] = key
            all_anomalies.append(df_copy)

    if all_anomalies:
        combined = pd.concat(all_anomalies, ignore_index=True)

        # 저장
        os.makedirs(output_dir, exist_ok=True)
        combined.to_csv(os.path.join(output_dir, "anomalies.csv"), index=False, encoding='utf-8-sig')
        print(f"[OK] 이상치 리포트 -> {output_dir}/anomalies.csv (총 {len(combined)}건)")

        results['combined'] = combined
    else:
        print("[OK] 감지된 이상치 없음")
        results['combined'] = pd.DataFrame()

    return results


if __name__ == "__main__":
    import sys

    parsed_file = sys.argv[1] if len(sys.argv) > 1 else "output/parsed.parquet"
    creative_file = sys.argv[2] if len(sys.argv) > 2 else "output/creative_tier.parquet"
    output_directory = sys.argv[3] if len(sys.argv) > 3 else "output"

    df_valid = pd.read_parquet(parsed_file)
    df_valid = df_valid[df_valid['parse_status'] == 'OK']

    creative_df = pd.read_parquet(creative_file)

    detect_all_anomalies(df_valid, creative_df, output_directory)
