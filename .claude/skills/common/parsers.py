"""
파싱 함수
소재명 파싱, 목표 CPA 로드, 지점 추출 등
"""
import pandas as pd
import os
import re
from .constants import VALID_BRANCHES


def strip_date_code(name: str) -> str:
    """소재명에서 날짜코드 제거 (_YYMM, _YYMMDD 등 4~6자리)"""
    if name is None or (isinstance(name, float) and pd.isna(name)) or not name:
        return ''
    return re.sub(r'_\d{4,6}$', '', str(name))


def load_target_cpa(target_cpa_path: str = "input/target_cpa.csv") -> dict:
    """목표 CPA 로드

    Returns:
        dict: {지점명: 목표CPA} 또는 빈 dict (파일 없을 시)
    """
    if os.path.exists(target_cpa_path):
        target_df = pd.read_csv(target_cpa_path, encoding='utf-8-sig')
        return dict(zip(target_df['지점'], target_df['목표CPA']))
    return {}


def load_ad_name_corrections(corrections_path: str = "input/ad_name_corrections.csv") -> dict:
    """광고명 정정 사전 로드.

    클라이언트가 검증해준 정답 이름을 ad_id 기준으로 매핑.
    잘못 설정된 광고명(_off 토글, 오타, 재활용 흔적)을 통일하여 매칭키 집계 정확도를 보장.

    CSV 컬럼: ad_id, correct_canonical_name, (선택) note

    Returns:
        dict: {ad_id: correct_canonical_name} — _off 접미사 제외한 정답 이름
    """
    if not os.path.exists(corrections_path):
        return {}
    df = pd.read_csv(corrections_path, encoding='utf-8-sig', dtype={'ad_id': str})
    return dict(zip(df['ad_id'], df['correct_canonical_name']))


def apply_ad_name_corrections(df: pd.DataFrame, corrections: dict) -> tuple[pd.DataFrame, int]:
    """ad_name 컬럼에 정정 사전 적용.

    - 해당 ad_id 의 모든 행을 정답 이름으로 교체
    - 원본의 _off 접미사는 보존 (ON/OFF 상태 정보)
    - 원본 이름은 ad_name_original 컬럼으로 보존

    Returns:
        (정정 적용된 df, 정정 적용 행수)
    """
    if not corrections:
        return df, 0
    if 'ad_name' not in df.columns:
        return df, 0

    df = df.copy()
    df['ad_id'] = df['ad_id'].astype(str)
    df['ad_name_original'] = df['ad_name']
    applied = 0
    for ad_id, correct_canon in corrections.items():
        mask = df['ad_id'] == ad_id
        if not mask.any():
            continue
        # 각 행의 _off 접미사 보존
        new_names = df.loc[mask, 'ad_name'].astype(str).apply(
            lambda orig: correct_canon + '_off' if orig.lower().endswith('_off') else correct_canon
        )
        df.loc[mask, 'ad_name'] = new_names
        applied += int(mask.sum())
    return df, applied


def parse_branch(name: str) -> str | None:
    """광고명에서 지점 추출 (위치 기반 우선)

    광고명 구조: (재)_지점_소재유형_... 또는 지점_소재유형_...
    두 번째 '_' 구분자 위치에서 지점을 먼저 찾고, 없으면 전체 매칭 fallback.

    Args:
        name: 광고명 문자열

    Returns:
        지점명 또는 None
    """
    if pd.isna(name):
        return None
    name = str(name)
    # 위치 기반: '_' 구분자에서 두 번째 토큰 우선 확인
    parts = name.split('_')
    for part in parts[:3]:
        for b in VALID_BRANCHES:
            if part == b:
                return b
    # fallback: 전체 문자열에서 매칭
    for b in VALID_BRANCHES:
        if b in name:
            return b
    return None
