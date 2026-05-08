"""
4월 종합 광고 분석 리포트 (1회성, 16섹션)
출력: output/analysis/april_comprehensive_202604.html
"""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "output" / "data" / "20260507"
OUT = ROOT / "output" / "analysis" / "april_comprehensive_202604.html"
TPL = ROOT / "output" / "analysis" / "_template_comprehensive.html"

AGE_ORDER = ["25-34", "35-44", "45-54", "≥55", "Unknown"]
CORE_AGES = ["35-44", "45-54", "≥55"]
CT_ORDER = ["진료셀프캠", "인플방문후기", "의료진정보", "진료QnA", "리얼모델후기"]
# 광고 등록 시 잘못 표기된 카테고리 → 정정
CT_ALIAS = {"방문후기": "인플방문후기"}
BRANCH_ORDER = ["서울", "부평", "수원", "일산", "대구", "창원", "천안", "대전"]

# 4월 먼슬리에서 사용된 목표
TARGET_CPA = 29_119
TARGET_CONV_TOTAL = 1_131
TARGET_CONV_BY_BRANCH = {
    '서울': 150, '부평': 150, '수원': 201, '일산': 150,
    '대구': 150, '창원': 100, '천안': 150, '대전': 80,
}
# 4월 실제 지점별 예산 (먼슬리 리포트 기준 / 합계 22,000,000원)
BUDGET_BY_BRANCH = {
    '서울': 2_000_000, '부평': 4_000_000, '수원': 4_000_000, '일산': 2_000_000,
    '대구': 3_000_000, '창원': 3_000_000, '천안': 2_000_000, '대전': 2_000_000,
}


def load():
    parsed = pd.read_parquet(DATA_DIR / "parsed.parquet")
    nba = pd.read_parquet(DATA_DIR / "normalized_by_age.parquet")
    parsed["date"] = pd.to_datetime(parsed["date"])
    nba["date"] = pd.to_datetime(nba["date"])
    pa = parsed[(parsed["date"] >= "2026-04-01") & (parsed["date"] <= "2026-04-30")].copy()
    na = nba[(nba["date"] >= "2026-04-01") & (nba["date"] <= "2026-04-30")].copy()
    # 잘못 표기된 카테고리 정정 (방문후기 → 인플방문후기)
    pa["소재유형"] = pa["소재유형"].replace(CT_ALIAS)
    meta = parsed[["ad_name", "지점", "소재유형", "소재구분", "소재명"]].drop_duplicates(subset=["ad_name"]).copy()
    meta["소재유형"] = meta["소재유형"].replace(CT_ALIAS)
    age_df = na.merge(meta, on="ad_name", how="left").dropna(subset=["지점", "소재유형", "소재명"])
    return pa, age_df, meta


def kpi(g):
    cost = int(g["cost"].sum())
    conv = int(g["conversions"].sum())
    click = int(g["clicks"].sum())
    imp = int(g["impressions"].sum()) if "impressions" in g.columns else 0
    return {
        "cost": cost, "conv": conv, "click": click, "imp": imp,
        "cpa": int(cost / conv) if conv > 0 else None,
        "cvr": round(conv / click * 100, 2) if click > 0 else 0.0,
        "ctr": round(click / imp * 100, 2) if imp > 0 else 0.0,
    }


def confidence_of(click):
    """클릭 수 기반 신뢰도 등급
    - low: 30-99 (참고)
    - mid: 100-299 (테스트 가능)
    - high: 300+ (운영 판단 가능)
    """
    if click >= 300: return "high"
    if click >= 100: return "mid"
    if click >= 30: return "low"
    return "none"


def week_of(d):
    if d <= pd.Timestamp("2026-04-07"): return "W1"
    if d <= pd.Timestamp("2026-04-14"): return "W2"
    if d <= pd.Timestamp("2026-04-21"): return "W3"
    return "W4"


def week_label(w):
    # W1은 4/1 셋팅 미실행으로 4/2~7 6일치 집계
    return {"W1": "W1 (4/2-7)", "W2": "W2 (4/8-14)", "W3": "W3 (4/15-21)", "W4": "W4 (4/22-30)"}[w]


def build(pa, age_df, meta):
    # ================= 1. 4월 한 줄 진단 + 총합 =================
    total = kpi(pa)
    achievement = {
        "conv_pct": round(total["conv"] / TARGET_CONV_TOTAL * 100, 1),
        "cpa_vs_target_pct": round((total["cpa"] - TARGET_CPA) / TARGET_CPA * 100, 1) if total["cpa"] else None,
        "budget_pct": round(total["cost"] / sum(BUDGET_BY_BRANCH.values()) * 100, 1),
    }

    # ================= 2. 월간 흐름 =================
    pa = pa.copy()
    pa["week"] = pa["date"].apply(week_of)
    weekly = []
    for w in ["W1", "W2", "W3", "W4"]:
        sub = pa[pa["week"] == w]
        k = kpi(sub)
        k["week"] = w
        k["label"] = week_label(w)
        k["ad_count"] = int(sub["ad_id"].nunique())
        weekly.append(k)

    # 일별 KPI · 4/1은 캠페인 셋팅 미실행으로 제외 (실제 운영 4/2~30)
    daily = []
    for d, sub in pa.groupby("date"):
        if d == pd.Timestamp("2026-04-01"):
            continue
        k = kpi(sub)
        k["date"] = d.strftime("%Y-%m-%d")
        daily.append(k)
    daily.sort(key=lambda r: r["date"])

    # ON vs OFF
    on_off = {
        "ON": kpi(pa[pa["is_off"] == False]),
        "OFF": kpi(pa[pa["is_off"] == True]),
    }
    # 신규(2604_*) vs 기존
    pa["is_new_apr"] = pa["ad_name"].str.contains("_260[3-4]", regex=True, na=False)
    new_recycled = {
        "NEW_APR": kpi(pa[pa["is_new_apr"]]),
        "EXISTING": kpi(pa[~pa["is_new_apr"]]),
    }
    # 신규 vs 재가공
    hook_kpi = []
    for h in ["신규", "재가공"]:
        sub = pa[pa["소재구분"] == h]
        if len(sub) == 0: continue
        k = kpi(sub)
        k["hook"] = h
        k["ad_count"] = int(sub["ad_id"].nunique())
        hook_kpi.append(k)

    # ================= 3. 나이대 구조 =================
    age_kpi = []
    age_total_cost = age_df["cost"].sum()
    age_total_conv = age_df["conversions"].sum()
    for ag in AGE_ORDER:
        sub = age_df[age_df["age_group"] == ag]
        if len(sub) == 0: continue
        k = kpi(sub)
        k["age_group"] = ag
        k["share_cost"] = round(k["cost"] / age_total_cost * 100, 1)
        k["share_conv"] = round(k["conv"] / age_total_conv * 100, 1)
        k["gap"] = round(k["share_conv"] - k["share_cost"], 1)
        age_kpi.append(k)

    # ================= 4. 소재유형별 KPI + 역할 =================
    ct_kpi = []
    for ct in CT_ORDER:
        sub = pa[pa["소재유형"] == ct]
        if len(sub) == 0: continue
        k = kpi(sub)
        k["creative_type"] = ct
        k["share_cost"] = round(k["cost"] / total["cost"] * 100, 1)
        k["share_conv"] = round(k["conv"] / total["conv"] * 100, 1) if total["conv"] else 0
        k["ad_count"] = int(sub["ad_id"].nunique())
        # 어느 나이대/지점에서 가장 강했는지
        ct_age = age_df[age_df["소재유형"] == ct].groupby("age_group").agg(
            cost=("cost", "sum"), conv=("conversions", "sum"), click=("clicks", "sum")
        )
        ct_age["cvr"] = ct_age["conv"] / ct_age["click"].replace(0, pd.NA) * 100
        ct_age = ct_age[ct_age["click"] >= 30]
        if len(ct_age) > 0:
            best_age = ct_age["cvr"].idxmax()
            k["best_age"] = best_age
            k["best_age_cvr"] = round(float(ct_age.loc[best_age, "cvr"]), 2)
        ct_branch = pa[pa["소재유형"] == ct].groupby("지점").agg(
            cost=("cost", "sum"), conv=("conversions", "sum"), click=("clicks", "sum")
        )
        ct_branch["cvr"] = ct_branch["conv"] / ct_branch["click"].replace(0, pd.NA) * 100
        ct_branch = ct_branch[ct_branch["click"] >= 50]
        if len(ct_branch) > 0:
            best_br = ct_branch["cvr"].idxmax()
            k["best_branch"] = best_br
            k["best_branch_cvr"] = round(float(ct_branch.loc[best_br, "cvr"]), 2)
        ct_kpi.append(k)

    # ================= 5. 매트릭스 (소재유형 × 나이대). Unknown 제외 =================
    matrix = []
    for ct in CT_ORDER:
        for ag in [a for a in AGE_ORDER if a != "Unknown"]:
            sub = age_df[(age_df["소재유형"] == ct) & (age_df["age_group"] == ag)]
            if len(sub) == 0: continue
            k = kpi(sub)
            k["confidence"] = confidence_of(k["click"])
            matrix.append({"creative_type": ct, "age_group": ag, **k})

    # ================= 6. 지점별 KPI + 목표대비 =================
    branch_kpi = []
    for br in BRANCH_ORDER:
        sub = pa[pa["지점"] == br]
        k = kpi(sub)
        k["branch"] = br
        k["target_conv"] = TARGET_CONV_BY_BRANCH[br]
        k["budget"] = BUDGET_BY_BRANCH[br]
        k["conv_pct"] = round(k["conv"] / k["target_conv"] * 100, 1) if k["target_conv"] else 0
        k["budget_pct"] = round(k["cost"] / k["budget"] * 100, 1) if k["budget"] else 0
        # 가장 강한 나이대
        ba = age_df[age_df["지점"] == br].groupby("age_group").agg(
            cost=("cost", "sum"), conv=("conversions", "sum"), click=("clicks", "sum")
        )
        ba["cvr"] = ba["conv"] / ba["click"].replace(0, pd.NA) * 100
        ba = ba[ba["click"] >= 30]
        if len(ba) > 0:
            k["best_age"] = ba["cvr"].idxmax()
            k["best_age_cvr"] = round(float(ba["cvr"].max()), 2)
        # 가장 강한 소재유형
        bc = pa[pa["지점"] == br].groupby("소재유형").agg(
            cost=("cost", "sum"), conv=("conversions", "sum"), click=("clicks", "sum")
        )
        bc["cvr"] = bc["conv"] / bc["click"].replace(0, pd.NA) * 100
        bc = bc[bc["click"] >= 50]
        if len(bc) > 0:
            k["best_ct"] = bc["cvr"].idxmax()
            k["best_ct_cvr"] = round(float(bc["cvr"].max()), 2)
        branch_kpi.append(k)

    # ================= 7. 지점 × 나이대 (Unknown 제외) =================
    branch_age = []
    for br in BRANCH_ORDER:
        for ag in [a for a in AGE_ORDER if a != "Unknown"]:
            sub = age_df[(age_df["지점"] == br) & (age_df["age_group"] == ag)]
            if len(sub) == 0: continue
            k = kpi(sub)
            k["confidence"] = confidence_of(k["click"])
            branch_age.append({"branch": br, "age_group": ag, **k})

    # ================= 8. 지점 × 소재유형 =================
    branch_ct = []
    for br in BRANCH_ORDER:
        for ct in CT_ORDER:
            sub = pa[(pa["지점"] == br) & (pa["소재유형"] == ct)]
            if len(sub) == 0: continue
            k = kpi(sub)
            k["confidence"] = confidence_of(k["click"])
            branch_ct.append({"branch": br, "creative_type": ct, **k})

    # ================= 9. 지점 × 나이대 × 소재유형 (셀) + 셀 내부 소재명 드릴다운 =================
    branch_cells = {}
    for br in BRANCH_ORDER:
        sub = age_df[age_df["지점"] == br]
        cells = []
        for (ag, ct), gg in sub.groupby(["age_group", "소재유형"]):
            click = int(gg["clicks"].sum())
            if click < 30: continue
            cost = int(gg["cost"].sum())
            conv = int(gg["conversions"].sum())
            # 셀 내부. 소재명별로 분해
            inner = []
            for cn, ggg in gg.groupby("소재명"):
                c = int(ggg["clicks"].sum())
                co = int(ggg["conversions"].sum())
                cs = int(ggg["cost"].sum())
                if cs < 5_000 and co == 0:
                    continue  # 미미한 노출은 제외
                inner.append({
                    "creative_name": cn,
                    "hook": ggg["소재구분"].iloc[0],
                    "cost": cs, "conv": co, "click": c,
                    "cpa": int(cs / co) if co > 0 else None,
                    "cvr": round(co / c * 100, 2) if c > 0 else 0,
                    "share_cost": round(cs / cost * 100, 1) if cost else 0,
                    "share_conv": round(co / conv * 100, 1) if conv else 0,
                })
            # 성과가 좋은 조합: 전환 기여 큰 순서로 / 전환이 낮은 조합: 비용 큰 순서로
            inner_by_conv = sorted(inner, key=lambda r: -r["conv"])
            inner_by_cost = sorted(inner, key=lambda r: -r["cost"])
            cells.append({
                "age_group": ag, "creative_type": ct,
                "cost": cost, "conv": conv, "click": click,
                "cpa": int(cost / conv) if conv > 0 else None,
                "cvr": round(conv / click * 100, 2),
                "confidence": confidence_of(click),
                "top_by_conv": inner_by_conv[:3],
                "top_by_cost": inner_by_cost[:3],
            })
        cells.sort(key=lambda r: r["cvr"], reverse=True)
        bk = kpi(sub)
        branch_cells[br] = {**bk, "cells": cells}

    # ================= 10. 소재별 승리 조합 =================
    # 각 소재명에 대해 최강 지점·나이대 셀 + 비용 큰 전환이 낮은 조합
    creative_winners = []
    for cn, gg in age_df.groupby("소재명"):
        total_cost = int(gg["cost"].sum())
        total_conv = int(gg["conversions"].sum())
        total_click = int(gg["clicks"].sum())
        if total_cost < 200_000 or total_click < 100:
            continue
        ct = gg["소재유형"].iloc[0]
        hook = gg["소재구분"].iloc[0]
        # 셀 단위 (지점×나이대)
        cells = []
        for (br, ag), cgg in gg.groupby(["지점", "age_group"]):
            click = int(cgg["clicks"].sum())
            if click < 20: continue
            cost = int(cgg["cost"].sum())
            conv = int(cgg["conversions"].sum())
            cells.append({
                "branch": br, "age_group": ag,
                "cost": cost, "conv": conv, "click": click,
                "cvr": round(conv / click * 100, 2),
                "cpa": int(cost / conv) if conv > 0 else None,
            })
        if not cells: continue
        cells.sort(key=lambda r: r["cvr"], reverse=True)
        creative_winners.append({
            "creative_name": cn, "creative_type": ct, "hook": hook,
            "total_cost": total_cost, "total_conv": total_conv, "total_click": total_click,
            "cvr": round(total_conv / total_click * 100, 2) if total_click else 0,
            "cpa": int(total_cost / total_conv) if total_conv > 0 else None,
            "branch_count": int(gg["지점"].nunique()),
            "best_cell": cells[0],
            "worst_cell": cells[-1] if len(cells) > 1 else None,
            "cell_count": len(cells),
        })
    creative_winners.sort(key=lambda r: -r["total_conv"])

    # ================= 11. 비효율 조합 =================
    # 비용 ≥ 30만 AND (CVR < 4% OR CPA > target_cpa × 1.5)
    inefficient = []
    for r in branch_age + branch_ct:
        # branch_age는 'age_group', branch_ct는 'creative_type'
        if r["click"] < 30: continue
        if r["cost"] < 300_000: continue
        bad_cvr = r["cvr"] < 4.0
        bad_cpa = r["cpa"] is not None and r["cpa"] > TARGET_CPA * 1.5
        if not (bad_cvr or bad_cpa): continue
        rec = {**r, "type": "branch_age" if "age_group" in r else "branch_ct",
               "reason": ("CVR 부진" if bad_cvr else "") + (" + " if bad_cvr and bad_cpa else "") + ("CPA 초과" if bad_cpa else "")}
        inefficient.append(rec)
    # 셀 단위(지점×나이×소재)도 추가. 비용 ≥ 20만, CVR <3 또는 CPA > target × 2
    for br, b in branch_cells.items():
        for c in b["cells"]:
            if c["cost"] < 200_000: continue
            very_bad = c["cvr"] < 3.0 or (c["cpa"] is not None and c["cpa"] > TARGET_CPA * 2)
            if very_bad:
                inefficient.append({
                    "type": "cell", "branch": br,
                    "age_group": c["age_group"], "creative_type": c["creative_type"],
                    "cost": c["cost"], "conv": c["conv"], "click": c["click"],
                    "cvr": c["cvr"], "cpa": c["cpa"],
                    "reason": "명확히 비효율적인 조합",
                })
    inefficient.sort(key=lambda r: -r["cost"])

    # ================= 12. 지역 특성 클러스터 =================
    # 지점별 가장 강한 나이대를 group으로
    region_clusters = {"high_age": [], "mid_age": [], "low_age": [], "balanced": []}
    for bk in branch_kpi:
        if not bk.get("best_age"): continue
        if bk["best_age"] in ("≥55",):
            region_clusters["high_age"].append(bk["branch"])
        elif bk["best_age"] in ("45-54",):
            region_clusters["mid_age"].append(bk["branch"])
        elif bk["best_age"] in ("35-44",):
            region_clusters["low_age"].append(bk["branch"])
        # 나이별 격차가 작으면 balanced (서로 다른 셀들의 CVR std가 작음)
    # 인플 강세/약세 지점
    influ_strong, influ_weak = [], []
    for r in branch_ct:
        if r["creative_type"] != "인플방문후기": continue
        if r["click"] < 50: continue
        if r["cvr"] >= 6.5: influ_strong.append(r["branch"])
        if r["cvr"] < 4.5: influ_weak.append(r["branch"])

    region_summary = {
        "clusters": region_clusters,
        "influ_strong": influ_strong,
        "influ_weak": influ_weak,
    }

    # ================= Unknown 분리 =================
    unknown_sub = age_df[age_df["age_group"] == "Unknown"]
    unknown_summary = {
        **kpi(unknown_sub),
        "rows": int(len(unknown_sub)),
        "by_branch": [
            {"branch": br, "cost": int(g["cost"].sum()), "conv": int(g["conversions"].sum()), "click": int(g["clicks"].sum())}
            for br, g in unknown_sub.groupby("지점")
        ],
    }

    # ================= ≥55 의료진정보 상세 (지점·소재명별) =================
    sm = age_df[(age_df["age_group"] == "≥55") & (age_df["소재유형"] == "의료진정보")]
    sm_total = kpi(sm)
    sm_by_branch = []
    for br in BRANCH_ORDER:
        g = sm[sm["지점"] == br]
        if len(g) == 0:
            continue
        sm_by_branch.append({"branch": br, **kpi(g)})
    sm_by_branch.sort(key=lambda r: -r["conv"])
    sm_by_creative = []
    for cn, g in sm.groupby("소재명"):
        cost = int(g["cost"].sum())
        if cost < 5_000:
            continue
        sm_by_creative.append({
            "creative_name": cn,
            "hook": g["소재구분"].iloc[0],
            **kpi(g),
            "branches": sorted(set(g["지점"].dropna().tolist())),
            "branch_count": int(g["지점"].nunique()),
        })
    sm_by_creative.sort(key=lambda r: -r["conv"])
    senior_med = {
        "total": sm_total,
        "by_branch": sm_by_branch,
        "by_creative": sm_by_creative,
    }

    # ================= 확장 / 축소 Top =================
    # 확장 후보: cell 단위 (지점×나이×소재유형). CVR 7%+ AND click ≥ 100 AND CPA < target
    expand_candidates = []
    for br, b in branch_cells.items():
        for c in b["cells"]:
            if c["confidence"] not in ("mid", "high"):
                continue
            if c["cvr"] < 7.0:
                continue
            if c["cpa"] is None or c["cpa"] > TARGET_CPA:
                continue
            expand_candidates.append({
                "branch": br, "age_group": c["age_group"], "creative_type": c["creative_type"],
                "cost": c["cost"], "conv": c["conv"], "click": c["click"], "cvr": c["cvr"], "cpa": c["cpa"],
                "confidence": c["confidence"],
                "top_creative": c["top_by_conv"][0] if c["top_by_conv"] else None,
            })
    expand_candidates.sort(key=lambda r: (-r["cvr"], -r["conv"]))
    expand_top = expand_candidates[:5]

    # 축소 후보: cell 단위. CVR < 4% AND cost ≥ 200k OR CPA > target × 1.5 AND cost ≥ 300k
    reduce_candidates = []
    for br, b in branch_cells.items():
        for c in b["cells"]:
            if c["click"] < 30:
                continue
            cond_a = c["cvr"] < 4.0 and c["cost"] >= 200_000
            cond_b = (c["cpa"] is not None and c["cpa"] > TARGET_CPA * 1.5) and c["cost"] >= 300_000
            if not (cond_a or cond_b):
                continue
            reduce_candidates.append({
                "branch": br, "age_group": c["age_group"], "creative_type": c["creative_type"],
                "cost": c["cost"], "conv": c["conv"], "click": c["click"], "cvr": c["cvr"], "cpa": c["cpa"],
                "confidence": c["confidence"],
                "leak_creative": c["top_by_cost"][0] if c["top_by_cost"] else None,
            })
    reduce_candidates.sort(key=lambda r: -r["cost"])
    reduce_top = reduce_candidates[:5]

    # ================= 5월 첫 주 액션 (P0급 3개로 압축) =================
    # 자동 추출 + 수동 큐레이션. 회수·예상 효과·모니터링 명시
    suwon_25 = age_df[(age_df["지점"] == "수원") & (age_df["age_group"] == "25-34")]
    suwon_25_cost = int(suwon_25["cost"].sum())
    suwon_25_conv = int(suwon_25["conversions"].sum())
    seoul_55_jr = age_df[(age_df["지점"] == "서울") & (age_df["age_group"] == "≥55") & (age_df["소재유형"] == "진료셀프캠")]
    seoul_55_cost = int(seoul_55_jr["cost"].sum())
    seoul_55_conv = int(seoul_55_jr["conversions"].sum())
    seoul_55_cvr = round(seoul_55_conv / seoul_55_jr["clicks"].sum() * 100, 2) if seoul_55_jr["clicks"].sum() else 0
    # ≥55 의료진정보 소액 테스트 후보 데이터 · 수원/부평/천안
    sm_test = {}
    for br in ["수원", "부평", "천안"]:
        g = age_df[(age_df["지점"] == br) & (age_df["age_group"] == "≥55") & (age_df["소재유형"] == "의료진정보")]
        sm_test[br] = {
            "cost": int(g["cost"].sum()),
            "conv": int(g["conversions"].sum()),
            "click": int(g["clicks"].sum()),
            "cvr": round(g["conversions"].sum() / g["clicks"].sum() * 100, 2) if g["clicks"].sum() else 0,
        }

    # 평균 CPA 개선 효과: 차단 대상의 cost 빼고 conv 빼고 다시 계산
    def cpa_after_remove(rm_cost, rm_conv):
        new_cost = total["cost"] - rm_cost
        new_conv = total["conv"] - rm_conv
        if new_conv == 0:
            return None
        return int(new_cost / new_conv)
    base_cpa = total["cpa"]
    suwon_25_after = cpa_after_remove(suwon_25_cost, suwon_25_conv)
    sm_total_cost = sum(sm_test[br]["cost"] for br in sm_test)
    sm_total_conv = sum(sm_test[br]["conv"] for br in sm_test)

    week1_actions = [
        {
            "kind": "reduce", "priority": "P0",
            "what": "수원 25-34 3개 셀 차단",
            "detail": f"셀 비용 {suwon_25_cost:,}원, 전환 {suwon_25_conv}건, CVR 1.5~2.2%, CPA 5.4~11.9만원. 비용 대비 전환이 명확히 낮은 조합.",
            "recovery": f"{suwon_25_cost:,}원/월 회수 (확정)",
            "effect": f"평균 CPA {base_cpa:,}원 → 약 {suwon_25_after:,}원 (추정 개선 약 {base_cpa-suwon_25_after}원)" if suwon_25_after else "-",
            "monitor": "차단 후 1주간 수원 35-44 인플방문후기 / ≥55 진료셀프캠 CVR 변동 추적",
        },
        {
            "kind": "expand", "priority": "P0",
            "what": "서울 ≥55 × 진료셀프캠 비중 확대",
            "detail": f"4월 비용 {seoul_55_cost:,}원 / 전환 {seoul_55_conv}건 / CVR {seoul_55_cvr}%. 4월 전사 1위 셀(신뢰도 high).",
            "recovery": "비용 30~40만원 추가 투입 (5월 1주차)",
            "effect": "추정 · 동일 CVR(10.7%) 유지 가정 시 추가 전환 25~30건, CPA 12,000~14,000원대 유지 가능",
            "monitor": "1주 후 CVR 8% 미만으로 떨어지면 확대 중단. 신규 ≥55 진료셀프캠 소재 인입 검토",
        },
        {
            "kind": "test", "priority": "P0",
            "what": "수원·부평·천안 ≥55 × 의료진정보 소액 테스트",
            "detail": (f"3개 지점 합계 비용 {sm_total_cost:,}원 / 전환 {sm_total_conv}건 / CVR 9.4~13.0% (신뢰도 low). "
                       f"수원 click {sm_test['수원']['click']}건 CVR {sm_test['수원']['cvr']}%, "
                       f"부평 click {sm_test['부평']['click']}건 CVR {sm_test['부평']['cvr']}%, "
                       f"천안 click {sm_test['천안']['click']}건 CVR {sm_test['천안']['cvr']}%. "
                       f"핵심 견인 소재: \"주사형비만치료제 10년은\"(신규)."),
            "recovery": f"3개 지점 각 8~10만원으로 확대(현재 합계 {sm_total_cost:,}원 → 약 25~30만원)",
            "effect": "추정 · 표본을 click 100+ (신뢰도 mid)까지 확대하여 CVR 9% 이상 신호 검증. 일산·창원은 이번 테스트에서 제외(4월 전환 0건).",
            "monitor": "확대 후 1주 누적 CVR 7% 미만이면 즉시 원위치. 핵심 견인 소재의 click·conv 분포 추적.",
        },
    ]

    return {
        "period": "2026.04.01 ~ 04.30",
        "targets": {
            "target_cpa": TARGET_CPA,
            "target_conv": TARGET_CONV_TOTAL,
            "total_budget": sum(BUDGET_BY_BRANCH.values()),
        },
        "total": total,
        "achievement": achievement,
        "weekly": weekly,
        "daily": daily,
        "on_off": on_off,
        "new_recycled": new_recycled,
        "hook_kpi": hook_kpi,
        "age_kpi": age_kpi,
        "ct_kpi": ct_kpi,
        "matrix": matrix,
        "branch_kpi": branch_kpi,
        "branch_age": branch_age,
        "branch_ct": branch_ct,
        "branch_cells": branch_cells,
        "creative_winners": creative_winners,
        "inefficient": inefficient[:20],
        "region": region_summary,
        "unknown": unknown_summary,
        "senior_med": senior_med,
        "expand_top": expand_top,
        "reduce_top": reduce_top,
        "week1_actions": week1_actions,
    }


def main():
    pa, age_df, meta = load()
    D = build(pa, age_df, meta)
    template = TPL.read_text(encoding="utf-8")
    html = template.replace("__DATA__", json.dumps(D, ensure_ascii=False, default=str))
    OUT.write_text(html, encoding="utf-8")
    print(f"[OK] {OUT}")
    print(f"  period: {D['period']}")
    print(f"  total: cost {D['total']['cost']:,} / conv {D['total']['conv']} / cpa {D['total']['cpa']:,}")
    print(f"  weekly: {len(D['weekly'])} weeks, daily: {len(D['daily'])} days")
    print(f"  branches: {len(D['branch_kpi'])}, branch_age: {len(D['branch_age'])}, branch_ct: {len(D['branch_ct'])}")
    print(f"  creative_winners: {len(D['creative_winners'])}, inefficient: {len(D['inefficient'])}")


if __name__ == "__main__":
    main()
