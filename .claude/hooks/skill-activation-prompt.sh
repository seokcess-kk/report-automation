#!/bin/bash
# UserPromptSubmit 훅 — 프롬프트에서 관련 스킬 자동 감지 후 제안

PROMPT="$1"

# creative-analyzer 스킬 트리거
if echo "$PROMPT" | grep -qiE "TIER|소재|CTR|CVR|CPA|훅|hook|creative"; then
  echo "📋 [SKILL 활성화] creative-analyzer 스킬을 참조하세요"
  echo "   경로: .claude/skills/creative-analyzer/"
fi

# report-generator 스킬 트리거
if echo "$PROMPT" | grep -qiE "Excel|PDF|차트|리포트|report|chart|한글|폰트"; then
  echo "📋 [SKILL 활성화] report-generator 스킬을 참조하세요"
  echo "   경로: .claude/skills/report-generator/"
fi

# daily-monitor 스킬 트리거
if echo "$PROMPT" | grep -qiE "데일리|daily|스냅샷|전일|모니터링"; then
  echo "📋 [SKILL 활성화] daily-monitor 스킬을 참조하세요"
  echo "   경로: .claude/skills/daily-monitor/"
fi

# data-integrity guardrail 트리거
if echo "$PROMPT" | grep -qiE "수치.*입력|하드코딩|직접.*계산"; then
  echo "🚫 [GUARDRAIL] data-integrity-guardrail 위반 가능성 감지"
  echo "   _calc 재계산값 컬럼만 사용, DataFrame에서 직접 읽어야 합니다"
fi
