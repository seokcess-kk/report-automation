"""
Generate a concise April 2026 decision report.

Output:
  output/analysis/april_decision_report_202604.html
"""
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import analyze_comprehensive_202604 as base


ROOT = Path(__file__).parent
OUT = ROOT / "output" / "analysis" / "april_decision_report_202604.html"


def fmt_won(v: Any) -> str:
    if v is None:
        return "-"
    return f"{int(v):,}원"


def fmt_man(v: Any) -> str:
    if v is None:
        return "-"
    return f"{int(round(int(v) / 10000)):,}만원"


def fmt_pct(v: Any) -> str:
    if v is None:
        return "-"
    return f"{float(v):.2f}%"


def fmt_num(v: Any) -> str:
    if v is None:
        return "-"
    return f"{int(v):,}"


def e(v: Any) -> str:
    return escape(str(v), quote=True)


def cls_conf(conf: str) -> str:
    return {"high": "운영 판단", "mid": "테스트 가능", "low": "참고", "none": "표본 부족"}.get(conf, conf)


def row(cells: list[str], tag: str = "td") -> str:
    return "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"


def metric_card(label: str, value: str, sub: str = "", tone: str = "") -> str:
    return f"""
    <article class="metric {tone}">
      <div class="metric-label">{label}</div>
      <div class="metric-value">{value}</div>
      <div class="metric-sub">{sub}</div>
    </article>
    """


def decision_card(label: str, title: str, items: list[tuple[str, str]], tone: str = "") -> str:
    body = "".join(
        f"""
        <div class="kv">
          <div class="kv-label">{e(k)}</div>
          <div class="kv-value">{v}</div>
        </div>
        """
        for k, v in items
    )
    return f"""
    <article class="decision {tone}">
      <div class="decision-label">{label}</div>
      <h3>{title}</h3>
      <div class="kv-wrap">{body}</div>
    </article>
    """


def simple_table(headers: list[str], body_rows: list[list[str]], cls: str = "") -> str:
    head = row(headers, "th")
    body = "".join(row(r) for r in body_rows)
    return f'<div class="table-wrap {cls}"><table><thead>{head}</thead><tbody>{body}</tbody></table></div>'


def build_report(D: dict[str, Any]) -> str:
    total = D["total"]
    achievement = D["achievement"]
    target = D["targets"]
    senior = D["senior_med"]

    branch_rows = []
    for b in D["branch_kpi"]:
        status = "증액 후보" if b["cpa"] and b["cpa"] <= total["cpa"] and b["conv_pct"] >= 68 else "정비 우선"
        if b["branch"] in ["부평", "창원"]:
            status = "동결 후 정비"
        if b["branch"] in ["수원", "천안"]:
            status = "구조 정비"
        branch_rows.append([
            e(b["branch"]),
            fmt_man(b["cost"]),
            f'{fmt_num(b["conv"])} / {fmt_num(b["target_conv"])}',
            f'{float(b["conv_pct"]):.1f}%',
            fmt_won(b["cpa"]),
            fmt_pct(b["cvr"]),
            e(status),
        ])

    senior_branch_rows = []
    for b in senior["by_branch"]:
        decision = "소액 확대 테스트" if b["branch"] in ["수원", "부평", "천안"] else "확대 제외"
        if b["branch"] in ["서울", "대구"]:
            decision = "참고만"
        senior_branch_rows.append([
            e(b["branch"]),
            fmt_won(b["cost"]),
            fmt_num(b["click"]),
            fmt_num(b["conv"]),
            fmt_pct(b["cvr"]),
            fmt_won(b["cpa"]),
            e(decision),
        ])

    senior_creative_rows = []
    for c in senior["by_creative"]:
        senior_creative_rows.append([
            e(c["creative_name"]),
            e(c["hook"]),
            fmt_won(c["cost"]),
            fmt_num(c["click"]),
            fmt_num(c["conv"]),
            fmt_pct(c["cvr"]),
            fmt_won(c["cpa"]),
        ])

    matrix_lookup = {(m["creative_type"], m["age_group"]): m for m in D["matrix"]}
    ages = ["25-34", "35-44", "45-54", "≥55"]
    cts = ["진료셀프캠", "인플방문후기", "의료진정보", "진료QnA", "리얼모델후기"]
    matrix_rows = []
    for ct in cts:
        cells = [f"<b>{e(ct)}</b>"]
        for ag in ages:
            m = matrix_lookup.get((ct, ag))
            if not m or m["click"] < 30:
                cells.append('<span class="muted">표본 부족</span>')
                continue
            cells.append(
                f'<div class="cell-cvr">{fmt_pct(m["cvr"])}</div>'
                f'<div class="cell-sub">{fmt_num(m["conv"])}건 / {fmt_num(m["click"])}클릭</div>'
                f'<span class="conf {m["confidence"]}">{cls_conf(m["confidence"])}</span>'
            )
        matrix_rows.append(cells)

    age_rows = []
    for a in D["age_kpi"]:
        if a["age_group"] == "Unknown":
            continue
        action = "비중 확대" if a["age_group"] == "≥55" else "유지"
        if a["age_group"] == "25-34":
            action = "집행 제외"
        if a["age_group"] == "35-44":
            action = "지점별 선별"
        age_rows.append([
            e(a["age_group"]),
            fmt_man(a["cost"]),
            fmt_num(a["conv"]),
            fmt_won(a["cpa"]),
            fmt_pct(a["cvr"]),
            f'{float(a["share_cost"]):.1f}% / {float(a["share_conv"]):.1f}%',
            e(action),
        ])

    ct_rows = []
    for c in D["ct_kpi"]:
        role = {
            "진료셀프캠": "메인 전환 소재",
            "인플방문후기": "지역 매칭 소재",
            "의료진정보": "일부 지점 테스트",
            "진료QnA": "보류",
            "리얼모델후기": "보류",
        }.get(c["creative_type"], "-")
        ct_rows.append([
            e(c["creative_type"]),
            e(role),
            fmt_man(c["cost"]),
            fmt_num(c["conv"]),
            fmt_won(c["cpa"]),
            fmt_pct(c["cvr"]),
            e(c.get("best_age", "-")),
            e(c.get("best_branch", "-")),
        ])

    exec_rows = [
        ["서울", "≥55 진료셀프캠 확대", "신규 ≥55 진료셀프캠", "없음", "증액 후보"],
        ["대구", "진료셀프캠 중심 유지", "35-44·45-54 진료셀프캠", "인플방문후기 과다 집행", "증액 후보"],
        ["대전", "35-44 집중", "35-44 진료셀프캠·인플방문후기", "≥55 인플방문후기", "증액 후보"],
        ["일산", "균형 유지", "45-54·≥55 진료셀프캠/인플", "의료진정보 확대", "소폭 증액"],
        ["부평", "35-44 진료셀프캠 축소", "45-54 진료셀프캠, ≥55 의료진정보 테스트", "≥55 인플방문후기", "동결 후 정비"],
        ["수원", "25-34 집행 제외", "≥55 의료진정보 소액 테스트", "25-34 전체, ≥55 인플방문후기", "구조 정비"],
        ["천안", "45-54 정비", "35-44 진료셀프캠, ≥55 의료진정보 테스트", "45-54 전 유형", "구조 정비"],
        ["창원", "35-44 중심 유지", "35-44 진료셀프캠·인플방문후기", "≥55 인플방문후기", "동결 후 정비"],
    ]

    winner_rows = []
    for x in D["expand_top"][:8]:
        winner_rows.append([
            e(f'{x["branch"]} {x["age_group"]} {x["creative_type"]}'),
            fmt_man(x["cost"]),
            fmt_num(x["conv"]),
            fmt_pct(x["cvr"]),
            fmt_won(x["cpa"]),
            e(cls_conf(x["confidence"])),
            e(x["top_creative"]["creative_name"]),
        ])

    reduce_rows = []
    for x in D["reduce_top"][:8]:
        reduce_rows.append([
            e(f'{x["branch"]} {x["age_group"]} {x["creative_type"]}'),
            fmt_man(x["cost"]),
            fmt_num(x["conv"]),
            fmt_pct(x["cvr"]),
            fmt_won(x["cpa"]),
            e(cls_conf(x["confidence"])),
            e(x["leak_creative"]["creative_name"]),
        ])

    kpi_html = (
        metric_card("비용", fmt_won(total["cost"]), f'4월 예산 대비 {achievement["budget_pct"]}% 소진')
        + metric_card("전환", f'{fmt_num(total["conv"])}건', f'목표 {fmt_num(target["target_conv"])}건 대비 {achievement["conv_pct"]}%', "warn")
        + metric_card("CPA", fmt_won(total["cpa"]), f'목표 CPA {fmt_won(target["target_cpa"])} 대비 +{achievement["cpa_vs_target_pct"]}%', "warn")
        + metric_card("CVR", fmt_pct(total["cvr"]), f'{fmt_num(total["click"])} 클릭 기준', "small")
        + metric_card("CTR", fmt_pct(total["ctr"]), f'{fmt_num(total["imp"])} 노출 기준', "small")
    )

    summary_cards = (
        decision_card(
            "결론 1",
            "전사 평균보다 지점별 조합 차이가 더 중요합니다",
            [
                ("판단", "5월 운영은 전체 평균 최적화가 아니라 <b>지점별 승리 조합 확대</b>로 가야 합니다."),
                ("근거", f'서울·일산·대구·대전은 CPA가 평균 {fmt_won(total["cpa"])}보다 낮거나 유사하고, 성과가 좋은 조합이 명확합니다.'),
                ("실행", "서울·대구·대전은 증액 후보로 두고, 수원·천안은 먼저 구조 정비 후 재평가합니다."),
            ],
            "blue",
        )
        + decision_card(
            "결론 2",
            "55세 이상 의료진정보는 전 지점 확대 신호가 아닙니다",
            [
                ("판단", "<b>수원·부평·천안 한정 소액 테스트</b>가 적절합니다."),
                ("근거", f'전체 {fmt_num(senior["total"]["conv"])}건 중 9건이 3개 지점에 집중됐고, 일산·창원은 전환 0건입니다.'),
                ("기준", "1주 누적 CVR 7% 미만이면 원복하고, 7% 이상이면 클릭 100+까지 표본을 확대합니다."),
            ],
            "green",
        )
        + decision_card(
            "결론 3",
            "소재유형은 역할을 나눠야 합니다",
            [
                ("판단", "진료셀프캠은 메인, 인플방문후기는 지역 매칭, 의료진정보는 일부 지점 테스트로 분리합니다."),
                ("근거", "진료셀프캠은 전환 530건으로 가장 안정적이고, 인플방문후기는 대전·창원·일산처럼 맞는 지점이 따로 있습니다."),
                ("실행", "소재 예산을 유형 단위로 일괄 증감하지 말고 지점·나이대 조합 기준으로 조정합니다."),
            ],
            "purple",
        )
    )

    action_cards = "".join(
        decision_card(
            a["priority"],
            e(a["what"]).replace("차단", "집행 제외"),
            [
                ("대상", e(a["detail"]).replace("차단", "집행 제외")),
                ("운영", e(a["recovery"])),
                ("효과", e(a["effect"])),
                ("확인 기준", e(a["monitor"])),
            ],
            {"reduce": "red", "expand": "green", "test": "amber"}.get(a["kind"], ""),
        )
        for a in D["week1_actions"]
    )

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>다이어트한의원 2026년 4월 광고 운영 인사이트 리포트</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>
:root {{
  --bg:#f7f8fb; --paper:#fff; --ink:#111827; --sub:#4b5563; --muted:#8a94a6;
  --line:#e3e7ee; --soft:#f1f4f8; --blue:#2563eb; --green:#059669;
  --red:#dc2626; --amber:#d97706; --purple:#7c3aed;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; background:var(--bg); color:var(--ink);
  font-family:'Pretendard Variable',Pretendard,-apple-system,BlinkMacSystemFont,'Noto Sans KR',sans-serif;
  font-size:15.5px; line-height:1.72; letter-spacing:0;
}}
a {{ color:inherit; }}
.page {{ max-width:1160px; margin:0 auto; padding:34px 24px 56px; }}
.hero {{ background:var(--paper); border-bottom:1px solid var(--line); }}
.hero-inner {{ max-width:1160px; margin:0 auto; padding:42px 24px 30px; }}
.eyebrow {{ font-size:12px; font-weight:800; color:var(--blue); margin-bottom:10px; }}
h1 {{ font-size:32px; line-height:1.24; margin:0 0 10px; letter-spacing:0; }}
.lead {{ max-width:880px; color:var(--sub); font-size:16px; margin:0 0 18px; }}
.meta {{ display:flex; gap:8px; flex-wrap:wrap; }}
.pill {{ border:1px solid var(--line); background:#fff; border-radius:6px; padding:6px 10px; font-size:13px; color:var(--sub); }}
.note {{ margin-top:16px; max-width:900px; color:var(--sub); font-size:13.5px; background:#fffbeb; border:1px solid #fde68a; border-radius:8px; padding:12px 14px; }}
.toc {{ display:flex; gap:8px; flex-wrap:wrap; margin:22px 0 28px; }}
.toc a {{ text-decoration:none; padding:7px 10px; border:1px solid var(--line); background:#fff; border-radius:6px; color:var(--sub); font-size:13px; }}
.section {{ margin:48px 0 0; }}
.section-head {{ display:grid; gap:6px; margin-bottom:18px; }}
.section-kicker {{ font-size:12px; font-weight:800; color:var(--blue); }}
h2 {{ font-size:24px; line-height:1.34; margin:0; letter-spacing:0; }}
.section-desc {{ max-width:860px; color:var(--sub); margin:0; }}
.metric-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:1px; background:var(--line); border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
.metric {{ background:#fff; padding:18px 20px; min-height:112px; }}
.metric.small {{ min-height:92px; }}
.metric.warn {{ border-top:3px solid var(--amber); }}
.metric-label {{ color:var(--sub); font-size:12px; font-weight:800; margin-bottom:8px; }}
.metric-value {{ font-size:27px; line-height:1.18; font-weight:800; font-variant-numeric:tabular-nums; }}
.metric-sub {{ color:var(--sub); font-size:13px; margin-top:6px; }}
.card-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }}
.card-grid.two {{ grid-template-columns:repeat(2,1fr); }}
.decision {{ background:#fff; border:1px solid var(--line); border-top:4px solid var(--blue); border-radius:10px; padding:18px 20px; }}
.decision.green {{ border-top-color:var(--green); }}
.decision.red {{ border-top-color:var(--red); }}
.decision.amber {{ border-top-color:var(--amber); }}
.decision.purple {{ border-top-color:var(--purple); }}
.decision.blue {{ border-top-color:var(--blue); }}
.decision-label {{ color:var(--sub); font-size:12px; font-weight:800; margin-bottom:5px; }}
.decision h3 {{ margin:0 0 14px; font-size:17px; line-height:1.42; }}
.kv-wrap {{ display:grid; gap:9px; }}
.kv {{ display:grid; grid-template-columns:68px 1fr; gap:10px; padding-top:9px; border-top:1px dashed var(--line); }}
.kv:first-child {{ border-top:none; padding-top:0; }}
.kv-label {{ color:var(--muted); font-size:12px; font-weight:800; }}
.kv-value {{ color:var(--ink); font-size:14.5px; line-height:1.62; }}
.action-box {{ background:#ecfdf5; border:1px solid #a7f3d0; border-left:4px solid var(--green); border-radius:0 8px 8px 0; padding:15px 18px; margin-top:16px; }}
.action-box b {{ color:#065f46; }}
.table-wrap {{ background:#fff; border:1px solid var(--line); border-radius:10px; overflow:auto; }}
table {{ width:100%; border-collapse:collapse; min-width:760px; }}
th {{ background:var(--soft); color:var(--sub); text-align:left; font-size:12px; padding:10px 12px; white-space:nowrap; }}
td {{ border-top:1px solid var(--line); padding:11px 12px; vertical-align:top; font-size:14px; }}
td:nth-child(n+2), th:nth-child(n+2) {{ text-align:right; }}
td:last-child, th:last-child {{ text-align:left; }}
.matrix td, .matrix th {{ text-align:center; }}
.matrix td:first-child, .matrix th:first-child {{ text-align:left; }}
.cell-cvr {{ font-weight:800; font-variant-numeric:tabular-nums; }}
.cell-sub {{ color:var(--sub); font-size:12px; margin-top:2px; }}
.conf {{ display:inline-block; margin-top:5px; border-radius:4px; padding:2px 5px; font-size:11px; font-weight:800; }}
.conf.high {{ background:#d1fae5; color:#065f46; }}
.conf.mid {{ background:#dbeafe; color:#1e40af; }}
.conf.low {{ background:#fef3c7; color:#92400e; }}
.muted {{ color:var(--muted); }}
.callout {{ background:#fff; border:1px solid var(--line); border-left:4px solid var(--amber); border-radius:0 10px 10px 0; padding:18px 20px; margin-bottom:14px; }}
.callout-title {{ font-size:18px; font-weight:800; margin-bottom:10px; }}
.split {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
.appendix {{ color:var(--sub); font-size:13px; margin-top:10px; }}
@media(max-width:860px) {{
  .metric-grid,.card-grid,.card-grid.two,.split {{ grid-template-columns:1fr; }}
  h1 {{ font-size:27px; }}
  .page,.hero-inner {{ padding-left:18px; padding-right:18px; }}
}}
@media print {{
  body {{ background:#fff; }}
  .toc {{ display:none; }}
  .section {{ break-inside:avoid; }}
  .page {{ max-width:none; padding:20px; }}
}}
</style>
</head>
<body>
<header class="hero">
  <div class="hero-inner">
    <div class="eyebrow">TikTok 광고 운영 인사이트 · 2026년 4월</div>
    <h1>다이어트한의원 4월 광고 종합 리포트</h1>
    <p class="lead">나이대, 지점, 소재유형을 함께 보고 5월 운영에서 늘릴 조합과 줄일 조합을 정리했습니다. 숫자 나열보다 실행 판단을 먼저 볼 수 있도록 구성했습니다.</p>
    <div class="meta">
      <span class="pill">분석 기간: 2026-04-02 ~ 2026-04-30</span>
      <span class="pill">4/1 제외: 캠페인 셋팅 미실행</span>
      <span class="pill">Unknown 연령: 매트릭스·랭킹 제외</span>
      <span class="pill">데이터: TikTok Marketing API 재수집 기준</span>
    </div>
    <div class="note"><b>추정치 기준</b>: 회수 비용, 추가 전환, CPA 개선 가능성은 동일 예산과 4월 셀별 CVR이 유지된다는 가정의 운영 시뮬레이션입니다. 실제 결과는 5월 경쟁 강도와 소재 피로도에 따라 달라질 수 있습니다.</div>
  </div>
</header>

<main class="page">
  <nav class="toc">
    <a href="#summary">1. 한 페이지 요약</a>
    <a href="#actions">2. 5월 우선 실행</a>
    <a href="#senior-med">3. 55+ 의료진정보</a>
    <a href="#segments">4. 나이대·소재유형</a>
    <a href="#branches">5. 지점별 판단</a>
    <a href="#appendix">6. 근거표</a>
  </nav>

  <section class="section" id="summary">
    <div class="section-head">
      <div class="section-kicker">SUMMARY</div>
      <h2>한 페이지 요약</h2>
      <p class="section-desc">처음에는 운영 판단만 봅니다. 상세 수치는 뒤의 근거표에서 확인할 수 있게 분리했습니다.</p>
    </div>
    <div class="metric-grid">{kpi_html}</div>
    <div style="height:18px"></div>
    <div class="card-grid">{summary_cards}</div>
    <div class="action-box"><b>5월 운영 방향:</b> 전 지점 동일 운영을 중단하고, 서울·대구·대전은 성과 조합 확대, 수원·천안은 구조 정비, 수원·부평·천안은 55세 이상 의료진정보를 소액 테스트로 검증합니다.</div>
  </section>

  <section class="section" id="actions">
    <div class="section-head">
      <div class="section-kicker">FIRST WEEK ACTIONS</div>
      <h2>5월 첫 주 우선 실행 3가지</h2>
      <p class="section-desc">각 카드는 실행자가 바로 볼 수 있도록 대상, 운영, 효과, 확인 기준을 분리했습니다.</p>
    </div>
    <div class="card-grid">{action_cards}</div>
  </section>

  <section class="section" id="senior-med">
    <div class="section-head">
      <div class="section-kicker">DEEP DIVE</div>
      <h2>55세 이상 × 의료진정보 성과 해석</h2>
      <p class="section-desc">CVR {fmt_pct(senior["total"]["cvr"])}만 보면 좋아 보이지만, 실제로는 지점과 소재가 좁게 집중된 신호입니다.</p>
    </div>
    <div class="callout">
      <div class="callout-title">결론: 전 지점 확대가 아니라 수원·부평·천안 한정 테스트</div>
      <div class="kv-wrap">
        <div class="kv"><div class="kv-label">성과</div><div class="kv-value">비용 {fmt_won(senior["total"]["cost"])}, 클릭 {fmt_num(senior["total"]["click"])}건, 전환 {fmt_num(senior["total"]["conv"])}건, CVR {fmt_pct(senior["total"]["cvr"])}</div></div>
        <div class="kv"><div class="kv-label">집중</div><div class="kv-value">수원·부평·천안에서 전환 9건이 발생했습니다. 일산·창원은 전환 0건입니다.</div></div>
        <div class="kv"><div class="kv-label">소재</div><div class="kv-value">핵심 견인 소재는 <b>주사형비만치료제 10년은</b>입니다. 보조 신호로 <b>4050나잇살 이유는 여기에</b>가 확인됩니다.</div></div>
        <div class="kv"><div class="kv-label">기준</div><div class="kv-value">3개 지점에서만 각 8~10만원 수준으로 확대하고, 1주 누적 CVR 7% 미만이면 원복합니다.</div></div>
      </div>
    </div>
    <div class="split">
      {simple_table(["지점", "비용", "클릭", "전환", "CVR", "CPA", "판단"], senior_branch_rows)}
      {simple_table(["소재", "구분", "비용", "클릭", "전환", "CVR", "CPA"], senior_creative_rows)}
    </div>
  </section>

  <section class="section" id="segments">
    <div class="section-head">
      <div class="section-kicker">SEGMENT STRATEGY</div>
      <h2>나이대와 소재유형 운영 방향</h2>
      <p class="section-desc">나이대는 예산 방향을, 소재유형은 역할을 정합니다. CVR이 높아도 표본이 작으면 테스트로만 봅니다.</p>
    </div>
    <div class="split">
      {simple_table(["나이대", "비용", "전환", "CPA", "CVR", "비용/전환 비중", "5월 판단"], age_rows)}
      {simple_table(["소재유형", "역할", "비용", "전환", "CPA", "CVR", "강한 나이대", "강한 지점"], ct_rows)}
    </div>
    <div class="action-box"><b>운영 판단:</b> 25-34는 집행 제외, ≥55는 일부 확대, 35-44와 45-54는 지점별 성과 조합을 기준으로 유지·조정합니다. 소재는 진료셀프캠을 메인으로 두되 인플방문후기는 지역 매칭, 의료진정보는 테스트로 제한합니다.</div>
  </section>

  <section class="section" id="branches">
    <div class="section-head">
      <div class="section-kicker">BRANCH STRATEGY</div>
      <h2>지점별 5월 실행표</h2>
      <p class="section-desc">보고서의 최종 실행표입니다. 본문에서 발견한 55세 이상 의료진정보 테스트도 수원·부평·천안에 반영했습니다.</p>
    </div>
    {simple_table(["지점", "5월 핵심", "확대", "축소·제외", "우선순위"], exec_rows)}
    <div style="height:14px"></div>
    {simple_table(["지점", "비용", "전환/목표", "달성률", "CPA", "CVR", "판단"], branch_rows)}
  </section>

  <section class="section" id="appendix">
    <div class="section-head">
      <div class="section-kicker">EVIDENCE</div>
      <h2>핵심 근거표</h2>
      <p class="section-desc">본문 판단의 근거입니다. 세부 수치는 부록으로 두어 본문 흐름을 가볍게 유지했습니다.</p>
    </div>
    <h3>나이대 × 소재유형 CVR</h3>
    <p class="appendix">진한 수치보다 신뢰도 라벨을 함께 봐야 합니다. 운영 판단은 클릭 300건 이상, 테스트 가능은 100건 이상, 참고는 30건 이상입니다.</p>
    {simple_table(["소재유형 / 나이대", *ages], matrix_rows, "matrix")}
    <div style="height:24px"></div>
    <div class="split">
      <div>
        <h3>확대 후보 조합</h3>
        {simple_table(["조합", "비용", "전환", "CVR", "CPA", "신뢰도", "견인 소재"], winner_rows)}
      </div>
      <div>
        <h3>축소·정비 후보 조합</h3>
        {simple_table(["조합", "비용", "전환", "CVR", "CPA", "신뢰도", "원인 소재"], reduce_rows)}
      </div>
    </div>
  </section>
</main>
</body>
</html>
"""
    return html


def main() -> None:
    pa, age_df, meta = base.load()
    data = base.build(pa, age_df, meta)
    OUT.write_text(build_report(data), encoding="utf-8")
    print(f"[OK] {OUT}")


if __name__ == "__main__":
    main()
