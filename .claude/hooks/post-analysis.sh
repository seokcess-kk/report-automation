#!/bin/bash
# TikTok Ad Analysis - Post-analysis Hook
# 분석 완료 후 처리

OUTPUT_DIR="output"
TODAY=$(date +%Y%m%d)
REPORT_DIR="$OUTPUT_DIR/$TODAY"

echo "[Post-analysis Hook] Checking output files..."

# 필수 출력 파일 확인
REQUIRED_FILES=(
    "creative_tier.parquet"
    "parsed.parquet"
    "normalized.parquet"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$OUTPUT_DIR/$file" ]; then
        echo "[WARNING] Expected file not found: $OUTPUT_DIR/$file"
    fi
done

# 리포트 파일 확인
if [ -f "$REPORT_DIR/tiktok_analysis_$TODAY.xlsx" ]; then
    echo "[OK] Excel report generated"
fi

if [ -f "$REPORT_DIR/tiktok_summary_$TODAY.pdf" ]; then
    echo "[OK] PDF report generated"
fi

if [ -f "$REPORT_DIR/improvement_suggestions.md" ]; then
    echo "[OK] Improvement suggestions generated"

    # 인사이트 요약 출력
    echo ""
    echo "=== Insight Summary ==="
    head -15 "$REPORT_DIR/improvement_suggestions.md"
    echo "..."
fi

# 이상치 감지 결과 확인
if [ -f "$OUTPUT_DIR/anomalies.csv" ]; then
    ANOMALY_COUNT=$(wc -l < "$OUTPUT_DIR/anomalies.csv")
    echo "[INFO] Anomalies detected: $((ANOMALY_COUNT - 1)) items"
fi

echo "[Post-analysis Hook] Completed"
exit 0
