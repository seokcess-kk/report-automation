"""
로깅 유틸리티
프로젝트 전체에서 일관된 로깅 포맷 제공
"""
import logging
import sys
from pathlib import Path


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """로거 설정

    Args:
        name: 로거 이름 (보통 스크립트 이름)
        level: 로깅 레벨 (기본: INFO)

    Returns:
        설정된 Logger 객체
    """
    logger = logging.getLogger(name)

    # 이미 핸들러가 있으면 중복 추가 방지
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '[%(levelname)s] %(message)s'
    ))
    logger.addHandler(handler)
    logger.setLevel(level)

    return logger


class DataFileError(Exception):
    """데이터 파일 관련 에러"""
    pass


class ParseError(Exception):
    """파싱 관련 에러"""
    pass


class ReportGenerationError(Exception):
    """리포트 생성 관련 에러"""
    pass


def validate_input_file(file_path: str, required_ext: list = None) -> Path:
    """입력 파일 검증

    Args:
        file_path: 파일 경로
        required_ext: 허용된 확장자 리스트 (예: ['.csv', '.parquet'])

    Returns:
        검증된 Path 객체

    Raises:
        DataFileError: 파일이 없거나 확장자가 맞지 않을 때
    """
    path = Path(file_path)

    if not path.exists():
        raise DataFileError(
            f"입력 파일 없음: {file_path}\n"
            f"  → 파일 경로를 확인하세요."
        )

    if required_ext and path.suffix.lower() not in required_ext:
        raise DataFileError(
            f"지원하지 않는 파일 형식: {path.suffix}\n"
            f"  → 허용된 형식: {', '.join(required_ext)}"
        )

    return path


def validate_output_dir(dir_path: str, create: bool = True) -> Path:
    """출력 디렉토리 검증

    Args:
        dir_path: 디렉토리 경로
        create: 없으면 생성 여부 (기본: True)

    Returns:
        검증된 Path 객체

    Raises:
        DataFileError: 디렉토리 생성 실패 시
    """
    path = Path(dir_path)

    if not path.exists():
        if create:
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise DataFileError(
                    f"출력 디렉토리 생성 실패: {dir_path}\n"
                    f"  → 에러: {e}"
                )
        else:
            raise DataFileError(f"출력 디렉토리 없음: {dir_path}")

    return path
