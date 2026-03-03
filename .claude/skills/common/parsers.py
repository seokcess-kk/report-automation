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
    if not name or pd.isna(name):
        return str(name) if name else ''
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


def parse_branch(name: str) -> str | None:
    """광고명에서 지점 추출

    Args:
        name: 광고명 문자열

    Returns:
        지점명 또는 None
    """
    if pd.isna(name):
        return None
    name = str(name)
    for b in VALID_BRANCHES:
        if b in name:
            return b
    return None
