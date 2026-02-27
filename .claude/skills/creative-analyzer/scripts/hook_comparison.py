"""
신규↔재가공 훅 효과 비교
설계서 섹션 6 기준

재가공(재) 소재의 특성:
  - 원본 영상은 동일
  - 썸네일 또는 초기 카피(훅)만 변경
  → CTR 변화 = 훅 효과를 가장 직접적으로 측정

매칭 방식 (3단계):
  A. Lineage 매칭: creative_lineage.csv 기반 명시적 매핑 (가장 정확)
  B. Strict 매칭: 소재유형 + 소재명 완전 일치
  C. 소재유형 집계 비교: 신규 vs 재가공 집계 단위 비교
"""
import pandas as pd
import numpy as np
import os


def load_creative_lineage(file_path: str) -> pd.DataFrame:
    """
    creative_lineage.csv 로드

    파일 형식:
    creative_group_id,원본소재명,재가공소재명,변경요소,비고

    Returns:
        lineage DataFrame or empty DataFrame if not found
    """
    try:
        lineage_df = pd.read_csv(file_path, encoding='utf-8-sig')
        required_cols = ['원본소재명', '재가공소재명']
        if all(c in lineage_df.columns for c in required_cols):
            print(f"[Lineage] creative_lineage.csv loaded: {len(lineage_df)} mappings")
            return lineage_df
        else:
            print(f"[WARNING] creative_lineage.csv missing required columns")
            return pd.DataFrame()
    except FileNotFoundError:
        print(f"[INFO] creative_lineage.csv not found - using automatic matching")
        return pd.DataFrame()


def match_by_lineage(creative_df: pd.DataFrame, lineage_df: pd.DataFrame) -> pd.DataFrame:
    """
    creative_lineage.csv 기반 명시적 매핑

    Returns:
        lineage_pairs: 매핑된 쌍 DataFrame
    """
    if len(lineage_df) == 0:
        return pd.DataFrame()

    신규 = creative_df[creative_df['소재구분'] == '신규'].copy()
    재가공 = creative_df[creative_df['소재구분'] == '재가공'].copy()

    lineage_pairs = []

    for _, mapping in lineage_df.iterrows():
        원본명 = mapping['원본소재명']
        재가공명 = mapping['재가공소재명']

        # 신규 소재에서 원본 찾기
        orig_matches = 신규[신규['소재명'].str.contains(원본명, na=False, regex=False)]
        # 재가공 소재에서 재가공 찾기
        rework_matches = 재가공[재가공['소재명'].str.contains(재가공명, na=False, regex=False)]

        if len(orig_matches) > 0 and len(rework_matches) > 0:
            for _, orig in orig_matches.iterrows():
                for _, rework in rework_matches.iterrows():
                    pair = {
                        '소재유형': orig['소재유형'],
                        '소재명': orig['소재명'],
                        '원본소재명': orig['소재명'],
                        '재가공소재명': rework['소재명'],
                        'CTR_신규': orig['CTR'],
                        'CVR_신규': orig['CVR'],
                        'CPA_신규': orig['CPA'],
                        'CTR_재가공': rework['CTR'],
                        'CVR_재가공': rework['CVR'],
                        'CPA_재가공': rework['CPA'],
                        'match_type': 'lineage',
                        '변경요소': mapping.get('변경요소', 'N/A'),
                        'creative_group_id': mapping.get('creative_group_id', 'N/A'),
                    }
                    lineage_pairs.append(pair)

    if lineage_pairs:
        result = pd.DataFrame(lineage_pairs)
        print(f"[Lineage Matching] {len(result)} pairs found")
        return result

    return pd.DataFrame()


def match_hook_pairs(creative_df: pd.DataFrame, lineage_path: str = None) -> tuple:
    """
    신규↔재가공 훅 쌍 매칭

    Args:
        creative_df: 소재 DataFrame
        lineage_path: creative_lineage.csv 경로 (optional)

    Returns:
        all_pairs: 모든 매칭된 쌍 DataFrame (lineage + strict)
        type_comparison: 소재유형별 집계 비교 DataFrame
    """
    신규 = creative_df[creative_df['소재구분'] == '신규'].copy()
    재가공 = creative_df[creative_df['소재구분'] == '재가공'].copy()

    print(f"[Hook Comparison] Original: {len(신규)} | Reworked: {len(재가공)}")

    all_pairs = pd.DataFrame()

    # A. Lineage 매칭 (creative_lineage.csv 기반)
    if lineage_path:
        lineage_df = load_creative_lineage(lineage_path)
        if len(lineage_df) > 0:
            lineage_pairs = match_by_lineage(creative_df, lineage_df)
            if len(lineage_pairs) > 0:
                all_pairs = pd.concat([all_pairs, lineage_pairs], ignore_index=True)

    # B. Strict 매칭 (소재유형 + 소재명 완전 일치)
    if len(신규) > 0 and len(재가공) > 0:
        strict_pairs = 신규.merge(
            재가공,
            on=['소재유형', '소재명'],
            suffixes=('_신규', '_재가공'),
            how='inner'
        )
        strict_pairs['match_type'] = 'strict'
        print(f"[Strict Matching] {len(strict_pairs)} pairs found")

        if len(strict_pairs) > 0:
            all_pairs = pd.concat([all_pairs, strict_pairs], ignore_index=True)
    else:
        print("[Strict Matching] No matching pairs")

    # B. 소재유형 집계 비교 (Strict 매칭 건수 보완용)
    type_comparison = creative_df.groupby(['소재유형', '소재구분']).agg(
        소재수=('소재명', 'count'),
        총비용=('총비용', 'sum'),
        총전환=('총전환', 'sum'),
        총클릭=('총클릭', 'sum'),
        총노출=('총노출', 'sum'),
        avg_CTR=('CTR', 'mean'),
        avg_CVR=('CVR', 'mean'),
        avg_CPA=('CPA', 'mean'),
        avg_랜딩률=('랜딩률', 'mean'),
    ).reset_index()

    # 재계산 (집계 기반)
    type_comparison['집계_CTR'] = (type_comparison['총클릭'] / type_comparison['총노출'].replace(0, np.nan) * 100).round(2)
    type_comparison['집계_CVR'] = (type_comparison['총전환'] / type_comparison['총클릭'].replace(0, np.nan) * 100).round(2)
    type_comparison['집계_CPA'] = (type_comparison['총비용'] / type_comparison['총전환'].replace(0, np.nan)).round(0)

    return strict_pairs, type_comparison


def hook_verdict(orig_ctr: float, re_ctr: float, orig_cvr: float, re_cvr: float) -> str:
    """
    훅 개선 효과 판정

    Args:
        orig_ctr: 원본(신규) CTR
        re_ctr: 재가공 CTR
        orig_cvr: 원본(신규) CVR
        re_cvr: 재가공 CVR

    Returns:
        판정 문자열
    """
    if pd.isna(orig_ctr) or pd.isna(re_ctr):
        return '데이터 부족 — 판정 불가'

    ctr_up = re_ctr > orig_ctr
    cvr_up = re_cvr > orig_cvr if pd.notna(orig_cvr) and pd.notna(re_cvr) else None

    if ctr_up and cvr_up:
        return '재가공 유효 — 클릭, 전환 모두 개선'
    elif ctr_up and cvr_up is False:
        return '부분 효과 — 클릭 UP, 전환 DOWN (랜딩 불일치 가능성)'
    elif ctr_up and cvr_up is None:
        return '부분 효과 — 클릭 UP (전환 데이터 부족)'
    elif not ctr_up and cvr_up:
        return '부분 효과 — 클릭 DOWN, 전환 UP (정밀 타겟팅 가능성)'
    else:
        return '재가공 효과 없음 — 원본 훅 복귀 검토'


def analyze_strict_pairs(strict_pairs: pd.DataFrame) -> pd.DataFrame:
    """
    Strict 매칭 쌍 분석
    """
    if len(strict_pairs) == 0:
        return pd.DataFrame()

    result = strict_pairs.copy()

    # CTR 변화율
    result['CTR_변화율'] = ((result['CTR_재가공'] - result['CTR_신규']) / result['CTR_신규'].replace(0, np.nan) * 100).round(1)
    result['CTR_변화'] = result.apply(
        lambda r: f"{r['CTR_신규']:.2f}% -> {r['CTR_재가공']:.2f}% ({'+' if r['CTR_변화율'] > 0 else ''}{r['CTR_변화율']:.1f}%)"
        if pd.notna(r['CTR_변화율']) else 'N/A',
        axis=1
    )

    # CVR 변화율
    result['CVR_변화율'] = ((result['CVR_재가공'] - result['CVR_신규']) / result['CVR_신규'].replace(0, np.nan) * 100).round(1)
    result['CVR_변화'] = result.apply(
        lambda r: f"{r['CVR_신규']:.2f}% -> {r['CVR_재가공']:.2f}% ({'+' if r['CVR_변화율'] > 0 else ''}{r['CVR_변화율']:.1f}%)"
        if pd.notna(r['CVR_변화율']) else 'N/A',
        axis=1
    )

    # CPA 변화율
    result['CPA_변화율'] = ((result['CPA_재가공'] - result['CPA_신규']) / result['CPA_신규'].replace(0, np.nan) * 100).round(1)
    result['CPA_변화'] = result.apply(
        lambda r: f"{r['CPA_신규']:,.0f}원 -> {r['CPA_재가공']:,.0f}원 ({'+' if r['CPA_변화율'] > 0 else ''}{r['CPA_변화율']:.1f}%)"
        if pd.notna(r['CPA_변화율']) and pd.notna(r['CPA_신규']) and pd.notna(r['CPA_재가공']) else 'N/A',
        axis=1
    )

    # 훅 판정
    result['훅판정'] = result.apply(
        lambda r: hook_verdict(r['CTR_신규'], r['CTR_재가공'], r['CVR_신규'], r['CVR_재가공']),
        axis=1
    )

    return result


def analyze_type_comparison(type_comparison: pd.DataFrame) -> pd.DataFrame:
    """
    소재유형별 신규↔재가공 비교 분석
    """
    # Pivot으로 신규/재가공 비교
    pivot_metrics = []

    for 소재유형 in type_comparison['소재유형'].unique():
        type_data = type_comparison[type_comparison['소재유형'] == 소재유형]
        신규_data = type_data[type_data['소재구분'] == '신규']
        재가공_data = type_data[type_data['소재구분'] == '재가공']

        row = {'소재유형': 소재유형}

        if len(신규_data) > 0:
            row['신규_소재수'] = 신규_data['소재수'].values[0]
            row['신규_CTR'] = 신규_data['집계_CTR'].values[0]
            row['신규_CVR'] = 신규_data['집계_CVR'].values[0]
            row['신규_CPA'] = 신규_data['집계_CPA'].values[0]
        else:
            row['신규_소재수'] = 0
            row['신규_CTR'] = np.nan
            row['신규_CVR'] = np.nan
            row['신규_CPA'] = np.nan

        if len(재가공_data) > 0:
            row['재가공_소재수'] = 재가공_data['소재수'].values[0]
            row['재가공_CTR'] = 재가공_data['집계_CTR'].values[0]
            row['재가공_CVR'] = 재가공_data['집계_CVR'].values[0]
            row['재가공_CPA'] = 재가공_data['집계_CPA'].values[0]
        else:
            row['재가공_소재수'] = 0
            row['재가공_CTR'] = np.nan
            row['재가공_CVR'] = np.nan
            row['재가공_CPA'] = np.nan

        # 변화율 계산
        if pd.notna(row['신규_CTR']) and pd.notna(row['재가공_CTR']) and row['신규_CTR'] != 0:
            row['CTR_변화율'] = round((row['재가공_CTR'] - row['신규_CTR']) / row['신규_CTR'] * 100, 1)
        else:
            row['CTR_변화율'] = np.nan

        if pd.notna(row['신규_CVR']) and pd.notna(row['재가공_CVR']) and row['신규_CVR'] != 0:
            row['CVR_변화율'] = round((row['재가공_CVR'] - row['신규_CVR']) / row['신규_CVR'] * 100, 1)
        else:
            row['CVR_변화율'] = np.nan

        if pd.notna(row['신규_CPA']) and pd.notna(row['재가공_CPA']) and row['신규_CPA'] != 0:
            row['CPA_변화율'] = round((row['재가공_CPA'] - row['신규_CPA']) / row['신규_CPA'] * 100, 1)
        else:
            row['CPA_변화율'] = np.nan

        # 훅 판정
        row['훅판정'] = hook_verdict(
            row['신규_CTR'], row['재가공_CTR'],
            row['신규_CVR'], row['재가공_CVR']
        )

        pivot_metrics.append(row)

    return pd.DataFrame(pivot_metrics)


def compare_hooks(creative_df: pd.DataFrame, output_dir: str, lineage_path: str = None) -> dict:
    """
    메인 실행 함수

    Args:
        creative_df: 소재 DataFrame
        output_dir: 출력 디렉토리
        lineage_path: creative_lineage.csv 경로 (optional, 3단계 고도화)
    """
    # 매칭 실행 (lineage + strict)
    all_pairs, type_comparison = match_hook_pairs(creative_df, lineage_path)

    # 모든 쌍 분석
    pairs_analysis = analyze_strict_pairs(all_pairs)

    # 소재유형별 비교 분석
    type_analysis = analyze_type_comparison(type_comparison)

    # 매칭 실패 재가공 소재 목록
    재가공 = creative_df[creative_df['소재구분'] == '재가공']
    if len(all_pairs) > 0:
        if '소재명' in all_pairs.columns:
            matched_names = all_pairs['소재명'].unique()
        elif '재가공소재명' in all_pairs.columns:
            matched_names = all_pairs['재가공소재명'].unique()
        else:
            matched_names = []
        unmatched_재가공 = 재가공[~재가공['소재명'].isin(matched_names)]
    else:
        unmatched_재가공 = 재가공

    # 결과 저장
    os.makedirs(output_dir, exist_ok=True)

    if len(pairs_analysis) > 0:
        pairs_analysis.to_csv(os.path.join(output_dir, "hook_strict_pairs.csv"), index=False, encoding='utf-8-sig')
        pairs_analysis.to_parquet(os.path.join(output_dir, "hook_strict_pairs.parquet"), index=False)
        print(f"[OK] Hook pairs analysis -> {output_dir}/hook_strict_pairs.csv")

    type_analysis.to_csv(os.path.join(output_dir, "hook_type_comparison.csv"), index=False, encoding='utf-8-sig')
    type_analysis.to_parquet(os.path.join(output_dir, "hook_type_comparison.parquet"), index=False)
    print(f"[OK] Type comparison -> {output_dir}/hook_type_comparison.csv")

    if len(unmatched_재가공) > 0:
        unmatched_재가공.to_csv(os.path.join(output_dir, "hook_unmatched.csv"), index=False, encoding='utf-8-sig')
        print(f"[WARNING] Unmatched reworked creatives: {len(unmatched_재가공)} -> {output_dir}/hook_unmatched.csv")

    return {
        'strict_pairs': pairs_analysis,
        'type_comparison': type_analysis,
        'unmatched': unmatched_재가공
    }


if __name__ == "__main__":
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else "output/creative_tier.parquet"
    output_directory = sys.argv[2] if len(sys.argv) > 2 else "output"
    lineage_file = sys.argv[3] if len(sys.argv) > 3 else "input/creative_lineage.csv"

    creative_df = pd.read_parquet(input_file)
    compare_hooks(creative_df, output_directory, lineage_file)
