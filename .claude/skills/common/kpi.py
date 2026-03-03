"""
KPI 계산 함수
전체 및 지점별 KPI 집계
"""
import pandas as pd
from .constants import VALID_BRANCHES


def calc_kpi(df: pd.DataFrame) -> dict:
    """KPI 계산 (CVR 포함)

    Args:
        df: 분석 대상 DataFrame (is_off 컬럼 포함)

    Returns:
        dict: {cost, conv, clicks, cpa, ctr, cvr}

    Note:
        - CPA: int(cost/conv) if conv > 0 else None (표준)
        - CVR: 전환/클릭 기준 (CLAUDE.md 통일)
    """
    df_on = df[~df['is_off']] if 'is_off' in df.columns else df
    cost = df_on['cost'].sum()
    conv = df_on['conversions'].sum()
    clicks = df_on['clicks'].sum()
    impr = df_on['impressions'].sum()

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
        df: 분석 대상 DataFrame (is_off, branch 컬럼 포함)

    Returns:
        dict: {지점명: {cost, conv, clicks, cpa, cvr}}
    """
    df_on = df[~df['is_off']] if 'is_off' in df.columns else df
    result = {}

    for branch in VALID_BRANCHES:
        branch_df = df_on[df_on['branch'] == branch]
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
