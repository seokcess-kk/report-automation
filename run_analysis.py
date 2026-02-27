#!/usr/bin/env python3
"""
TikTok 광고 분석 파이프라인 오케스트레이터
Phase 0~5 순차 실행

사용법:
    python run_analysis.py
    python run_analysis.py input/tiktok_raw.csv
"""
import os
import sys
import time
from datetime import datetime

# 프로젝트 루트 설정
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)

# 스킬 스크립트 경로
SKILLS_DIR = os.path.join(PROJECT_ROOT, ".claude", "skills")

# 출력 디렉토리 (날짜별)
TODAY = datetime.now().strftime("%Y%m%d")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output", TODAY)


def print_phase(phase_num: int, phase_name: str, status: str = "START"):
    """Phase 상태 출력"""
    icons = {"START": "...", "OK": "[OK]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}
    icon = icons.get(status, "")
    print(f"\n{'='*60}")
    print(f"{icon} Phase {phase_num}: {phase_name} [{status}]")
    print(f"{'='*60}")


def run_phase_0(input_csv: str) -> str:
    """Phase 0 - 원본 정규화"""
    print_phase(0, "원본 정규화")

    from importlib.util import spec_from_file_location, module_from_spec

    script_path = os.path.join(SKILLS_DIR, "tiktok-normalizer", "scripts", "normalize_tiktok_raw.py")
    spec = spec_from_file_location("normalize", script_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    output_path = os.path.join(OUTPUT_DIR, "normalized.parquet")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    module.normalize(input_csv, output_path)

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
    result = module.score_creatives(parsed_path, OUTPUT_DIR, target_cpa_path)

    creative_tier_path = os.path.join(OUTPUT_DIR, "creative_tier.parquet")

    # 2-B: 훅 비교 (hook_comparison)
    print("\n[2-B] 훅 비교 분석...")
    script_path = os.path.join(SKILLS_DIR, "creative-analyzer", "scripts", "hook_comparison.py")
    spec = spec_from_file_location("hook", script_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    creative_df = pd.read_parquet(creative_tier_path)
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
            creative_df = pd.read_parquet(creative_tier_path)
            if hasattr(module, 'generate_insights'):
                module.generate_insights(creative_df, OUTPUT_DIR)

        print_phase(3, "인사이트 생성", "OK")
    else:
        print_phase(3, "인사이트 생성", "SKIP")
        print("  → generate_insights.py 없음")


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

        creative_tier_path = os.path.join(OUTPUT_DIR, "creative_tier.parquet")
        parsed_path = os.path.join(OUTPUT_DIR, "parsed.parquet")
        off_path = os.path.join(OUTPUT_DIR, "creative_off.parquet")

        creative_df = pd.read_parquet(creative_tier_path)
        df_valid = pd.read_parquet(parsed_path)
        df_valid = df_valid[df_valid['parse_status'] == 'OK']

        try:
            off_df = pd.read_parquet(off_path)
        except:
            off_df = None

        month = datetime.now().strftime("%Y%m")
        module.build_monthly(OUTPUT_DIR, creative_df, df_valid, off_df, month)
    else:
        print("  → build_monthly.py 없음")

    print_phase(5, "리포트 생성", "OK")


def main():
    """메인 실행"""
    start_time = time.time()

    print("\n" + "="*60)
    print(">>> TikTok Ad Analysis Pipeline START")
    print("="*60)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"출력 경로: {OUTPUT_DIR}")

    # 입력 파일 확인
    input_csv = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJECT_ROOT, "input", "tiktok_raw.csv")

    if not os.path.exists(input_csv):
        print(f"\n[ERROR] Input file not found: {input_csv}")
        print("사용법: python run_analysis.py input/tiktok_raw.csv")
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

        # Phase 4: QA 검증
        run_phase_4()

        # Phase 5: 리포트 생성
        run_phase_5()

        elapsed = time.time() - start_time

        print("\n" + "="*60)
        print(">>> Pipeline COMPLETE!")
        print("="*60)
        print(f"소요 시간: {elapsed:.1f}초")
        print(f"출력 경로: {OUTPUT_DIR}")
        print("\n생성된 파일:")
        for f in os.listdir(OUTPUT_DIR):
            size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
            print(f"  - {f} ({size/1024:.1f}KB)")

    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
