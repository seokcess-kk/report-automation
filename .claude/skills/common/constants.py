"""
전역 상수 정의
모든 리포트 스크립트에서 공유하는 상수값
"""

# 지점 순서 (고정 - 대전·부산 추가)
VALID_BRANCHES = ['서울', '부평', '수원', '일산', '대구', '창원', '천안', '대전', '부산']

# 유효 광고 유형
VALID_AD_TYPES = ['인플방문후기', '진료셀프캠', '의료진정보', '리얼모델후기', '진료QnA', '방문후기']

# 지점별 월 예산
MONTHLY_BUDGET = {
    '서울': 2_000_000,
    '부평': 2_000_000,
    '수원': 2_000_000,
    '일산': 2_000_000,
    '대구': 2_000_000,
    '창원': 2_000_000,
    '천안': 2_000_000,
    '대전': 2_000_000,
    '부산': 2_000_000,
}

# 지점별 월 목표 전환수
MONTHLY_TARGET_CONV_BY_BRANCH = {
    '서울': 147, '부평': 95, '수원': 84, '일산': 136,
    '대구': 109, '창원': 76, '천안': 91, '대전': 70, '부산': 83,
}

# 지점별 월 목표 노출수
MONTHLY_TARGET_IMP_BY_BRANCH = {
    '서울': 181_818, '부평': 181_818, '수원': 200_000, '일산': 200_000,
    '대구': 181_818, '창원': 181_818, '천안': 200_000, '대전': 166_667, '부산': 181_818,
}

# 지점별 월 목표 클릭수
MONTHLY_TARGET_CLICK_BY_BRANCH = {
    '서울': 1_636, '부평': 1_273, '수원': 1_200, '일산': 1_600,
    '대구': 1_364, '창원': 1_091, '천안': 1_300, '대전': 1_000, '부산': 1_182,
}

# 월 목표 합계 (지점별 합산)
MONTHLY_TARGET_CONV = sum(MONTHLY_TARGET_CONV_BY_BRANCH.values())
MONTHLY_TARGET_IMP = sum(MONTHLY_TARGET_IMP_BY_BRANCH.values())
MONTHLY_TARGET_CLICK = sum(MONTHLY_TARGET_CLICK_BY_BRANCH.values())

# 총 월 예산
TOTAL_MONTHLY_BUDGET = sum(MONTHLY_BUDGET.values())
