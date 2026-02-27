# 훅 에이전트

> 역할: 신규 vs 재가공 훅 효과 비교

## 전제 조건
- Phase 2 분석 에이전트 완료: `output/creative_tier.parquet` 존재

## 입력 파일
- `output/creative_tier.parquet` - 소재구분 컬럼 포함된 TIER 데이터
- `input/creative_lineage.csv` (선택) - 명시적 원본-재가공 매핑

## 실행 명령
```bash
python .claude/skills/creative-analyzer/scripts/hook_comparison.py output/creative_tier.parquet output input/creative_lineage.csv
```

## 출력 파일
- `output/hook_strict_pairs.parquet` - 정확 매칭 쌍 (소재유형 + 소재명 완전 일치)
- `output/hook_strict_pairs.csv` - CSV 형식
- `output/hook_type_comparison.parquet` - 소재유형별 집계 비교
- `output/hook_type_comparison.csv` - CSV 형식
- `output/hook_unmatched.csv` - 매칭 안 된 재가공 소재 목록

## 매칭 전략 (3단계)

### A. Lineage 매칭 (가장 정확)
- `creative_lineage.csv` 사용하여 명시적 매핑
- 컬럼: creative_group_id, 원본소재명, 재가공소재명, 변경요소

### B. 정확 매칭 (Strict)
- 기준: 소재유형 + 소재명 완전 일치
- 다른 지점의 동일 소재는 같은 것으로 간주

### C. 소재유형 집계 (대체)
- 비교: "인플방문후기 신규" vs "인플방문후기 재가공" 집계 단위
- 정확 매칭이 0건일 때 사용

## 훅 판정 로직
```python
def hook_verdict(orig_ctr, re_ctr, orig_cvr, re_cvr):
    ctr_up = re_ctr > orig_ctr
    cvr_up = re_cvr > orig_cvr

    if ctr_up and cvr_up:
        return '재가공 유효 — 클릭·전환 모두 개선'
    elif ctr_up and not cvr_up:
        return '부분 효과 — 클릭↑ 전환↓ (랜딩 불일치 가능성)'
    elif not ctr_up and cvr_up:
        return '부분 효과 — 클릭↓ 전환↑ (정밀 타겟팅 가능성)'
    else:
        return '재가공 효과 없음 — 원본 훅 복귀 검토'
```

## 핵심 규칙
- 정확 매칭 0건은 오류가 아님 → 자동으로 소재유형 집계로 대체
- `creative_lineage.csv` 없으면 → Lineage 매칭 건너뛰고 자동 매칭만 사용
- 항상 `hook_unmatched.csv` 출력 (매칭 안 된 재가공 소재)

## 검증 체크리스트
- [ ] strict_pairs 또는 type_comparison 중 하나 이상 존재
- [ ] 재가공 소재 매칭 안 된 목록 생성됨

## 훅 판정 방향 주의 (버그 방지)
- CTR +45.3% → "부분 효과" 또는 "재가공 유효" (올바름)
- CTR +45.3% → "효과 없음" (잘못됨 - 역전 버그)
