#!/usr/bin/env python3
"""
TikTok 광고 분석 파이프라인 오케스트레이터
Phase 0~5 순차 실행

사용법:
    python run_analysis.py                       # 기존 CSV로 분석
    python run_analysis.py input/tiktok_raw.csv  # 특정 CSV 지정
    python run_analysis.py --collect             # API로 수집 후 분석
    python run_analysis.py --collect --days 30
    python run_analysis.py --collect --include-age
"""
import argparse
import os
import sys
import time
from datetime import datetime

# 프로젝트 루트 설정
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)

# 스킬 스크립트 경로
SKILLS_DIR = os.path.join(PROJECT_ROOT, ".claude", "skills")

# 출력 디렉토리 (데이터는 output/data/YYYYMMDD/)
TODAY = datetime.now().strftime("%Y%m%d")
DATA_DIR = os.path.join(PROJECT_ROOT, "output", "data", TODAY)
MONTHLY_DIR = os.path.join(PROJECT_ROOT, "output", "monthly")

# 하위 호환성을 위해 OUTPUT_DIR도 유지 (DATA_DIR과 동일)
OUTPUT_DIR = DATA_DIR


def print_phase(phase_num: int, phase_name: str, status: str = "START"):
    """Phase 상태 출력"""
    icons = {"START": "...", "OK": "[OK]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}
    icon = icons.get(status, "")
    print(f"\n{'='*60}")
    print(f"{icon} Phase {phase_num}: {phase_name} [{status}]")
    print(f"{'='*60}")


def run_collect(days: int, include_age: bool, include_hour: bool = False, start: str = None, end: str = None):
    """Phase -1 (선택) - TikTok API로 raw CSV 수집"""
    print_phase(-1, "API 수집")

    from importlib.util import spec_from_file_location, module_from_spec

    script_path = os.path.join(SKILLS_DIR, "tiktok-api", "scripts", "fetch_tiktok_raw.py")
    if not os.path.exists(script_path):
        print_phase(-1, "API 수집", "FAIL")
        raise FileNotFoundError(f"{script_path} 없음 — tiktok-api 스킬 확인")

    spec = spec_from_file_location("fetch_tiktok_raw", script_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    argv_backup = sys.argv[:]
    try:
        sys.argv = ['fetch_tiktok_raw.py', '--days', str(days)]
        if start:
            sys.argv += ['--start', start]
        if end:
            sys.argv += ['--end', end]
        if include_age:
            sys.argv += ['--include-age']
        if include_hour:
            sys.argv += ['--include-hour']
        module.main()
    finally:
        sys.argv = argv_backup

    print_phase(-1, "API 수집", "OK")


def run_phase_0(input_csv: str) -> str:
    """Phase 0 - 원본 정규화 (main + 나이대 CSV 있으면 함께 정규화)"""
    print_phase(0, "원본 정규화")

    from importlib.util import spec_from_file_location, module_from_spec

    script_path = os.path.join(SKILLS_DIR, "tiktok-normalizer", "scripts", "normalize_tiktok_raw.py")
    spec = spec_from_file_location("normalize", script_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "normalized.parquet")
    module.normalize(input_csv, output_path)

    # 나이대 CSV 있으면 함께 정규화
    by_age_csv = os.path.join(PROJECT_ROOT, "input", "tiktok_raw_by_age.csv")
    if os.path.exists(by_age_csv):
        by_age_out = os.path.join(OUTPUT_DIR, "normalized_by_age.parquet")
        module.normalize(by_age_csv, by_age_out)
        print(f"[OK] 나이대 정규화: {by_age_out}")

    # 시간대 CSV 있으면 함께 정규화
    by_hour_csv = os.path.join(PROJECT_ROOT, "input", "tiktok_raw_by_hour.csv")
    if os.path.exists(by_hour_csv):
        by_hour_out = os.path.join(OUTPUT_DIR, "normalized_by_hour.parquet")
        module.normalize(by_hour_csv, by_hour_out)
        print(f"[OK] 시간대 정규화: {by_hour_out}")

    print_phase(0, "원본 정규화", "OK")
    return output_path


def run_phase_1(normalized_path: str) -> str:
    """Phase 1 - 데이터 준비 (광고명 파싱)"""
    print_phase(1, "데이터 준비 (파싱)")

    from importlib.util import spec_from_file_location, module_from_spec

    script_path = os.path.join(SKILLS_DIR, "tiktok-parser", "scripts", "parse_tiktok.py")
    spec = spec_from_file_location("parse", script_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    output_path = os.path.join(OUTPUT_DIR, "parsed.parquet")
    failures_path = os.path.join(PROJECT_ROOT, "logs", "parse_failures.csv")

    os.makedirs(os.path.dirname(failures_path), exist_ok=True)

    module.main(normalized_path, output_path, failures_path)

    print_phase(1, "데이터 준비 (파싱)", "OK")
    return output_path


def run_phase_2(parsed_path: str) -> dict:
    """Phase 2 - 병렬 분석 (소재 평가 + 훅 비교)"""
    print_phase(2, "병렬 분석")

    from importlib.util import spec_from_file_location, module_from_spec
    import pandas as pd

    # 2-A: 소재 평가 (score_creatives)
    print("\n[2-A] 소재 평가 + TIER 분류...")
    script_path = os.path.join(SKILLS_DIR, "creative-analyzer", "scripts", "score_creatives.py")
    spec = spec_from_file_location("score", script_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    target_cpa_path = os.path.join(PROJECT_ROOT, "input", "target_cpa.csv")
    age_input_path = os.path.join(OUTPUT_DIR, "normalized_by_age.parquet")
    if not os.path.exists(age_input_path):
        age_input_path = None
    result = module.score_creatives(parsed_path, OUTPUT_DIR, target_cpa_path, age_input_path=age_input_path)

    # 2-B: 훅 비교 (hook_comparison)
    print("\n[2-B] 훅 비교 분석...")
    script_path = os.path.join(SKILLS_DIR, "creative-analyzer", "scripts", "hook_comparison.py")
    spec = spec_from_file_location("hook", script_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    creative_df = result['creative_tier']
    lineage_path = os.path.join(PROJECT_ROOT, "input", "creative_lineage.csv")
    module.compare_hooks(creative_df, OUTPUT_DIR, lineage_path)

    print_phase(2, "병렬 분석", "OK")
    return result


def run_phase_3():
    """Phase 3 - 인사이트 생성"""
    print_phase(3, "인사이트 생성")

    # 인사이트 생성 스크립트가 있으면 실행
    script_path = os.path.join(SKILLS_DIR, "insight-writer", "scripts", "generate_insights.py")

    if os.path.exists(script_path):
        from importlib.util import spec_from_file_location, module_from_spec
        import pandas as pd

        spec = spec_from_file_location("insight", script_path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        creative_tier_path = os.path.join(OUTPUT_DIR, "creative_tier.parquet")
        if os.path.exists(creative_tier_path):
            module.main(OUTPUT_DIR, OUTPUT_DIR)

        print_phase(3, "인사이트 생성", "OK")
    else:
        print_phase(3, "인사이트 생성", "SKIP")
        print("  → generate_insights.py 없음")


def run_phase_3_5():
    """Phase 3.5 - 세그먼트 분석 + 트래커 데이터 + 액션 제안"""
    print_phase(3.5, "세그먼트 분석 + 트래커 + 액션 제안")

    from importlib.util import spec_from_file_location, module_from_spec

    # 세그먼트 분석 (요일/소재유형/시간대)
    seg_script = os.path.join(SKILLS_DIR, "creative-analyzer", "scripts", "analyze_segments.py")
    if os.path.exists(seg_script):
        spec = spec_from_file_location("analyze_segments", seg_script)
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.main(DATA_DIR)

    # branch_pace
    pace_script = os.path.join(SKILLS_DIR, "action-advisor", "scripts", "build_branch_pace.py")
    if os.path.exists(pace_script):
        spec = spec_from_file_location("build_branch_pace", pace_script)
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)
        pace = mod.build_pace(DATA_DIR)
        import json as _json
        with open(os.path.join(DATA_DIR, 'branch_pace.json'), 'w', encoding='utf-8') as f:
            _json.dump(pace, f, ensure_ascii=False, indent=2)
        print(f"[OK] branch_pace.json ({len(pace['branches'])}지점)")
    else:
        print("  → build_branch_pace.py 없음 — 스킵")

    # action_proposals
    prop_script = os.path.join(SKILLS_DIR, "action-advisor", "scripts", "generate_proposals.py")
    if os.path.exists(prop_script):
        spec = spec_from_file_location("generate_proposals", prop_script)
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)
        result = mod.generate(DATA_DIR)
        import json as _json
        with open(os.path.join(DATA_DIR, 'action_proposals.json'), 'w', encoding='utf-8') as f:
            _json.dump(result, f, ensure_ascii=False, indent=2)
        s = result['summary']
        print(f"[OK] action_proposals.json - total {s['total']} (high {s['high']} / medium {s['medium']})")
    else:
        print("  → generate_proposals.py 없음 — 스킵")

    print_phase(3.5, "트래커 데이터 + 액션 제안", "OK")


def run_phase_4():
    """Phase 4 - QA 검증"""
    print_phase(4, "QA 검증")

    import pandas as pd

    checks = []

    # 1. 파일 존재 확인
    required_files = [
        "normalized.parquet",
        "parsed.parquet",
        "creative_tier.parquet",
    ]

    for f in required_files:
        path = os.path.join(OUTPUT_DIR, f)
        if os.path.exists(path):
            checks.append(f"[OK] {f} 생성됨")
        else:
            checks.append(f"[FAIL] {f} 없음")

    # 2. 데이터 무결성 검사
    try:
        normalized = pd.read_parquet(os.path.join(OUTPUT_DIR, "normalized.parquet"))
        creative_tier = pd.read_parquet(os.path.join(OUTPUT_DIR, "creative_tier.parquet"))

        raw_cost = normalized['cost'].sum()
        tier_cost = creative_tier['총비용'].sum()

        # OFF 소재 비용 포함
        off_path = os.path.join(OUTPUT_DIR, "creative_off.parquet")
        if os.path.exists(off_path):
            creative_off = pd.read_parquet(off_path)
            tier_cost += creative_off['총비용'].sum()
            checks.append(f"[OK] OFF 소재 {len(creative_off)}개 분리됨")

        cost_diff = abs(raw_cost - tier_cost)
        if cost_diff < raw_cost * 0.01:  # 1% 이하 오차
            checks.append(f"[OK] 비용 무결성 OK (오차: {cost_diff:,.0f}원)")
        else:
            checks.append(f"[FAIL] 비용 불일치 (raw: {raw_cost:,.0f} vs tier: {tier_cost:,.0f})")

        # TIER 분포
        tier_dist = creative_tier['TIER'].value_counts()
        checks.append(f"[OK] TIER 분포: {tier_dist.to_dict()}")

    except Exception as e:
        checks.append(f"[FAIL] 검증 오류: {e}")

    for check in checks:
        print(f"  {check}")

    print_phase(4, "QA 검증", "OK")


def run_phase_5():
    """Phase 5 - 리포트 생성"""
    print_phase(5, "리포트 생성")

    import pandas as pd

    # 5-A: 먼슬리 리포트
    print("\n[5-A] 먼슬리 리포트 생성...")
    script_path = os.path.join(SKILLS_DIR, "report-generator", "scripts", "build_monthly.py")

    if os.path.exists(script_path):
        from importlib.util import spec_from_file_location, module_from_spec

        spec = spec_from_file_location("monthly", script_path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        # 데이터 기준 월 추출 (데이터의 마지막 날짜 기준)
        import pandas as _pd
        _parsed = _pd.read_parquet(os.path.join(DATA_DIR, "parsed.parquet"))
        _parsed['date'] = _pd.to_datetime(_parsed['date'])
        month = _parsed['date'].max().strftime("%Y%m")
        del _parsed
        # build_monthly는 data_dir과 month를 받아서 output/monthly/YYYYMM/에 저장
        module.build_monthly(DATA_DIR, month)
    else:
        print("  → build_monthly.py 없음")

    print_phase(5, "리포트 생성", "OK")


def parse_args():
    parser = argparse.ArgumentParser(description="TikTok 광고 분석 파이프라인")
    parser.add_argument('input', nargs='?', default=None, help='입력 CSV (기본: input/tiktok_raw.csv)')
    parser.add_argument('--collect', action='store_true', help='API로 raw CSV 자동 수집 후 분석')
    parser.add_argument('--days', type=int, default=14, help='--collect 시 최근 N일 (기본 14)')
    parser.add_argument('--start', default=None, help='--collect 시 시작일 YYYY-MM-DD')
    parser.add_argument('--end', default=None, help='--collect 시 종료일 YYYY-MM-DD')
    parser.add_argument('--include-age', action='store_true', help='나이대 breakdown 함께 수집')
    parser.add_argument('--include-hour', action='store_true', help='시간대 breakdown 함께 수집')
    return parser.parse_args()


def main():
    """메인 실행"""
    args = parse_args()
    start_time = time.time()

    print("\n" + "="*60)
    print(">>> TikTok Ad Analysis Pipeline START")
    print("="*60)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"데이터 경로: {DATA_DIR}")

    # API 수집 (선택)
    if args.collect:
        try:
            run_collect(args.days, args.include_age, args.include_hour, args.start, args.end)
        except Exception as e:
            print(f"\n[ERROR] API 수집 실패: {e}")
            print("기존 CSV로 계속 진행합니다.")

        # ad_mapping 갱신 (수집 모드에서만 — API 크레딧 필요)
        try:
            from importlib.util import spec_from_file_location, module_from_spec
            os.makedirs(DATA_DIR, exist_ok=True)
            mapping_script = os.path.join(SKILLS_DIR, "action-advisor", "scripts", "build_ad_mapping.py")
            if os.path.exists(mapping_script):
                spec = spec_from_file_location("build_ad_mapping", mapping_script)
                mod = module_from_spec(spec)
                spec.loader.exec_module(mod)
                mapping = mod.build(mod.TIKTOK_ADVERTISER_ID, mod.TIKTOK_ACCESS_TOKEN)
                import json as _json
                with open(os.path.join(DATA_DIR, 'ad_mapping.json'), 'w', encoding='utf-8') as f:
                    _json.dump(mapping, f, ensure_ascii=False, indent=2)
                print(f"[OK] ad_mapping.json ({len(mapping['ads'])} ads)")
        except Exception as e:
            print(f"[WARNING] ad_mapping 생성 실패: {e}")

    # 입력 파일 확인
    input_csv = args.input or os.path.join(PROJECT_ROOT, "input", "tiktok_raw.csv")

    if not os.path.exists(input_csv):
        print(f"\n[ERROR] Input file not found: {input_csv}")
        print("사용법: python run_analysis.py [input/tiktok_raw.csv] [--collect]")
        sys.exit(1)

    print(f"입력 파일: {input_csv}")

    try:
        # Phase 0: 원본 정규화
        normalized_path = run_phase_0(input_csv)

        # Phase 1: 데이터 준비
        parsed_path = run_phase_1(normalized_path)

        # Phase 2: 병렬 분석
        result = run_phase_2(parsed_path)

        # Phase 3: 인사이트 생성
        run_phase_3()

        # Phase 3.5: 트래커 데이터 + 액션 제안
        run_phase_3_5()

        # Phase 4: QA 검증
        run_phase_4()

        # Phase 5: 리포트 생성
        run_phase_5()

        elapsed = time.time() - start_time

        print("\n" + "="*60)
        print(">>> Pipeline COMPLETE!")
        print("="*60)
        print(f"소요 시간: {elapsed:.1f}초")
        print(f"데이터 경로: {DATA_DIR}")
        print("\n생성된 파일:")
        for f in os.listdir(DATA_DIR):
            size = os.path.getsize(os.path.join(DATA_DIR, f))
            print(f"  - {f} ({size/1024:.1f}KB)")

    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
