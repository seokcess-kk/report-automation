"""
TikTok 광고명 파싱 + 메타데이터 추출
설계서 섹션 1-2 기준

파싱 패턴:
  ON:  (신/재)_지점_소재유형_소재명_날짜코드
  OFF: (신/재)_지점_소재유형_소재명_날짜코드_off

추출 항목:
  - 소재구분: (신) = 신규, (재) = 재가공
  - 지점: 서울, 부평, 수원, 대구, 창원, 천안, 일산
  - 소재유형: 인플방문후기, 진료셀프캠, 의료진정보
  - 소재명: 핵심 창의물 이름
  - 날짜코드: 5~6자리
  - is_off: 광고명 끝이 '_off'이면 True
  - 매칭키: 소재유형_소재명 (훅 쌍 매칭용)
"""
import pandas as pd
import re
import os


# 유효값 목록
VALID_BRANCHES = ['부평', '서울', '수원', '대구', '창원', '천안', '일산']
VALID_AD_TYPES = ['인플방문후기', '진료셀프캠', '의료진정보']


def parse_ad_name(name: str) -> dict:
    """
    광고명을 파싱하여 메타데이터 추출

    Returns:
        dict with keys: 소재구분, 지점, 소재유형, 소재명, 날짜코드, is_off, 매칭키,
                       parse_status, parse_issue
    """
    result = {
        '소재구분': None,
        '지점': None,
        '소재유형': None,
        '소재명': None,
        '날짜코드': None,
        'is_off': False,
        '매칭키': None,
        'parse_status': 'FAIL',
        'parse_issue': None
    }

    if not name or pd.isna(name):
        result['parse_issue'] = 'EMPTY_NAME'
        return result

    name = str(name).strip()

    # 1. _off 감지 후 제거
    result['is_off'] = name.lower().endswith('_off')
    clean_name = name[:-4] if result['is_off'] else name  # '_off' 4글자 제거

    # 2. 언더스코어로 분리
    parts = clean_name.split('_')

    if len(parts) < 4:
        result['parse_issue'] = 'TOO_FEW_PARTS'
        return result

    # 3. 소재구분 파싱 (첫 번째 파트)
    first_part = parts[0]
    if '신' in first_part:
        result['소재구분'] = '신규'
    elif '재' in first_part:
        result['소재구분'] = '재가공'
    else:
        result['parse_issue'] = 'UNKNOWN_CREATIVE_TYPE'
        return result

    # 4. 지점 파싱 (두 번째 파트)
    branch = parts[1]
    if branch not in VALID_BRANCHES:
        result['parse_issue'] = 'UNKNOWN_BRANCH'
        return result
    result['지점'] = branch

    # 5. 소재유형 파싱 (세 번째 파트)
    ad_type = parts[2]
    if ad_type not in VALID_AD_TYPES:
        result['parse_issue'] = 'UNKNOWN_TYPE'
        return result
    result['소재유형'] = ad_type

    # 6. 날짜코드와 소재명 파싱
    # 마지막 파트가 5~6자리 숫자인지 확인
    last_part = parts[-1]
    date_pattern = re.compile(r'^\d{5,6}$')

    if date_pattern.match(last_part):
        result['날짜코드'] = last_part
        # 소재명: 4번째 파트부터 마지막 전까지
        creative_parts = parts[3:-1]
    else:
        # 날짜코드가 없는 경우
        result['날짜코드'] = None
        creative_parts = parts[3:]

    if not creative_parts:
        result['parse_issue'] = 'SHORT_CREATIVE_NAME'
        return result

    result['소재명'] = '_'.join(creative_parts)

    # 소재명이 너무 짧으면 경고
    if len(result['소재명']) < 2:
        result['parse_issue'] = 'SHORT_CREATIVE_NAME'
        return result

    # 7. 매칭키 생성
    result['매칭키'] = f"{result['소재유형']}_{result['소재명']}"

    # 8. 파싱 성공
    result['parse_status'] = 'OK'

    return result


def parse_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrame의 모든 광고명을 파싱하여 메타데이터 컬럼 추가
    """
    # 광고명 컬럼 확인
    ad_name_col = 'ad_name' if 'ad_name' in df.columns else '광고 이름'

    if ad_name_col not in df.columns:
        raise ValueError(f"광고명 컬럼을 찾을 수 없습니다. 사용 가능 컬럼: {df.columns.tolist()}")

    # 파싱 실행
    parsed_data = df[ad_name_col].apply(parse_ad_name)
    parsed_df = pd.DataFrame(parsed_data.tolist())

    # 원본 DataFrame에 파싱 결과 병합
    result_df = pd.concat([df.reset_index(drop=True), parsed_df], axis=1)

    # 파싱 통계 출력
    total = len(result_df)
    ok_count = (result_df['parse_status'] == 'OK').sum()
    fail_count = (result_df['parse_status'] == 'FAIL').sum()

    print(f"[파싱 결과] 전체: {total}행 | 성공: {ok_count}행 | 실패: {fail_count}행")

    if fail_count > 0:
        issues = result_df[result_df['parse_status'] == 'FAIL']['parse_issue'].value_counts()
        print(f"[파싱 실패 원인]\n{issues.to_string()}")

    return result_df


def save_parse_failures(df: pd.DataFrame, output_path: str):
    """
    파싱 실패 소재를 별도 파일로 저장
    """
    failures = df[df['parse_status'] == 'FAIL'].copy()
    if len(failures) > 0:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        failures.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"[WARNING] 파싱 실패 {len(failures)}건 → {output_path}")
    return failures


def main(input_path: str, output_path: str, failures_path: str):
    """
    메인 실행 함수
    """
    # 입력 파일 로드
    if input_path.endswith('.parquet'):
        df = pd.read_parquet(input_path)
    else:
        df = pd.read_csv(input_path, encoding='utf-8-sig')

    print(f"[입력] {len(df)}행 로드됨")

    # 파싱 실행
    parsed_df = parse_dataframe(df)

    # 파싱 실패 저장
    save_parse_failures(parsed_df, failures_path)

    # 결과 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    parsed_df.to_parquet(output_path, index=False)
    print(f"[OK] 파싱 완료 → {output_path}")

    return parsed_df


if __name__ == "__main__":
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else "output/normalized.parquet"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "output/parsed.parquet"
    failures_file = sys.argv[3] if len(sys.argv) > 3 else "logs/parse_failures.csv"
    main(input_file, output_file, failures_file)
