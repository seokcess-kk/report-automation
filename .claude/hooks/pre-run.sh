#!/bin/bash
# TikTok Ad Analysis - Pre-run Hook
# 입력 파일 감지 및 검증

INPUT_DIR="input"
REQUIRED_FILE="tiktok_raw.csv"

echo "[Pre-run Hook] Checking input files..."

# 필수 파일 존재 확인
if [ ! -f "$INPUT_DIR/$REQUIRED_FILE" ]; then
    echo "[ERROR] Required file not found: $INPUT_DIR/$REQUIRED_FILE"
    exit 1
fi

# 파일 크기 확인 (빈 파일 방지)
FILE_SIZE=$(stat -f%z "$INPUT_DIR/$REQUIRED_FILE" 2>/dev/null || stat --printf="%s" "$INPUT_DIR/$REQUIRED_FILE" 2>/dev/null)
if [ "$FILE_SIZE" -lt 100 ]; then
    echo "[ERROR] Input file too small: $FILE_SIZE bytes"
    exit 1
fi

# Optional 파일 확인
if [ -f "$INPUT_DIR/creative_lineage.csv" ]; then
    echo "[INFO] creative_lineage.csv detected - lineage matching enabled"
fi

if [ -f "$INPUT_DIR/db_by_branch.csv" ]; then
    echo "[INFO] db_by_branch.csv detected - funnel analysis enabled"
fi

if [ -f "$INPUT_DIR/target_cpa.csv" ]; then
    echo "[INFO] target_cpa.csv detected - custom CPA thresholds enabled"
fi

echo "[Pre-run Hook] Input validation passed"
exit 0
