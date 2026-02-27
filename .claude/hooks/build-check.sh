#!/bin/bash
# Stop 훅 — 작업 완료 시 자동 QA 검증

echo "🔍 자동 QA 검증 시작..."

# 프로젝트 루트 디렉토리
PROJECT_DIR="$(dirname "$(dirname "$(dirname "$0")")")"

# 가장 최근 output 폴더 탐색
LATEST=$(ls -td "$PROJECT_DIR/output/20"*/ 2>/dev/null | head -1)

if [ -z "$LATEST" ]; then
  echo "⚠️ output 폴더 없음 — QA 스킵"
  exit 0
fi

echo "📁 검증 대상: $LATEST"

# qa_report.json 확인
QA_REPORT="$LATEST/qa_report.json"
if [ -f "$QA_REPORT" ]; then
  ALL_PASS=$(python3 -c "import json; d=json.load(open('$QA_REPORT')); print(d.get('all_pass','false'))" 2>/dev/null)
  if [ "$ALL_PASS" = "True" ]; then
    echo "✅ QA 통과: $QA_REPORT"
  else
    echo "❌ QA 실패: $QA_REPORT — qa-agent 실행 권장"
    python3 -c "
import json
d=json.load(open('$QA_REPORT'))
for f in d.get('failures',[]):
    print('  ·', f)
" 2>/dev/null
  fi
else
  echo "⚠️ qa_report.json 없음"
fi

# 리포트 파일 존재 확인
echo ""
echo "📄 리포트 파일 확인:"
for ext in xlsx pdf html; do
  if ls "$LATEST"*.$ext 2>/dev/null | head -1 | grep -q .; then
    echo "  ✅ $ext 파일 존재"
  else
    echo "  ⚠️ $ext 파일 없음"
  fi
done

# improvement_suggestions.md 확인
if [ -f "$LATEST/improvement_suggestions.md" ]; then
  echo "  ✅ improvement_suggestions.md 존재"
else
  echo "  ⚠️ improvement_suggestions.md 없음"
fi

echo ""
echo "🔍 QA 검증 완료"
