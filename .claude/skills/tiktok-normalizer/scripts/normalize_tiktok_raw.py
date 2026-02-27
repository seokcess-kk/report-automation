"""
TikTok 광고 raw CSV를 분석 가능한 표준 형식으로 변환
- 광고 ID 지수 표기 보정
- KPI 재계산 (_calc)
- 귀속 주의 플래그 생성
"""
import pandas as pd
import numpy as np
import os


def normalize(input_path: str, output_path: str):
    """
    TikTok raw CSV를 표준화된 parquet 형식으로 변환
    """
    # 1. 광고 ID 문자열 강제 로딩 (지수 표기 정밀도 손실 방지)
    df = pd.read_csv(input_path, dtype={'광고 ID': str}, encoding='utf-8-sig')

    # 2. 컬럼명 표준화
    COLUMN_ALIAS = {
        '클릭수(목적지)': 'clicks',
        '노출수': 'impressions',
        '전환수': 'conversions',
        '비용': 'cost',
        '랜딩 페이지 조회(웹사이트)': 'landing_views',
        '일별': 'date',
        '나이': 'age_group',
        '광고 이름': 'ad_name',
        '광고 ID': 'ad_id',
        '도달': 'reach',
        '동영상 조회수': 'video_views',
    }
    df = df.rename(columns={k: v for k, v in COLUMN_ALIAS.items() if k in df.columns})

    # 3. 숫자형 강제 변환
    NUM_COLS = ['clicks', 'impressions', 'conversions', 'cost', 'landing_views', 'reach']
    for col in NUM_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(',', ''), errors='coerce'
            ).fillna(0)

    # 4. KPI 재계산 (_calc 컬럼만 이후 분석에 사용)
    df['CTR_calc'] = (df['clicks'] / df['impressions'].replace(0, np.nan) * 100).round(4)
    df['CVR_calc'] = (df['conversions'] / df['clicks'].replace(0, np.nan) * 100).round(4)
    df['CPA_calc'] = (df['cost'] / df['conversions'].replace(0, np.nan)).round(0)
    df['LPV_rate_calc'] = (df['landing_views'] / df['clicks'].replace(0, np.nan) * 100).round(4)
    # raw 비율 컬럼은 참고용으로 보존 (분석에 사용 금지)

    # 5. 귀속 주의 플래그 (클릭=0 AND 전환>0 → 뷰스루/지연 전환 추정)
    df['attribution_caution'] = (df['clicks'] == 0) & (df['conversions'] > 0)
    n_caution = df['attribution_caution'].sum()
    if n_caution > 0:
        print(f"[WARNING] attribution_caution {n_caution}건 감지 (클릭=0/전환>0)")

    # 6. 날짜 파싱
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # 7. 통화 단일값 확인
    if '통화' in df.columns:
        currencies = df['통화'].unique()
        if len(currencies) > 1:
            print(f"[WARNING] 통화 혼재 감지: {currencies}")

    # 8. 중복 행 감지
    dup_key = ['ad_id', 'date', 'age_group']
    if all(k in df.columns for k in dup_key):
        dupes = df[df.duplicated(dup_key, keep=False)]
        if len(dupes) > 0:
            print(f"[WARNING] 중복 행 {len(dupes)}건 감지")

    # 9. 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_parquet(output_path, index=False)
    print(f"[OK] 표준화 완료: {len(df)}행 → {output_path}")
    return df


if __name__ == "__main__":
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else "input/tiktok_raw.csv"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "output/normalized.parquet"
    normalize(input_file, output_file)
