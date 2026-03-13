"""
KPI 계산 함수
전체 및 지점별 KPI 집계
"""
import pandas as pd
from .constants import VALID_BRANCHES


def calc_kpi(df: pd.DataFrame) -> dict:
    """KPI 계산 (CVR 포함)

    Args:
        df: 분석 대상 DataFrame

    Returns:
        dict: {cost, conv, clicks, cpa, ctr, cvr}

    Note:
        - CPA: int(cost/conv) if conv > 0 else None (표준)
        - CVR: 전환/클릭 기준 (CLAUDE.md 통일)
        - OFF 소재 포함: KPI 계산에는 OFF 소재도 포함 (실제 집행 비용이므로)
    """
    cost = df['cost'].sum()
    conv = df['conversions'].sum()
    clicks = df['clicks'].sum()
    impr = df['impressions'].sum()

    return {
        'cost': int(cost),
        'conv': int(conv),
        'clicks': int(clicks),
        'cpa': int(cost / conv) if conv > 0 else None,
        'ctr': round(clicks / impr * 100, 2) if impr > 0 else 0,
        'cvr': round(conv / clicks * 100, 2) if clicks > 0 else 0,
    }


def calc_branch_kpi(df: pd.DataFrame) -> dict:
    """지점별 KPI 계산 (CVR 포함)

    Args:
        df: 분석 대상 DataFrame (branch 컬럼 포함)

    Returns:
        dict: {지점명: {cost, conv, clicks, cpa, cvr}}

    Note:
        - OFF 소재 포함: KPI 계산에는 OFF 소재도 포함 (실제 집행 비용이므로)
    """
    result = {}

    for branch in VALID_BRANCHES:
        branch_df = df[df['branch'] == branch]
        if len(branch_df) == 0:
            continue

        cost = branch_df['cost'].sum()
        conv = branch_df['conversions'].sum()
        clicks = branch_df['clicks'].sum()

        result[branch] = {
            'cost': int(cost),
            'conv': int(conv),
            'clicks': int(clicks),
            'cpa': int(cost / conv) if conv > 0 else None,
            'cvr': round(conv / clicks * 100, 2) if clicks > 0 else 0,
        }

    return result
