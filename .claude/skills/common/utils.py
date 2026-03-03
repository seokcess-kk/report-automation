"""
유틸리티 함수
포맷팅, JSON 직렬화 등
"""
import numpy as np
import pandas as pd


def clean(obj):
    """JSON 직렬화용 클린 함수

    NaN, Inf 값을 None으로 변환, numpy 타입을 Python 기본 타입으로 변환

    Args:
        obj: 변환 대상 객체 (dict, list, 스칼라 등)

    Returns:
        JSON 직렬화 가능한 객체
    """
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean(v) for v in obj]
    if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return None if (np.isnan(obj) or np.isinf(obj)) else round(float(obj), 2)
    if isinstance(obj, pd.Timestamp):
        return obj.strftime('%Y-%m-%d')
    if isinstance(obj, np.ndarray):
        return [clean(v) for v in obj.tolist()]
    return obj


def fmt(n, unit: str = '') -> str:
    """숫자 포맷 (천 단위 콤마)

    Args:
        n: 숫자 또는 None
        unit: 단위 문자열 (예: '원', '건')

    Returns:
        포맷된 문자열 또는 '-'
    """
    if n is None:
        return '-'
    return f"{int(n):,}{unit}"


def fmt_man(n) -> str:
    """만원 단위 포맷 (예: 1,234,567 → 123만)

    Args:
        n: 숫자 또는 None

    Returns:
        포맷된 문자열 또는 '-'
    """
    if n is None:
        return '-'
    man = n / 10000
    if man >= 100:
        return f"{int(man):,}만"
    elif man >= 10:
        return f"{man:.0f}만"
    else:
        return f"{man:.1f}만"


def fmt_pct(n) -> str:
    """퍼센트 포맷

    Args:
        n: 숫자 또는 None

    Returns:
        포맷된 문자열 (예: '5.23%') 또는 '-'
    """
    if n is None:
        return '-'
    return f"{n:.2f}%"
