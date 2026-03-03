"""
공용 모듈 패키지
TikTok 광고 분석 파이프라인 전역에서 사용되는 상수, 함수, 유틸리티
"""
from .constants import (
    VALID_BRANCHES,
    VALID_AD_TYPES,
    MONTHLY_BUDGET,
    MONTHLY_TARGET_CONV,
    TOTAL_MONTHLY_BUDGET,
)
from .parsers import (
    strip_date_code,
    load_target_cpa,
    parse_branch,
)
from .kpi import (
    calc_kpi,
    calc_branch_kpi,
)
from .utils import (
    clean,
    fmt,
    fmt_man,
    fmt_pct,
)
from .logger import (
    setup_logger,
    DataFileError,
    ParseError,
    ReportGenerationError,
    validate_input_file,
    validate_output_dir,
)

__all__ = [
    # constants
    'VALID_BRANCHES',
    'VALID_AD_TYPES',
    'MONTHLY_BUDGET',
    'MONTHLY_TARGET_CONV',
    'TOTAL_MONTHLY_BUDGET',
    # parsers
    'strip_date_code',
    'load_target_cpa',
    'parse_branch',
    # kpi
    'calc_kpi',
    'calc_branch_kpi',
    # utils
    'clean',
    'fmt',
    'fmt_man',
    'fmt_pct',
    # logger
    'setup_logger',
    'DataFileError',
    'ParseError',
    'ReportGenerationError',
    'validate_input_file',
    'validate_output_dir',
]
