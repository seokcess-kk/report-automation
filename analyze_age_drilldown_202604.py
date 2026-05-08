"""
4월 나이대 × 소재유형 × 지점 드릴다운 분석 (1회성)
출력: output/analysis/age_drilldown_202604.html
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "output" / "data" / "20260507"
OUT = ROOT / "output" / "analysis" / "age_drilldown_202604.html"

AGE_ORDER = ["25-34", "35-44", "45-54", "≥55", "Unknown"]
CORE_AGES = ["35-44", "45-54", "≥55"]
CT_ORDER = ["진료셀프캠", "인플방문후기", "의료진정보", "방문후기", "진료QnA", "리얼모델후기"]
BRANCH_ORDER = ["서울", "부평", "수원", "일산", "대구", "창원", "천안", "대전"]


def load():
    nba = pd.read_parquet(DATA_DIR / "normalized_by_age.parquet")
    parsed = pd.read_parquet(DATA_DIR / "parsed.parquet")
    meta = parsed[["ad_name", "지점", "소재유형", "소재구분", "소재명"]].drop_duplicates(subset=["ad_name"])
    nba["date"] = pd.to_datetime(nba["date"])
    df = nba[(nba["date"] >= "2026-04-01") & (nba["date"] <= "2026-04-30")].copy()
    df = df.merge(meta, on="ad_name", how="left").dropna(subset=["지점", "소재유형", "소재명"])
    return df


def kpi(g):
    cost = int(g["cost"].sum())
    conv = int(g["conversions"].sum())
    click = int(g["clicks"].sum())
    imp = int(g["impressions"].sum())
    return {
        "cost": cost,
        "conv": conv,
        "click": click,
        "imp": imp,
        "cpa": int(cost / conv) if conv > 0 else None,
        "cvr": round(conv / click * 100, 2) if click > 0 else 0.0,
        "ctr": round(click / imp * 100, 2) if imp > 0 else 0.0,
    }


def build_data(df):
    total_cost = int(df["cost"].sum())
    total_conv = int(df["conversions"].sum())
    total_click = int(df["clicks"].sum())
    overall_cpa = total_cost / total_conv if total_conv > 0 else None

    # ===== A. 나이대별 KPI =====
    age_kpi = []
    for ag in AGE_ORDER:
        sub = df[df["age_group"] == ag]
        if len(sub) == 0:
            continue
        k = kpi(sub)
        k["age_group"] = ag
        k["share_cost"] = round(k["cost"] / total_cost * 100, 1) if total_cost else 0
        k["share_conv"] = round(k["conv"] / total_conv * 100, 1) if total_conv else 0
        k["gap"] = round(k["share_conv"] - k["share_cost"], 1)
        age_kpi.append(k)

    # ===== A. 매트릭스 (소재유형 × 나이대) =====
    matrix = []
    for ct in CT_ORDER:
        for ag in AGE_ORDER:
            sub = df[(df["소재유형"] == ct) & (df["age_group"] == ag)]
            if len(sub) == 0:
                continue
            k = kpi(sub)
            matrix.append({"creative_type": ct, "age_group": ag, **k})

    # ===== B. 나이대별 TOP 소재 =====
    top_by_age = {}
    for ag in AGE_ORDER:
        sub = df[df["age_group"] == ag]
        rows = []
        for cn, gg in sub.groupby("소재명"):
            click = int(gg["clicks"].sum())
            if click < 30:
                continue
            cost = int(gg["cost"].sum())
            conv = int(gg["conversions"].sum())
            rows.append({
                "creative_name": cn,
                "creative_type": gg["소재유형"].iloc[0],
                "hook": gg["소재구분"].iloc[0],
                "cost": cost,
                "conv": conv,
                "click": click,
                "cpa": int(cost / conv) if conv > 0 else None,
                "cvr": round(conv / click * 100, 2),
                "branch_count": int(gg["지점"].nunique()),
            })
        rows.sort(key=lambda r: r["conv"], reverse=True)
        top_by_age[ag] = rows[:8]

    # ===== D. 지점별 셀 분석 =====
    branch_cells = {}
    for br in BRANCH_ORDER:
        sub = df[df["지점"] == br]
        cells = []
        for (ag, ct), gg in sub.groupby(["age_group", "소재유형"]):
            click = int(gg["clicks"].sum())
            if click < 30:
                continue
            cost = int(gg["cost"].sum())
            conv = int(gg["conversions"].sum())
            cells.append({
                "age_group": ag,
                "creative_type": ct,
                "cost": cost,
                "conv": conv,
                "click": click,
                "cpa": int(cost / conv) if conv > 0 else None,
                "cvr": round(conv / click * 100, 2),
            })
        cells.sort(key=lambda r: r["cvr"], reverse=True)
        bk = kpi(sub)
        # 나이대 분포
        age_share = []
        for ag in AGE_ORDER:
            sa = sub[sub["age_group"] == ag]
            if len(sa) == 0:
                continue
            ak = kpi(sa)
            age_share.append({
                "age_group": ag,
                "cost": ak["cost"],
                "conv": ak["conv"],
                "cvr": ak["cvr"],
                "cpa": ak["cpa"],
                "share_cost": round(ak["cost"] / bk["cost"] * 100, 1) if bk["cost"] else 0,
            })
        # 소재유형 분포
        ct_share = []
        for ct in CT_ORDER:
            sc = sub[sub["소재유형"] == ct]
            if len(sc) == 0 or sc["clicks"].sum() < 30:
                continue
            ck = kpi(sc)
            ct_share.append({
                "creative_type": ct,
                "cost": ck["cost"],
                "conv": ck["conv"],
                "cvr": ck["cvr"],
                "cpa": ck["cpa"],
                "share_cost": round(ck["cost"] / bk["cost"] * 100, 1) if bk["cost"] else 0,
            })
        ct_share.sort(key=lambda r: -r["cost"])
        branch_cells[br] = {
            **bk,
            "cells": cells,
            "age_share": age_share,
            "ct_share": ct_share,
        }

    # ===== E. 나이대 격차 큰 소재 =====
    sub_core = df[df["age_group"].isin(CORE_AGES)]
    g = sub_core.groupby(["소재명", "age_group"]).agg(
        cost=("cost", "sum"),
        conv=("conversions", "sum"),
        click=("clicks", "sum"),
    ).reset_index()
    g["CVR"] = g.apply(
        lambda r: r["conv"] / r["click"] * 100 if r["click"] >= 30 else None, axis=1
    )
    piv = g.pivot(index="소재명", columns="age_group", values="CVR")
    piv_cost = g.pivot(index="소재명", columns="age_group", values="cost").fillna(0)
    ct_map = sub_core.drop_duplicates(subset=["소재명"]).set_index("소재명")["소재유형"]
    total_cn_cost = piv_cost.sum(axis=1)
    valid = piv.notna().sum(axis=1)
    mask = (total_cn_cost >= 300_000) & (valid >= 2)
    age_gap = []
    for cn in piv[mask].index:
        row = {ag: (None if pd.isna(piv.at[cn, ag]) else round(piv.at[cn, ag], 2))
               for ag in CORE_AGES if ag in piv.columns}
        valid_vals = [v for v in row.values() if v is not None]
        if len(valid_vals) < 2:
            continue
        max_v = max(valid_vals)
        min_v = min(valid_vals)
        max_age = [a for a, v in row.items() if v == max_v][0]
        min_age = [a for a, v in row.items() if v == min_v][0]
        age_gap.append({
            "creative_name": cn,
            "creative_type": ct_map.get(cn, "-"),
            "by_age": row,
            "total_cost": int(total_cn_cost[cn]),
            "spread": round(max_v - min_v, 2),
            "max_age": max_age,
            "min_age": min_age,
            "max_cvr": max_v,
            "min_cvr": min_v,
        })
    age_gap.sort(key=lambda r: -r["spread"])

    return {
        "period": "2026.04.01 ~ 04.30",
        "total": {
            "cost": total_cost,
            "conv": total_conv,
            "click": total_click,
            "cpa": int(overall_cpa) if overall_cpa else None,
            "cvr": round(total_conv / total_click * 100, 2) if total_click else 0,
        },
        "age_kpi": age_kpi,
        "matrix": matrix,
        "top_by_age": top_by_age,
        "branch_cells": branch_cells,
        "age_gap": age_gap,
    }


def render_html(D):
    return TEMPLATE.replace("__DATA__", json.dumps(D, ensure_ascii=False))


# 템플릿은 별도 함수로 — 내용이 길어 다음 파일 작업으로 분리 가능
TEMPLATE = ""  # placeholder — 실제 템플릿은 build_template() 으로 주입

def build_template():
    """별도 HTML 템플릿 파일 사용"""
    tpl_path = ROOT / "output" / "analysis" / "_template_age_drilldown.html"
    return tpl_path.read_text(encoding="utf-8")


def main():
    df = load()
    D = build_data(df)
    global TEMPLATE
    TEMPLATE = build_template()
    html = render_html(D)
    OUT.write_text(html, encoding="utf-8")
    print(f"[OK] {OUT}")
    print(f"  rows: {len(df):,}, period: {D['period']}, branches: {len(D['branch_cells'])}, age_gap: {len(D['age_gap'])}")


if __name__ == "__main__":
    main()
