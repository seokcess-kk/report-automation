"""
소재 다차원 평가 + TIER 분류
설계서 섹션 5 기준

절대 금지 규칙 준수:
1. raw CTR/CVR/CPA 컬럼 사용 금지 → _calc 재계산값만 사용
2. 클릭=0 AND 전환>0 행의 행 단위 CVR 계산 금지
3. 파싱 실패(parse_status=FAIL) 소재 TIER 분류 금지
4. 볼륨 미달(클릭<100 AND 비용<100,000원) 소재 TIER 분류 금지
5. 지점 편중 소재 수치 보정 금지 → 주석으로 맥락만 표시
6. 소재 TIER 평가를 일별×나이대 행 단위로 수행 금지
   → 반드시 소재 단위 집계 후 TIER 부여
"""
import pandas as pd
import numpy as np
import os


# 지점별 현재 데이터 기준 평균 CPA (참고용)
BRANCH_AVG_CPA = {
    '서울': 15648, '일산': 15962, '대구': 22570,
    '천안': 32649, '부평': 34451, '수원': 42646, '창원': 48417
}


def load_target_cpa(file_path: str, evaluable_df: pd.DataFrame) -> callable:
    """
    목표 CPA 로딩 및 함수 반환
    """
    try:
        target_df = pd.read_csv(file_path, encoding='utf-8-sig')
        TARGET_CPA_MAP = dict(zip(target_df['지점'], target_df['목표CPA']))
        print(f"[INFO] target_cpa.csv 로드됨: {TARGET_CPA_MAP}")

        def get_target_cpa(지점목록):
            cpas = [TARGET_CPA_MAP.get(b) for b in 지점목록 if TARGET_CPA_MAP.get(b)]
            return sum(cpas) / len(cpas) if cpas else evaluable_df['CPA'].median()

        return get_target_cpa

    except FileNotFoundError:
        global_target_cpa = evaluable_df['CPA'].median() if len(evaluable_df) > 0 else 30000
        print(f"[INFO] target_cpa.csv 없음 → 중앙값 CPA {global_target_cpa:,.0f}원 적용")

        def get_target_cpa(지점목록):
            return global_target_cpa

        return get_target_cpa


def separate_on_off(df: pd.DataFrame):
    """
    ON/OFF 소재 분리 (TIER 분류 전 첫 번째 단계)
    """
    df_on = df[df['is_off'] == False].copy()
    df_off = df[df['is_off'] == True].copy()

    print(f"[소재 분리] ON: {len(df_on)}행 | OFF: {len(df_off)}행")

    return df_on, df_off


def aggregate_off_creatives(df_off: pd.DataFrame) -> pd.DataFrame:
    """
    OFF 소재 집계 (TIER 분류 없이 마지막 성과만 보존)
    """
    if len(df_off) == 0:
        return pd.DataFrame()

    creative_off = df_off.groupby(['소재구분', '소재유형', '소재명']).agg(
        집행지점목록=('지점', lambda x: sorted(x.dropna().unique().tolist())),
        총비용=('cost', 'sum'),
        총전환=('conversions', 'sum'),
        총클릭=('clicks', 'sum'),
        총노출=('impressions', 'sum'),
        마지막집행일=('date', 'max'),
        집행일수=('date', 'nunique'),
    ).reset_index()

    creative_off['CPA'] = (creative_off['총비용'] / creative_off['총전환'].replace(0, np.nan)).round(0)
    creative_off['CTR'] = (creative_off['총클릭'] / creative_off['총노출'].replace(0, np.nan) * 100).round(2)
    creative_off['CVR'] = (creative_off['총전환'] / creative_off['총클릭'].replace(0, np.nan) * 100).round(2)
    creative_off['상태'] = 'OFF'

    return creative_off


def aggregate_creatives(df_on: pd.DataFrame) -> pd.DataFrame:
    """
    소재 단위 집계
    집계 단위: 소재구분 + 소재유형 + 소재명 (지점/날짜코드 미포함)
    """
    GROUP_KEY = ['소재구분', '소재유형', '소재명']

    creative_df = df_on.groupby(GROUP_KEY).agg(
        집행지점목록=('지점', lambda x: sorted(x.dropna().unique().tolist())),
        집행지점분포=('지점', lambda x: x.value_counts().to_dict()),
        집행지점수=('지점', 'nunique'),
        총비용=('cost', 'sum'),
        총전환=('conversions', 'sum'),
        총클릭=('clicks', 'sum'),
        총노출=('impressions', 'sum'),
        총랜딩=('landing_views', 'sum'),
        집행일수=('date', 'nunique'),
        귀속주의건수=('attribution_caution', 'sum'),
        매칭키=('매칭키', 'first'),
    ).reset_index()

    # KPI 재계산 (집계 후 재계산 — 행 단위 CVR 사용 금지)
    creative_df['CPA'] = (creative_df['총비용'] / creative_df['총전환'].replace(0, np.nan)).round(0)
    creative_df['CTR'] = (creative_df['총클릭'] / creative_df['총노출'].replace(0, np.nan) * 100).round(2)
    creative_df['CVR'] = (creative_df['총전환'] / creative_df['총클릭'].replace(0, np.nan) * 100).round(2)
    creative_df['랜딩률'] = (creative_df['총랜딩'] / creative_df['총클릭'].replace(0, np.nan) * 100).round(1)

    return creative_df


def classify_tier(creative_df: pd.DataFrame, target_cpa_path: str) -> pd.DataFrame:
    """
    TIER 분류 (평가 가능 소재만)
    """

    # 평가 가능 여부 판단 함수
    def is_evaluable(row):
        """TIER 평가 가능 여부: 집행일수 7일 이상 + 볼륨 조건 충족"""
        day_ok = row['집행일수'] >= 7
        volume_ok = (row['총클릭'] >= 100) or (row['총비용'] >= 100_000)
        return day_ok and volume_ok

    creative_df['평가가능'] = creative_df.apply(is_evaluable, axis=1)

    # 기준선: 평가 가능 소재 기준으로만 계산
    evaluable = creative_df[creative_df['평가가능']]
    AVG_CTR = evaluable['CTR'].mean() if len(evaluable) > 0 else 0.7
    AVG_LANDING = evaluable['랜딩률'].mean() if len(evaluable) > 0 else 70.0

    print(f"[기준선] 평가가능 소재: {len(evaluable)}개 | 평균 CTR: {AVG_CTR:.2f}% | 평균 랜딩률: {AVG_LANDING:.1f}%")

    # 목표 CPA 함수 로드
    get_target_cpa = load_target_cpa(target_cpa_path, evaluable)

    # TIER 분류 함수
    def _classify(row):
        # 게이트 1: 집행일수 7일 미만
        if row['집행일수'] < 7:
            return 'UNCLASSIFIED'

        # 게이트 2: 볼륨 미달
        if not row['평가가능']:
            return 'LOW_VOLUME'

        target_cpa = get_target_cpa(row['집행지점목록'])

        cpa_ok = pd.notna(row['CPA']) and row['CPA'] <= target_cpa
        cvr_ok = pd.notna(row['CVR']) and row['CVR'] >= 5.0
        ctr_ok = pd.notna(row['CTR']) and row['CTR'] >= AVG_CTR * 1.2
        land_ok = pd.notna(row['랜딩률']) and row['랜딩률'] >= AVG_LANDING * 1.1

        # 순서 중요: if/elif 순차 처리
        if cpa_ok and cvr_ok:
            return 'TIER1'
        elif cpa_ok and not cvr_ok and (pd.notna(row['랜딩률']) and row['랜딩률'] >= 50):
            return 'TIER2'
        elif not cpa_ok and cvr_ok:
            return 'TIER3'
        else:
            return 'TIER4'

    creative_df['TIER'] = creative_df.apply(_classify, axis=1)

    # TIER 근거 문장 생성
    def tier_reason(row):
        target_cpa = get_target_cpa(row['집행지점목록'])
        if row['TIER'] == 'TIER1':
            return f"CPA({row['CPA']:,.0f}원) ≤ 목표({target_cpa:,.0f}원) AND CVR({row['CVR']:.1f}%) ≥ 5%"
        elif row['TIER'] == 'TIER2':
            return f"CPA({row['CPA']:,.0f}원) ≤ 목표({target_cpa:,.0f}원) / CVR {row['CVR']:.1f}% < 5% / 랜딩률 {row['랜딩률']:.1f}% ≥ 50%"
        elif row['TIER'] == 'TIER3':
            return f"CPA({row['CPA']:,.0f}원) > 목표 / CVR({row['CVR']:.1f}%) ≥ 5%"
        elif row['TIER'] == 'TIER4':
            return "TIER1~3 조건 미충족"
        elif row['TIER'] == 'LOW_VOLUME':
            return f"클릭 {row['총클릭']}건 / 비용 {row['총비용']:,.0f}원 — 표본 부족"
        else:
            return f"집행 {row['집행일수']}일 — 데이터 누적 중"

    creative_df['TIER_근거'] = creative_df.apply(tier_reason, axis=1)

    # TIER 분포 출력
    tier_dist = creative_df['TIER'].value_counts()
    print(f"[TIER 분포]\n{tier_dist.to_string()}")

    return creative_df


def add_branch_note(creative_df: pd.DataFrame) -> pd.DataFrame:
    """
    지점 편중 주석 추가 (70% 이상 집중 시)
    """

    def branch_note(row):
        d = row['집행지점분포']
        if not d or not isinstance(d, dict):
            return None
        total = sum(d.values())
        if total == 0:
            return None
        dominant = max(d, key=d.get)
        ratio = d[dominant] / total * 100
        if ratio >= 70:
            avg = BRANCH_AVG_CPA.get(dominant)
            note = f"[!] {dominant} {ratio:.0f}% 집중"
            if avg:
                note += f" (지점 평균 CPA {avg:,}원)"
            return note
        return None

    creative_df['지점편중주석'] = creative_df.apply(branch_note, axis=1)

    return creative_df


def add_branch_relative_flag(creative_df: pd.DataFrame, df_valid: pd.DataFrame) -> pd.DataFrame:
    """
    지점별 상대 평가 (Branch-relative Flag)
    같은 소재라도 지점에 따라 성과가 크게 다를 수 있음.
    각 지점에서의 소재 성과를 해당 지점 평균 대비로 평가.
    """
    # 소재×지점 CPA 집계
    branch_creative_df = df_valid.groupby(['소재명', '지점']).agg(
        총비용=('cost', 'sum'),
        총전환=('conversions', 'sum'),
    ).reset_index()

    branch_creative_df['CPA'] = (
        branch_creative_df['총비용'] / branch_creative_df['총전환'].replace(0, np.nan)
    ).round(0)

    # 소재별 지점 CPA 맵 생성
    branch_cpa_map = {}
    for 소재명 in branch_creative_df['소재명'].unique():
        소재_data = branch_creative_df[branch_creative_df['소재명'] == 소재명]
        branch_cpa_map[소재명] = dict(zip(소재_data['지점'], 소재_data['CPA']))

    def branch_relative_flag(row):
        """
        각 지점에서의 소재 성과를 해당 지점 평균 대비로 평가
        """
        소재 = row['소재명']
        flags = []
        if 소재 in branch_cpa_map:
            for 지점, cpa in branch_cpa_map[소재].items():
                avg = BRANCH_AVG_CPA.get(지점)
                if avg and pd.notna(cpa):
                    ratio = cpa / avg
                    if ratio <= 0.7:
                        flags.append(f"[V] {지점} TOP ({ratio:.0%})")
                    elif ratio >= 1.5:
                        flags.append(f"[X] {지점} LOW ({ratio:.0%})")
        return " | ".join(flags) if flags else None

    creative_df['지점별_상대평가'] = creative_df.apply(branch_relative_flag, axis=1)

    # 플래그 통계 출력
    has_flag = creative_df['지점별_상대평가'].notna().sum()
    print(f"[지점별 상대평가] {has_flag}개 소재에 플래그 부여")

    return creative_df


def analyze_age_groups(df_valid: pd.DataFrame) -> pd.DataFrame:
    """
    나이대별 예산 효율 분석
    """
    VALID_AGE_GROUPS = ['25-34', '35-44', '45-54', '≥55']

    df_age = df_valid[df_valid['age_group'].isin(VALID_AGE_GROUPS)].copy()

    if len(df_age) == 0:
        print("[WARNING] 유효한 나이대 데이터가 없습니다.")
        return pd.DataFrame()

    age_summary = df_age.groupby('age_group').agg(
        총비용=('cost', 'sum'),
        총전환=('conversions', 'sum'),
        총클릭=('clicks', 'sum'),
        총노출=('impressions', 'sum'),
        귀속주의=('attribution_caution', 'sum'),
    ).reset_index()

    total_cost = age_summary['총비용'].sum()
    total_conv = age_summary['총전환'].sum()

    age_summary['비용비중'] = (age_summary['총비용'] / total_cost * 100).round(1) if total_cost > 0 else 0
    age_summary['전환비중'] = (age_summary['총전환'] / total_conv * 100).round(1) if total_conv > 0 else 0
    age_summary['CPA'] = (age_summary['총비용'] / age_summary['총전환'].replace(0, np.nan)).round(0)
    age_summary['CTR'] = (age_summary['총클릭'] / age_summary['총노출'].replace(0, np.nan) * 100).round(2)

    # 예산 효율 점수
    age_summary['예산효율점수'] = (age_summary['전환비중'] / age_summary['비용비중'].replace(0, np.nan)).round(2)

    def age_efficiency_label(score):
        if pd.isna(score):
            return None
        if score >= 1.2:
            return '✅ 효율 우수 — 비중 확대 검토'
        elif score >= 0.8:
            return '➡️ 양호'
        elif score >= 0.5:
            return '⬇️ 효율 낮음 — 소재/타겟 최적화 검토'
        else:
            return '🔴 비효율 — 해당 나이대 맞춤 소재 개발 필요'

    age_summary['효율판정'] = age_summary['예산효율점수'].apply(age_efficiency_label)
    age_summary['신뢰도주의'] = age_summary['귀속주의'].apply(
        lambda n: f"⚠️ 귀속 주의 {n}건 포함" if n > 0 else None
    )

    return age_summary


def score_creatives(input_path: str, output_dir: str, target_cpa_path: str = "input/target_cpa.csv"):
    """
    메인 실행 함수
    """
    # 입력 파일 로드
    df = pd.read_parquet(input_path)
    print(f"[입력] {len(df)}행 로드됨")

    # 파싱 성공한 행만 사용
    df_valid = df[df['parse_status'] == 'OK'].copy()
    df_invalid = df[df['parse_status'] != 'OK'].copy()
    print(f"[필터링] 유효: {len(df_valid)}행 | 파싱실패: {len(df_invalid)}행 (분석 제외)")

    # ON/OFF 분리
    df_on, df_off = separate_on_off(df_valid)

    # OFF 소재 집계
    creative_off = aggregate_off_creatives(df_off)

    # ON 소재 집계
    creative_df = aggregate_creatives(df_on)

    # TIER 분류
    creative_df = classify_tier(creative_df, target_cpa_path)

    # 지점 편중 주석 추가
    creative_df = add_branch_note(creative_df)

    # 지점별 상대 평가 추가
    creative_df = add_branch_relative_flag(creative_df, df_on)

    # 나이대 분석
    age_summary = analyze_age_groups(df_valid)

    # 결과 저장
    os.makedirs(output_dir, exist_ok=True)

    creative_df.to_parquet(os.path.join(output_dir, "creative_tier.parquet"), index=False)
    creative_df.to_csv(os.path.join(output_dir, "creative_tier.csv"), index=False, encoding='utf-8-sig')
    print(f"[OK] 소재 TIER 분석 → {output_dir}/creative_tier.parquet")

    if len(creative_off) > 0:
        creative_off.to_parquet(os.path.join(output_dir, "creative_off.parquet"), index=False)
        creative_off.to_csv(os.path.join(output_dir, "creative_off.csv"), index=False, encoding='utf-8-sig')
        print(f"[OK] OFF 소재 → {output_dir}/creative_off.parquet")

    if len(age_summary) > 0:
        age_summary.to_parquet(os.path.join(output_dir, "age_analysis.parquet"), index=False)
        age_summary.to_csv(os.path.join(output_dir, "age_analysis.csv"), index=False, encoding='utf-8-sig')
        print(f"[OK] 나이대 분석 → {output_dir}/age_analysis.parquet")

    return {
        'creative_tier': creative_df,
        'creative_off': creative_off,
        'age_summary': age_summary,
        'df_valid': df_valid
    }


if __name__ == "__main__":
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else "output/parsed.parquet"
    output_directory = sys.argv[2] if len(sys.argv) > 2 else "output"
    target_cpa_file = sys.argv[3] if len(sys.argv) > 3 else "input/target_cpa.csv"
    score_creatives(input_file, output_directory, target_cpa_file)
