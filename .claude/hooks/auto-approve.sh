#!/bin/bash
# TikTok Ad Analysis - Auto-approve Hook
# 자동 승인 로직 (CI/CD 환경용)

# 환경 변수 확인
AUTO_APPROVE=${AUTO_APPROVE:-false}

if [ "$AUTO_APPROVE" = "true" ]; then
    echo "[Auto-approve] Automatic approval enabled"

    # QA 결과 확인
    QA_PASS_RATE=${QA_PASS_RATE:-0}

    if [ "$QA_PASS_RATE" -ge 90 ]; then
        echo "[Auto-approve] QA pass rate: ${QA_PASS_RATE}% - APPROVED"
        exit 0
    else
        echo "[Auto-approve] QA pass rate: ${QA_PASS_RATE}% - REJECTED (minimum 90%)"
        exit 1
    fi
else
    echo "[Auto-approve] Manual approval required"
    echo "Set AUTO_APPROVE=true to enable automatic approval"
    exit 0
fi
