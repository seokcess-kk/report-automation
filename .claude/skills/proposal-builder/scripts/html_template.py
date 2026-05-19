"""6월 운영 제안서 HTML 템플릿 — 컨설팅 deck 스타일 (v2)

설계 원칙 (codex 합의):
  - Answer First → Evidence → Action
  - Insight / Evidence / Action / Appendix 4등급 카드
  - 셀 배경 색칠 ✕ → 상태 배지 + 좌측 border
  - 표 위에 항상 1줄 해석문
  - 전환수·CPA를 Primary KPI로 최상위 노출
"""

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>다이트한의원 TikTok 6월 운영 제안서</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>
:root{
  --bg:#0a0a0c;--s1:#15151a;--s2:#1f1f25;--s3:#27272f;--bd:#2a2a32;--bd2:#3a3a45;
  --acc:#818cf8;--blue:#38bdf8;--pur:#a78bfa;--warn:#fbbf24;--red:#f87171;
  --tx:#f4f4f5;--tx2:#a1a1aa;--tx3:#6b6b75;
  --t1:#34d399;--t2:#38bdf8;--t3:#a78bfa;--t4:#f87171;
  --primary:#fbbf24;     /* Primary KPI 강조 */
  --funnel:#818cf8;      /* Funnel KPI 보조 */
  --insight:#818cf8;
  --evidence:#3a3a45;
  --action:#34d399;
  --appendix:#52525b;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--tx);
  font-family:'Pretendard Variable',Pretendard,-apple-system,BlinkMacSystemFont,system-ui,'Noto Sans KR',sans-serif;
  font-size:13px;line-height:1.65;letter-spacing:-0.003em;
  -webkit-font-smoothing:antialiased}
h1,h2,h3,h4{letter-spacing:-0.025em}

/* ==================== Cover & Nav ==================== */
.cover{background:var(--bg);border-bottom:1px solid var(--bd);padding:42px 32px 28px}
.cover-inner{max-width:1200px;margin:0 auto}
.cover-brand{font-size:11px;font-weight:800;letter-spacing:.12em;color:var(--acc);margin-bottom:14px;text-transform:uppercase}
.cover-title{font-size:32px;font-weight:900;letter-spacing:-.03em;margin-bottom:10px;line-height:1.2}
.cover-sub{font-size:14px;color:var(--tx2);margin-bottom:18px;line-height:1.5;font-weight:500}
.cover-meta{display:flex;gap:8px;flex-wrap:wrap}
.chip{background:var(--s2);border:1px solid var(--bd);border-radius:5px;padding:5px 12px;font-size:11px;color:var(--tx2);font-weight:500}
.chip span{color:var(--tx);font-weight:700}

nav{position:sticky;top:0;z-index:100;background:rgba(10,10,12,.96);backdrop-filter:blur(14px);border-bottom:1px solid var(--bd)}
.nav-inner{max-width:1200px;margin:0 auto;display:flex;overflow-x:auto;scrollbar-width:none}
.nav-inner::-webkit-scrollbar{display:none}
.tb{background:none;border:none;color:var(--tx2);cursor:pointer;font-family:inherit;font-size:13px;
  font-weight:600;padding:0 24px;height:52px;border-bottom:2px solid transparent;white-space:nowrap;transition:color .2s,border-color .2s;letter-spacing:-0.01em;
  display:flex;align-items:center;gap:8px}
.tb-num{font-size:10px;font-weight:800;color:var(--tx3);letter-spacing:.06em}
.tb:hover{color:var(--tx)}
.tb:hover .tb-num{color:var(--tx2)}
.tb.on{color:var(--tx);border-bottom-color:var(--acc);font-weight:700}
.tb.on .tb-num{color:var(--acc)}
.pg{display:none}
.pg.on{display:block}
.wrap{max-width:1200px;margin:0 auto;padding:32px 24px 56px}

/* ==================== Page Header Strip ==================== */
.page-hd{margin-bottom:32px;padding-bottom:24px;border-bottom:1px solid var(--bd)}
.page-hd-num{font-size:11px;font-weight:800;letter-spacing:.12em;color:var(--acc);text-transform:uppercase;margin-bottom:8px}
.page-hd-title{font-size:24px;font-weight:900;letter-spacing:-.025em;margin-bottom:12px;line-height:1.25}
.page-hd-msg{font-size:15px;color:var(--tx);font-weight:500;line-height:1.55;margin-bottom:14px;padding-left:14px;border-left:3px solid var(--acc)}
.page-hd-msg strong{color:var(--acc);font-weight:700}
.page-hd-meta{display:flex;gap:14px;flex-wrap:wrap;font-size:11px;color:var(--tx2)}
.page-hd-meta span strong{color:var(--tx);font-weight:600;margin-left:4px}

/* ==================== Section Header ==================== */
.sec{margin-bottom:36px}
.sec-hd{display:flex;align-items:baseline;gap:10px;margin-bottom:14px}
.sec-hd-num{font-size:11px;font-weight:800;color:var(--acc);letter-spacing:.05em;font-family:"DM Mono",monospace}
.sec-hd-title{font-size:16px;font-weight:800;letter-spacing:-.01em;color:var(--tx)}
.sec-hd-sub{font-size:12px;color:var(--tx2);font-weight:500;margin-left:auto}

.lead{font-size:13px;color:var(--tx);line-height:1.7;margin-bottom:14px;padding:12px 16px;
  background:rgba(129,140,248,.05);border-left:3px solid var(--acc);border-radius:0 6px 6px 0}
.lead strong{color:var(--acc);font-weight:700}

/* ==================== Card Hierarchy ==================== */
.insight-card{background:linear-gradient(135deg,rgba(129,140,248,.10),rgba(129,140,248,.02));
  border:1px solid rgba(129,140,248,.25);border-left:4px solid var(--insight);border-radius:8px;padding:18px 22px}
.evidence-card{background:var(--s1);border:1px solid var(--bd);border-radius:8px;padding:18px 22px}
.action-card{background:var(--s1);border:1px solid var(--bd);border-left:4px solid var(--action);border-radius:8px;padding:18px 22px}
.appendix-card{background:rgba(31,31,37,.4);border:1px solid var(--bd);border-radius:8px;padding:14px 18px;color:var(--tx2)}

.card-title{font-size:14px;font-weight:800;letter-spacing:-.01em;margin-bottom:6px;color:var(--tx)}
.card-sub{font-size:11px;color:var(--tx2);margin-bottom:14px;line-height:1.6;font-weight:500}

.g2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
@media(max-width:900px){.g2,.g3,.g4{grid-template-columns:1fr}}

/* ==================== Badges ==================== */
.bd{display:inline-flex;align-items:center;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:800;letter-spacing:.01em;line-height:1.4;text-transform:uppercase;font-family:inherit}
.bd-good{background:rgba(52,211,153,.14);color:var(--t1);border:1px solid rgba(52,211,153,.3)}
.bd-warn{background:rgba(251,191,36,.14);color:var(--warn);border:1px solid rgba(251,191,36,.3)}
.bd-bad {background:rgba(248,113,113,.14);color:var(--red);border:1px solid rgba(248,113,113,.3)}
.bd-new {background:rgba(167,139,250,.14);color:var(--pur);border:1px solid rgba(167,139,250,.3)}
.bd-mid {background:rgba(56,189,248,.10);color:var(--blue);border:1px solid rgba(56,189,248,.25)}
.bd-na  {background:rgba(82,82,91,.14);color:var(--tx3);border:1px solid var(--bd)}

.bd-A{background:rgba(248,113,113,.14);color:var(--red);border:1px solid rgba(248,113,113,.3)}
.bd-B{background:rgba(52,211,153,.14);color:var(--t1);border:1px solid rgba(52,211,153,.3)}
.bd-C{background:rgba(167,139,250,.14);color:var(--pur);border:1px solid rgba(167,139,250,.3)}

.bd-pri-high{background:rgba(248,113,113,.16);color:var(--red);border:1px solid rgba(248,113,113,.35)}
.bd-pri-mid {background:rgba(251,191,36,.14);color:var(--warn);border:1px solid rgba(251,191,36,.3)}
.bd-pri-low {background:rgba(52,211,153,.10);color:var(--t1);border:1px solid rgba(52,211,153,.25)}
.bd-pri-new {background:rgba(167,139,250,.14);color:var(--pur);border:1px solid rgba(167,139,250,.3)}

/* ==================== KPI Cards (P0) ==================== */
.kpi-primary-row{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:16px}
@media(max-width:700px){.kpi-primary-row{grid-template-columns:1fr}}
.kpi-primary{background:var(--s1);border:1px solid var(--bd);border-top:4px solid var(--primary);
  border-radius:8px;padding:20px 22px;position:relative}
.kpi-primary-lbl{font-size:10px;font-weight:800;letter-spacing:.12em;color:var(--primary);margin-bottom:8px;text-transform:uppercase}
.kpi-primary-val{font-size:30px;font-weight:900;font-family:"DM Mono",monospace;letter-spacing:-.025em;color:var(--tx);line-height:1.1}
.kpi-primary-unit{font-size:14px;font-weight:600;color:var(--tx2);margin-left:4px}
.kpi-primary-sub{font-size:11px;color:var(--tx2);margin-top:8px;line-height:1.5}
.kpi-primary-sub strong{color:var(--tx);font-weight:700}
.kpi-stretch{position:absolute;top:14px;right:18px;font-size:10px;font-weight:800;color:var(--warn);background:rgba(251,191,36,.10);padding:3px 8px;border-radius:4px;letter-spacing:.04em}

.kpi-funnel-row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
@media(max-width:700px){.kpi-funnel-row{grid-template-columns:1fr}}
.kpi-funnel{background:var(--s1);border:1px solid var(--bd);border-left:3px solid var(--funnel);
  border-radius:6px;padding:14px 16px}
.kpi-funnel-lbl{font-size:10px;font-weight:700;letter-spacing:.08em;color:var(--funnel);margin-bottom:6px;text-transform:uppercase}
.kpi-funnel-val{font-size:20px;font-weight:800;font-family:"DM Mono",monospace;letter-spacing:-.02em;color:var(--tx)}
.kpi-funnel-sub{font-size:10px;color:var(--tx2);margin-top:4px}

/* ==================== Judgement Cards (P0 3대 판단) ==================== */
.judg-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
@media(max-width:900px){.judg-grid{grid-template-columns:1fr}}
.judg{background:var(--s1);border:1px solid var(--bd);border-left:4px solid var(--cl);border-radius:8px;padding:18px 22px}
.judg.expand{--cl:var(--t1)}
.judg.improve{--cl:var(--red)}
.judg.stabilize{--cl:var(--pur)}
.judg-tag{display:inline-block;font-size:10px;font-weight:800;color:var(--cl);background:rgba(255,255,255,.04);padding:2px 8px;border-radius:4px;margin-bottom:10px;letter-spacing:.04em;text-transform:uppercase}
.judg-decision{font-size:15px;font-weight:800;color:var(--tx);margin-bottom:6px;letter-spacing:-.01em}
.judg-target{font-size:12px;color:var(--tx2);margin-bottom:10px;line-height:1.5}
.judg-target strong{color:var(--tx);font-weight:700}
.judg-row{display:flex;align-items:flex-start;gap:8px;font-size:11px;color:var(--tx2);line-height:1.55;margin-top:6px}
.judg-row-lbl{font-weight:700;color:var(--tx);min-width:48px}
.judg-impact{margin-top:12px;padding-top:10px;border-top:1px dashed var(--bd);font-size:11px;color:var(--cl);font-weight:700}
.judg-impact span{color:var(--tx2);font-weight:500;margin-left:4px}

/* ==================== Tables ==================== */
.tw{overflow-x:auto;border-radius:8px;border:1px solid var(--bd)}
table{width:100%;border-collapse:collapse;font-size:12px}
th{background:var(--s2);color:var(--tx2);font-weight:700;font-size:10px;letter-spacing:.05em;
  padding:11px 12px;text-align:left;border-bottom:1px solid var(--bd);white-space:nowrap;line-height:1.4;text-transform:uppercase}
td{padding:11px 12px;border-bottom:1px solid var(--bd);color:var(--tx);vertical-align:middle;white-space:nowrap;font-family:"DM Mono",monospace;font-size:12px}
td.lbl{font-family:inherit;color:var(--tx);font-size:12px;font-weight:700}
td.txt{font-family:inherit;color:var(--tx);font-size:11.5px;font-weight:500;white-space:normal;line-height:1.5}
td.muted{color:var(--tx2)}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(255,255,255,.015)}

/* Master matrix - 지점별 행 강조 */
.tbl-master tr td:first-child{font-weight:800}

/* ==================== Heatmap ==================== */
.hm-row{display:grid;align-items:stretch;border-bottom:1px solid var(--bd)}
.hm-row:last-child{border-bottom:none}
.hm-lbl-cell{padding:9px 12px;font-size:11px;color:var(--tx2);background:var(--s2);border-right:1px solid var(--bd);display:flex;align-items:center;font-weight:600}
.hm-val{padding:9px 6px;font-family:"DM Mono",monospace;font-size:11px;text-align:center;border-right:1px solid var(--bd);display:flex;align-items:center;justify-content:center}
.hm-val:last-child{border-right:none}
.h-good{background:rgba(52,211,153,.10);color:var(--t1);font-weight:700}
.h-mid{background:rgba(96,165,250,.05);color:var(--blue)}
.h-bad{background:rgba(248,113,113,.10);color:var(--red);font-weight:700}
.h-na{color:var(--tx3)}

/* ==================== Funnel Cell (P3 매트릭스) ==================== */
.fcell{padding:8px 10px;border-radius:5px;background:rgba(255,255,255,.015);border:1px solid var(--bd);
  font-size:11px;line-height:1.5;min-width:140px;white-space:normal;vertical-align:top}
.fcell.good{background:transparent;border-color:transparent;opacity:.55}
.fcell.warn{background:rgba(251,191,36,.04);border-color:rgba(251,191,36,.2)}
.fcell.bad{background:rgba(248,113,113,.05);border-color:rgba(248,113,113,.25)}
.fcell-row{display:flex;align-items:center;gap:5px;margin-bottom:3px}
.fcell-action{color:var(--tx);font-weight:600;font-size:11px;line-height:1.45;margin:4px 0}
.fcell.good .fcell-action{color:var(--tx2);font-weight:500}
.fcell-role{color:var(--tx2);font-size:10px;line-height:1.4;margin-bottom:3px}
.fcell-role strong{color:var(--pur);font-weight:700}
.fcell-kpi{color:var(--tx3);font-size:10px;font-family:"DM Mono",monospace;letter-spacing:-.01em}

/* ==================== Quadrant chart container ==================== */
.quad-wrap{position:relative;height:360px;background:var(--s1);border:1px solid var(--bd);border-radius:8px;padding:14px}
.quad-labels{position:absolute;inset:14px;pointer-events:none;font-size:10px;color:var(--tx3);font-weight:700;letter-spacing:.04em;text-transform:uppercase}
.quad-lbl{position:absolute}
.quad-lbl.tl{top:4px;left:8px;color:var(--t1)}
.quad-lbl.tr{top:4px;right:8px;color:var(--red)}
.quad-lbl.bl{bottom:4px;left:8px;color:var(--blue)}
.quad-lbl.br{bottom:4px;right:8px;color:var(--warn)}

/* ==================== Branch Cards (지점별 카드) ==================== */
.bp{background:var(--s1);border:1px solid var(--bd);border-left:4px solid var(--cl);
  border-radius:8px;padding:18px 22px;margin-bottom:12px}
.bp.A{--cl:var(--red)}
.bp.B{--cl:var(--t1)}
.bp.C{--cl:var(--pur)}
.bp-hdr{display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap}
.bp-name{font-size:17px;font-weight:800;letter-spacing:-.015em}
.bp-meta{font-size:11px;color:var(--tx2);font-family:"DM Mono",monospace;margin-left:auto}

.bp-section{margin-top:12px}
.bp-section-lbl{font-size:10px;font-weight:800;letter-spacing:.06em;color:var(--tx2);margin-bottom:6px;text-transform:uppercase}

.gridline{height:1px;background:var(--bd);margin:12px 0}

/* ==================== Recommendations (유지/확대/신규) ==================== */
.reco-rail{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:8px}
@media(max-width:800px){.reco-rail{grid-template-columns:1fr}}
.reco-col{background:var(--s2);border:1px solid var(--bd);border-radius:6px;padding:10px 12px}
.reco-col.keep{border-top:2px solid var(--t1)}
.reco-col.expand{border-top:2px solid var(--warn)}
.reco-col.new{border-top:2px solid var(--acc)}
.reco-col-lbl{font-size:10px;font-weight:800;color:var(--tx);margin-bottom:6px;letter-spacing:.04em;text-transform:uppercase}
.reco-col.keep .reco-col-lbl{color:var(--t1)}
.reco-col.expand .reco-col-lbl{color:var(--warn)}
.reco-col.new .reco-col-lbl{color:var(--acc)}
.reco-item{font-size:11px;color:var(--tx);line-height:1.45;padding:5px 0;border-bottom:1px dashed var(--bd)}
.reco-item:last-child{border-bottom:none}
.reco-item-meta{font-size:10px;color:var(--tx2);font-family:"DM Mono",monospace;margin-top:2px}

/* ==================== TOP3 Cards (P3 4.3) ==================== */
.top3-rail{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:10px}
@media(max-width:800px){.top3-rail{grid-template-columns:1fr}}
.top3-col{background:var(--s1);border:1px solid var(--bd);border-radius:6px;padding:14px 16px}
.top3-col-lbl{font-size:11px;font-weight:800;letter-spacing:.04em;margin-bottom:10px;text-transform:uppercase}
.top3-col.cpm .top3-col-lbl{color:var(--red)}
.top3-col.ctr .top3-col-lbl{color:var(--blue)}
.top3-col.cvr .top3-col-lbl{color:var(--t1)}
.t3-card{background:var(--s2);border-radius:5px;padding:10px 12px;margin-bottom:6px;position:relative}
.t3-card:last-child{margin-bottom:0}
.t3-rank{position:absolute;top:6px;right:10px;font-size:10px;font-weight:900;color:var(--tx3);font-family:"DM Mono",monospace}
.t3-name{font-size:11px;color:var(--tx);font-weight:600;margin-bottom:6px;line-height:1.45;padding-right:26px;word-break:keep-all}
.t3-val{font-size:16px;font-weight:900;font-family:"DM Mono",monospace;color:var(--acc);letter-spacing:-.02em}
.t3-sub{font-size:10px;color:var(--tx2);margin-top:3px;font-family:"DM Mono",monospace;line-height:1.4}
.t3-tag{display:inline-block;font-size:9px;font-weight:800;padding:1px 5px;border-radius:3px;background:rgba(251,146,60,.15);color:var(--warn);margin-left:4px}

/* ==================== Appendix ==================== */
.appendix-stack{display:flex;flex-direction:column;gap:8px}
.appx{background:var(--s1);border:1px solid var(--bd);border-radius:6px;overflow:hidden}
.appx[open]{background:rgba(31,31,37,.55)}
.appx summary{cursor:pointer;padding:12px 18px;font-size:12px;font-weight:700;color:var(--tx2);list-style:none;
  display:flex;align-items:center;justify-content:space-between;transition:background .15s}
.appx summary:hover{background:var(--s2);color:var(--tx)}
.appx summary::-webkit-details-marker{display:none}
.appx summary::after{content:"▼";font-size:10px;color:var(--tx3);transition:transform .2s;margin-left:8px}
.appx[open] summary::after{transform:rotate(180deg)}
.appx-num{font-size:10px;font-weight:800;color:var(--acc);font-family:"DM Mono",monospace;margin-right:6px}
.appx-body{padding:16px 20px;border-top:1px solid var(--bd)}

/* ==================== Misc ==================== */
.muted{color:var(--tx2);font-size:11px;font-weight:500}
.num{font-family:"DM Mono",monospace}
.delta-up{color:var(--t1);font-weight:700}
.delta-down{color:var(--red);font-weight:700}
.delta-neutral{color:var(--tx2);font-weight:700}
.gap-positive{color:var(--t1)}
.gap-negative{color:var(--red)}

/* 4-week roadmap mini */
.rm-row{display:grid;grid-template-columns:80px 1fr;gap:14px;padding:10px 14px;background:var(--s2);border-radius:6px;margin-bottom:6px;align-items:start}
.rm-week{font-size:11px;font-weight:800;color:var(--acc);font-family:"DM Mono",monospace}
.rm-body{font-size:11px;color:var(--tx);line-height:1.6}
.rm-body strong{color:var(--tx);font-weight:700}

::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-thumb{background:var(--bd2);border-radius:3px}
</style>
</head>
<body>

<div class="cover"><div class="cover-inner">
  <div class="cover-brand">다이트한의원 · TikTok Ads · 2026년 6월 운영 제안</div>
  <h1 class="cover-title">2026년 6월 TikTok 운영 방향 보고</h1>
  <div class="cover-sub">전 기간 운영 데이터 진단을 바탕으로 6월 목표·액션·타겟팅·콘텐츠 실행안을 정리하여 보고드립니다.</div>
  <div class="cover-meta" id="cover-meta"></div>
</div></div>

<nav><div class="nav-inner">
  <button class="tb on" data-tab="exec"><span class="tb-num">01</span>Executive Summary</button>
  <button class="tb" data-tab="diag"><span class="tb-num">02</span>성과 진단</button>
  <button class="tb" data-tab="plan"><span class="tb-num">03</span>6월 목표·액션</button>
  <button class="tb" data-tab="exec_plan"><span class="tb-num">04</span>타겟팅·콘텐츠 실행안</button>
  <button class="tb" data-tab="addon"><span class="tb-num">05</span>애드온 판단</button>
</div></nav>

<!-- ========================= 01 Executive Summary ========================= -->
<div id="pg-exec" class="pg on"><div class="wrap">
  <div class="page-hd">
    <div class="page-hd-num">01 · Executive Summary</div>
    <h2 class="page-hd-title">6월 운영 방향 요약</h2>
    <div class="page-hd-msg">6월 다이트한의원 TikTok 운영은 지점별 퍼널 병목에 따라 <strong style="color:var(--red)">A 효율 개선</strong> · <strong style="color:var(--t1)">B 예산 확대</strong> · <strong style="color:var(--pur)">C 신규 안정화</strong> 세 방향으로 분리 적용을 권고드립니다. 전환 목표는 <strong style="color:var(--primary)">762건(Stretch 822건)</strong>으로 설정하였습니다.</div>
    <div class="page-hd-meta">
      <span>분석 기간 <strong id="meta-period"></strong></span>
      <span>대상 <strong id="meta-branches"></strong></span>
      <span>누적 KPI 베이스라인 <strong>전 기간 2~5월</strong> · 베스트월 비교 <strong>2~4월</strong></span>
      <span>생성 <strong id="meta-generated"></strong></span>
    </div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">1.1</span><span class="sec-hd-title">6월 운영 목표</span><span class="sec-hd-sub">Primary KPI · 비즈니스 결과</span></div>
    <div class="lead">전환수 <strong>762건</strong>을 base target, <strong>822건</strong>을 stretch target으로 설정하였습니다. 평균 CPA는 <strong>27,278원</strong>을 가드레일로 운영하겠습니다. 모든 수치는 지점별 베스트월(2~4월) 재달성을 기준으로 산정된 값입니다.</div>
    <div class="kpi-primary-row" id="kpi-primary"></div>
    <div class="sec-hd" style="margin-top:18px"><span class="sec-hd-num">1.2</span><span class="sec-hd-title">목표 달성 조건</span><span class="sec-hd-sub">Funnel KPI · 조정 레버</span></div>
    <div class="kpi-funnel-row" id="kpi-funnel"></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">1.3</span><span class="sec-hd-title">지점 그룹별 운영 방향</span></div>
    <div class="lead">9개 지점을 효율 등급·전환 기여도·데이터 충분도로 평가하여 세 그룹으로 분류하였습니다. 그룹별 운영 강도와 중단 조건을 다음과 같이 적용하겠습니다.</div>
    <div class="judg-grid" id="judg-cards"></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">1.4</span><span class="sec-hd-title">지점별 전환 기여 분포</span><span class="sec-hd-sub">전 기간 누적 · 2~5월</span></div>
    <div class="lead" id="overview-lead">막대 길이는 누적 전환수, 색상은 CPA 효율 등급(전 지점 평균 ±15%)을 나타냅니다.</div>
    <div class="evidence-card"><div style="position:relative;height:300px"><canvas id="branchConvChart"></canvas></div></div>
  </div>
</div></div>

<!-- ========================= 02 성과 진단 ========================= -->
<div id="pg-diag" class="pg"><div class="wrap">
  <div class="page-hd">
    <div class="page-hd-num">02 · Performance Diagnosis</div>
    <h2 class="page-hd-title">지점별 퍼널 병목 진단</h2>
    <div class="page-hd-msg">전 기간 운영 데이터를 진단한 결과, 9개 지점은 운영 패턴상 세 그룹으로 분류됩니다. 효율 부진 지점은 CVR 병목 해소가 우선이며, 확대 후보 지점은 CPM 가드라인 유지가 필요한 것으로 판단됩니다.</div>
    <div class="page-hd-meta">
      <span>진단 기준 <strong>전 지점 평균 대비 ±10% / ±20%</strong></span>
      <span>비교 대상 <strong>전 기간 2~5월 누적</strong></span>
    </div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">2.1</span><span class="sec-hd-title">지점×퍼널 진단 매트릭스</span></div>
    <div class="lead" id="diag-lead-21"></div>
    <div class="evidence-card" style="padding:0;overflow:hidden"><div class="tw"><table id="diag-matrix"></table></div></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">2.2</span><span class="sec-hd-title">전환량 × CPA 사분면</span></div>
    <div class="lead">가로축은 평균 CPA, 세로축은 누적 전환수, 버블 크기는 비용 규모를 나타냅니다. 좌상은 확대 후보, 우상은 효율 리스크, 좌하는 잠재 후보, 우하는 재진단 필요 영역입니다.</div>
    <div class="evidence-card">
      <div class="quad-wrap">
        <div class="quad-labels">
          <div class="quad-lbl tl">↖ 확대 후보</div>
          <div class="quad-lbl tr">↗ 효율 리스크</div>
          <div class="quad-lbl bl">↙ 잠재 후보</div>
          <div class="quad-lbl br">↘ 재진단</div>
        </div>
        <canvas id="quadChart"></canvas>
      </div>
    </div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">2.3</span><span class="sec-hd-title">월별 × 지점별 퍼널 히트맵</span></div>
    <div class="lead">셀 색상은 해당 지점이 다른 월 대비 상대적으로 어떠한지를 보여줍니다. 5월은 운영 중단으로 발생한 부분 데이터이므로 시점 비교에는 사용하지 않으며, 참고 표기만 유지합니다.</div>
    <div class="evidence-card">
      <div style="margin-bottom:14px">
        <div style="font-size:11px;font-weight:700;color:var(--tx2);margin-bottom:6px">CPM (원) · 낮을수록 우수</div>
        <div id="hm-cpm" class="tw"></div>
      </div>
      <div style="margin-bottom:14px">
        <div style="font-size:11px;font-weight:700;color:var(--tx2);margin-bottom:6px">CTR (%) · 높을수록 우수</div>
        <div id="hm-ctr" class="tw"></div>
      </div>
      <div>
        <div style="font-size:11px;font-weight:700;color:var(--tx2);margin-bottom:6px">CVR (%) · 높을수록 우수</div>
        <div id="hm-cvr" class="tw"></div>
      </div>
    </div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">2.4</span><span class="sec-hd-title">비용·예산 효율 분석</span></div>
    <div class="lead" id="budget-lead-24"></div>
    <div class="g2" style="margin-bottom:14px">
      <div class="evidence-card">
        <div class="card-title">월별 총비용 · 전환 · CPA 추이</div>
        <div class="card-sub">5월은 운영 중단 부분월로 색상을 달리하여 표시하였습니다.</div>
        <div style="position:relative;height:260px"><canvas id="monthlyBudgetChart"></canvas></div>
      </div>
      <div class="evidence-card">
        <div class="card-title">지점별 100만원당 전환수</div>
        <div class="card-sub">막대가 길수록 동일 비용 대비 전환 회수가 우수함을 의미합니다.</div>
        <div style="position:relative;height:260px"><canvas id="convPerMillionChart"></canvas></div>
      </div>
    </div>
    <div class="evidence-card" style="padding:0;overflow:hidden"><div class="tw"><table id="budget-efficiency-tbl"></table></div></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">2.A</span><span class="sec-hd-title">Appendix A · 진단 근거 자료</span></div>
    <div class="appendix-stack">
      <details class="appx">
        <summary><span><span class="appx-num">A.1</span>지점별 누적 KPI 요약 (전환·비중·CPA·운영일수)</span></summary>
        <div class="appx-body"><div class="tw"><table id="conv-summary-tbl"></table></div></div>
      </details>
      <details class="appx">
        <summary><span><span class="appx-num">A.2</span>전 지점 평균과 지점별 비교</span></summary>
        <div class="appx-body">
          <div class="evidence-card" style="margin-bottom:10px;padding:14px 18px"><table id="root-peer-avg-tbl"></table></div>
          <div class="tw"><table id="root-comparison-tbl"></table></div>
        </div>
      </details>
      <details class="appx">
        <summary><span><span class="appx-num">A.3</span>지점별 약점 진단 및 추세 가드레일 (정상월 2~4월 기준)</span></summary>
        <div class="appx-body"><div id="root-diag-list"></div></div>
      </details>
      <details class="appx">
        <summary><span><span class="appx-num">A.4</span>지점별 월별 전환수 추이</span></summary>
        <div class="appx-body"><div class="tw"><table id="conv-monthly-tbl"></table></div></div>
      </details>
    </div>
  </div>
</div></div>

<!-- ========================= 03 6월 목표·액션 ========================= -->
<div id="pg-plan" class="pg"><div class="wrap">
  <div class="page-hd">
    <div class="page-hd-num">03 · June Targets & Action Plan</div>
    <h2 class="page-hd-title">6월 목표 · 액션 플랜</h2>
    <div class="page-hd-msg">퍼널 병목 원인이 지점마다 다르므로 처방 또한 분리하여 적용을 권고드립니다. 단순 예산 증액으로는 6월 목표 달성이 어려우며, CPM · CTR · CVR 각각의 원인에 맞는 실행 액션이 동반되어야 합니다.</div>
    <div class="page-hd-meta">
      <span>목표 산정 <strong>지점별 베스트월 (정상월 2~4월) 재달성</strong></span>
      <span>현재값 기준 <strong>전 기간 2~5월 누적</strong></span>
    </div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">3.1</span><span class="sec-hd-title">지점별 6월 목표 요약</span></div>
    <div class="lead" id="plan-lead-31"></div>
    <div class="evidence-card" style="padding:0;overflow:hidden"><div class="tw"><table id="plan-master-tbl" class="tbl-master"></table></div></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">3.2</span><span class="sec-hd-title">퍼널별 원인 분석 및 실행 액션</span></div>
    <div class="lead">CPM · CTR · CVR 각각에 대해 본 데이터에서 관측된 시그널을 바탕으로 원인을 해석하고, 6월에 즉시 실행할 운영 액션과 검증 KPI를 정리하였습니다.</div>
    <div class="g3" id="funnel-action-cards"></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">3.3</span><span class="sec-hd-title">지점별 운영 처방 카드</span></div>
    <div class="lead">3.1이 목표 수치 비교라면, 본 섹션은 지점별 6월 운영 지시서입니다. 그룹 판단 · 핵심 병목 · 운영 액션 · 검증 KPI · 중단 조건을 한 카드로 정리하였습니다.</div>
    <div id="branch-action-cards"></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">3.4</span><span class="sec-hd-title">6월 예산 시나리오</span></div>
    <div class="lead" id="budget-lead-34"></div>
    <div class="g3" style="margin-bottom:16px" id="budget-scenarios"></div>
    <div class="evidence-card" style="padding:0;overflow:hidden"><div class="tw"><table id="budget-rec-tbl"></table></div></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">3.5</span><span class="sec-hd-title">A/B 테스트 운영 가이드</span></div>
    <div class="lead">TikTok Ads는 예산이 캠페인 또는 광고 그룹(지점) 단위로 설정되며, 소재는 광고 단위 ON/OFF만 가능합니다. 따라서 A/B 검증은 <strong>광고 그룹을 복제하여 두 그룹에서 1개 변수만 다르게 운영</strong>하는 방식을 권고드립니다.</div>
    <div class="g3" style="margin-bottom:14px">
      <div class="action-card">
        <div class="card-title" style="font-size:14px;color:var(--action)">진행 방식</div>
        <div style="font-size:11px;color:var(--tx);line-height:1.65;margin-top:8px">
          ① 효율 양호 지점의 광고 그룹을 복제하여 두 그룹으로 분리합니다.<br>
          ② 한 번에 <strong>1개 변수만</strong> 변경합니다 (소재 묶음 또는 입찰 전략).<br>
          ③ 다른 변수는 모두 동일하게 통제합니다 (예산 · 타겟 · 시간대).<br>
          ④ 학습 종료 후 두 그룹의 결과를 비교하여 우세 변수를 채택합니다.
        </div>
      </div>
      <div class="action-card">
        <div class="card-title" style="font-size:14px;color:var(--action)">학습 조건</div>
        <div style="font-size:11px;color:var(--tx);line-height:1.65;margin-top:8px">
          · 학습 기간 <strong>최소 2주</strong> 이상 확보 (알고리즘 안정화 목적)<br>
          · 그룹별 누적 <strong>전환 30건 이상</strong> 확보 시 유의미한 비교 가능<br>
          · 미달 시 추세 참고에 한정하고 확정 판단은 보류합니다.<br>
          · 학습 모수 부족 시 그룹 통합 후 재시작을 권고드립니다.
        </div>
      </div>
      <div class="action-card">
        <div class="card-title" style="font-size:14px;color:var(--action)">우선 추천 지점 및 변수</div>
        <div style="font-size:11px;color:var(--tx);line-height:1.65;margin-top:8px">
          <strong>지점 후보</strong> · <span id="ab-priority-branches">효율 양호 및 학습 모수 충분 지점</span><br>
          <strong>검증 변수 후보</strong><br>
          ① 소재 묶음 A(후기형) vs B(상담전환형)<br>
          ② 입찰 전략 (최대 전환 vs 비용 한도)<br>
          ③ 노출 시간대 (전일 vs 피크 회피)
        </div>
      </div>
    </div>
    <div class="appendix-card" style="margin-top:8px">
      <strong style="color:var(--warn)">유의 사항.</strong> 동일 지역 풀을 두 그룹이 나누어 가지므로 학습 속도가 느려질 가능성이 있습니다. 학습 모수 부족이 예상되는 경우 (a) 같은 광고 그룹에서 기간을 분리하는 순차 A/B, (b) 그룹이 유사한 지점 간 비교 운영을 대안으로 고려할 수 있습니다. 다만 (b)는 외부 변수 통제가 어려운 점을 함께 고려해 주시기 바랍니다.
    </div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">3.B</span><span class="sec-hd-title">Appendix B · 운영 보조 자료</span></div>
    <div class="lead" style="margin-bottom:14px">본문 의사결정의 근거가 되는 운영 자료입니다. 주차별 실행 일정, 요일별 운영 가이드, 클라이언트 측 점검 요청 항목을 포함합니다.</div>
    <div class="appendix-stack">
      <details class="appx">
        <summary><span><span class="appx-num">B.1</span>6월 주차별 실행 로드맵</span></summary>
        <div class="appx-body">
          <div class="rm-row"><div class="rm-week">1주차<br>06/01-07</div><div class="rm-body"><strong>효율 부진 지점 진단 착수.</strong> 수원 · 창원 · 천안의 CVR 원인을 점검하겠습니다 (소재 ↔ 랜딩 hero "9만원" 정합성, 5단계 폼 이탈률 확인). CPA가 평균 대비 높은 지점은 광고 그룹 예산 증액을 보류하고, CVR 회복 이후 단계적으로 증액합니다. 부산은 학습 기간 안정화 모니터링을 진행합니다.</div></div>
          <div class="rm-row"><div class="rm-week">2주차<br>06/08-14</div><div class="rm-body"><strong>효율 양호 지점 확대 및 CPM 가드라인 적용.</strong> 서울 · 일산 · 대구 · 대전 광고 그룹 예산을 +5~10% 점진 증액합니다. CPM이 지속 상승 중인 부평 · 대구 · 창원은 신규 광고 그룹 복제(OR 분리)로 노출 효율을 함께 확보합니다. 1주차 부진 지점의 회복 추이도 함께 평가하겠습니다.</div></div>
          <div class="rm-row"><div class="rm-week">3주차<br>06/15-21</div><div class="rm-body"><strong>콘텐츠 다양화 및 신규 소재 투입.</strong> P3에서 정의한 신규 도입 소재를 지점별로 광고 단위 ON 처리합니다. 전환수 · CPA 우수 소재는 동일 지점에서 확대 운영하고, OFF된 우수 소재 중 재활용 후보를 검토하겠습니다.</div></div>
          <div class="rm-row"><div class="rm-week">4주차<br>06/22-30</div><div class="rm-body"><strong>중간 점검 및 7월 방향 정리.</strong> 검증 KPI를 기준으로 지점별 회복 여부를 확인합니다. 6월 운영 결과를 토대로 7월 운영 방향을 조정하겠습니다. 애드온 전면 확대는 통제된 A/B 결과 확인 후 결정합니다.</div></div>
        </div>
      </details>
      <details class="appx">
        <summary><span><span class="appx-num">B.2</span>요일별 성과 및 예산 조정 가이드</span></summary>
        <div class="appx-body">
          <div class="lead" style="margin-bottom:10px">정상 운영 월(2~4월) 요일별 성과를 기준으로 예산 집중·축소 후보를 정리하였습니다. 시간대 데이터는 원천 파일에 포함되지 않으므로, 추가 확인이 필요한 경우 TikTok Ads Manager 시간대 리포트를 별도 점검해 주시기 바랍니다.</div>
          <div class="tw"><table id="weekday-action-tbl"></table></div>
        </div>
      </details>
      <details class="appx">
        <summary><span><span class="appx-num">B.3</span>클라이언트 확인 요청 사항 · 병원 내부 컨트롤 영역</span></summary>
        <div class="appx-body">
          <div class="lead" style="margin-bottom:14px">아래 항목은 광고 운영 단계에서 직접 조정할 수 없는 병원 내부 영역에 해당합니다. CVR 해석의 정확도 향상을 위해 클라이언트 측 점검을 요청드립니다. 랜딩페이지는 전 지점 동일 포맷으로 운영되고 있어 지점별 차이 점검은 제외하였습니다.</div>
          <div class="g2">
            <div class="appendix-card"><div class="card-title" style="color:var(--acc);font-size:12px">전환 채널 분리 확인</div><ul style="font-size:11px;color:var(--tx2);line-height:1.8;padding-left:16px;margin-top:6px"><li>광고 유입 후 전화·카카오톡·5단계 폼 전환 비율 (지점별)</li><li>전 기간 채널 구성비 변화</li><li>콜트래커 정상 작동 여부</li></ul></div>
            <div class="appendix-card"><div class="card-title" style="color:var(--acc);font-size:12px">상담 응대 품질</div><ul style="font-size:11px;color:var(--tx2);line-height:1.8;padding-left:16px;margin-top:6px"><li>지점별 상담 응답률·부재콜 비율</li><li>응대 가능 시간대 vs 광고 노출 시간 매치</li><li>최근 인력·응대 정책 변화</li></ul></div>
            <div class="appendix-card"><div class="card-title" style="color:var(--acc);font-size:12px">랜딩 공통 점검 (전 지점)</div><ul style="font-size:11px;color:var(--tx2);line-height:1.8;padding-left:16px;margin-top:6px"><li>소재 ↔ 랜딩 hero("첫 달 9만원") 톤 정합성 (소재가 후기형/할인형/의료진형 중 무엇이든 hero와 호응하는가)</li><li>5단계 폼(부위→기대효과→연령→연락처→동의) 단계별 이탈률 — 어디서 끊기는가</li><li>지점명이 하단에 있어 사용자 인지 어려움 — 상단 지점 chip 추가 검토</li></ul></div>
            <div class="appendix-card"><div class="card-title" style="color:var(--acc);font-size:12px">예약 → 내원 전환</div><ul style="font-size:11px;color:var(--tx2);line-height:1.8;padding-left:16px;margin-top:6px"><li>예약 확정률·노쇼 비율 (지점별)</li><li>채널별 예약 확정률 차이</li><li>부산(신규)의 예약 처리 안정성</li></ul></div>
          </div>
        </div>
      </details>
    </div>
  </div>
</div></div>

<!-- ========================= 04 타겟팅·콘텐츠 실행안 ========================= -->
<div id="pg-exec_plan" class="pg"><div class="wrap">
  <div class="page-hd">
    <div class="page-hd-num">04 · Targeting & Content Execution Plan</div>
    <h2 class="page-hd-title">타겟팅 · 콘텐츠 실행안</h2>
    <div class="page-hd-msg">지점별 약점 퍼널을 보완할 수 있도록 타겟팅 방향과 소재 역할을 매트릭스로 정리하였습니다. 단순한 "추천 소재 1개"가 아니라, 퍼널 병목에 기반한 소재 역할과 검증된 소재 후보를 함께 제시드립니다.</div>
    <div class="page-hd-meta">
      <span>실행 단위 <strong>지점 × 퍼널 (9 × 3)</strong></span>
      <span>소재 역할 분류 <strong>7종</strong></span>
    </div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">4.1</span><span class="sec-hd-title">지점 × 퍼널 실행 매트릭스</span></div>
    <div class="lead" id="ep-lead-41"></div>
    <div class="evidence-card" style="padding:0;overflow:hidden"><div class="tw"><table id="exec-matrix"></table></div></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">4.2</span><span class="sec-hd-title">지점별 콘텐츠 큐레이션</span></div>
    <div class="lead">4.1이 처방이라면, 본 섹션은 실제 투입할 소재 묶음입니다. <span style="color:var(--t1)">●</span> <strong>유지</strong>는 본인 지점에서 이미 우수한 소재, <span style="color:var(--warn)">●</span> <strong>확대</strong>는 본인 지점에서 운영 중이지만 타 지점에서 더 좋은 성과를 보인 소재, <span style="color:var(--acc)">●</span> <strong>신규 도입</strong>은 본인 지점에는 미운영이나 타 지점에서 검증된 소재를 의미합니다.</div>
    <div id="content-curation"></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">4.3</span><span class="sec-hd-title">퍼널별 우수 콘텐츠 TOP 3</span></div>
    <div class="lead">CPM · CTR · CVR 세 퍼널 기준의 우수 콘텐츠 TOP 3을 지점별로 정리하였습니다. 각 카드에는 전환수 · CPA · 운영일수를 보조 정보로 함께 표기하였습니다.</div>
    <details class="appx" open>
      <summary><span><span class="appx-num">4.3</span>지점별 TOP 3 카드 펼쳐 보기</span></summary>
      <div class="appx-body"><div id="top-by-branch"></div></div>
    </details>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">4.C</span><span class="sec-hd-title">Appendix C · 소재 분석 보조 자료</span></div>
    <div class="lead" style="margin-bottom:14px">본문 콘텐츠 추천의 근거가 되는 소재 분석 자료입니다. 필요한 항목을 펼쳐 확인하실 수 있습니다.</div>
    <div class="appendix-stack">
      <details class="appx">
        <summary><span><span class="appx-num">C.1</span>소재유형 인사이트 · 어떤 소재가 무엇을 해냈는가</span></summary>
        <div class="appx-body">
          <div id="ctype-insights" style="margin-bottom:14px"></div>
          <div class="g2" style="margin-bottom:14px">
            <div class="evidence-card"><div class="card-title">소재유형별 성과</div><div class="card-sub">전환수 큰 순. 효율 등급은 전 지점 평균 CPA 대비 ±15%.</div><div class="tw"><table id="ctype-summary-tbl"></table></div></div>
            <div class="evidence-card"><div class="card-title">지점 × 소재유형 효율 매트릭스</div><div class="card-sub">셀 색 = CPA 효율 등급. 빈 셀 = 데이터 부족.</div><div id="ctype-matrix" class="tw"></div></div>
          </div>
        </div>
      </details>
      <details class="appx">
        <summary><span><span class="appx-num">C.2</span>신규 vs 재가공 · 6월 제작 비중 결정 근거</span></summary>
        <div class="appx-body"><div id="ctype-kind-cards"></div></div>
      </details>
      <details class="appx">
        <summary><span><span class="appx-num">C.3</span>키워드 인사이트 · 메시지 사분면</span></summary>
        <div class="appx-body">
          <div id="kw-insights" style="margin-bottom:14px"></div>
          <div class="evidence-card" style="margin-bottom:14px"><div class="card-title">메시지 사분면 · 사용량 × 효율</div><div id="kw-quadrants"></div></div>
          <div class="evidence-card"><div class="card-title">카테고리별 성과</div><div class="tw"><table id="kw-summary-tbl"></table></div></div>
        </div>
      </details>
      <details class="appx">
        <summary><span><span class="appx-num">C.4</span>라이프사이클 · 얼마나 오래 효율적인가</span></summary>
        <div class="appx-body">
          <div id="lc-insights" style="margin-bottom:14px"></div>
          <div class="g2" style="margin-bottom:14px">
            <div class="evidence-card"><div class="card-title">단계별 분포 · 신선/성숙/장기</div><div id="lc-stage-stats"></div></div>
            <div class="evidence-card"><div class="card-title">6월 운영 액션 후보</div><div class="card-sub">OFF 권장 + 장수 우수</div><div id="lc-action-cards"></div></div>
          </div>
          <div class="evidence-card" style="margin-bottom:14px"><div class="card-title">6월 신규 제작 변주 가이드</div><div class="card-sub">장수 우수 소재의 공통 패턴 추출.</div><div id="lc-variant-guide"></div></div>
          <details class="appx"><summary><span>소재별 라이프사이클 상세 표</span></summary><div class="appx-body"><div class="tw"><table id="lc-detail-tbl"></table></div></div></details>
        </div>
      </details>
      <details class="appx">
        <summary><span><span class="appx-num">C.5</span>OFF 소재 분석 · 사유 분포 + 재활용 후보</span></summary>
        <div class="appx-body">
          <div id="off-insights" style="margin-bottom:14px"></div>
          <div class="g2"><div class="evidence-card"><div class="card-title">OFF 사유 분포</div><div id="off-reason-stats"></div></div>
          <div class="evidence-card"><div class="card-title">6월 재활용 후보 (효율 양호한데 OFF)</div><div id="off-reusable"></div></div></div>
        </div>
      </details>
      <details class="appx">
        <summary><span><span class="appx-num">C.6</span>동일 소재의 지점간 성과 차이</span></summary>
        <div class="appx-body">
          <div id="cv-insights" style="margin-bottom:14px"></div>
          <div class="g2" style="margin-bottom:14px">
            <div class="evidence-card"><div class="card-title">변동 등급 분포</div><div id="cv-grade-stats"></div></div>
            <div class="evidence-card"><div class="card-title">차이 큰 소재 TOP10</div><div id="cv-top-cards"></div></div>
          </div>
          <details class="appx"><summary><span>전체 상세 표 펼쳐 보기</span></summary><div class="appx-body"><div class="tw"><table id="cv-detail-tbl"></table></div></div></details>
        </div>
      </details>
    </div>
  </div>
</div></div>

<!-- ========================= 05 애드온 판단 ========================= -->
<div id="pg-addon" class="pg"><div class="wrap">
  <div class="page-hd">
    <div class="page-hd-num">05 · Add-on Judgement</div>
    <h2 class="page-hd-title">애드온 운영 판단</h2>
    <div class="page-hd-msg">6월 애드온 운영은 전면 확대가 아니라, 효율 양호 지점을 중심으로 한 조건부 확대를 권고드립니다. 현재 데이터는 적용·비적용 그룹 간 관찰 비교에 해당하며 인과 관계로 단정할 수 없으므로, 통제된 A/B 검증을 거친 후 본격 확대 여부를 결정하는 것이 안전한 것으로 판단됩니다.</div>
    <div class="page-hd-meta">
      <span>비교 방식 <strong>적용 그룹 vs 비적용 그룹 관찰 비교</strong></span>
      <span>해석 한계 <strong>선택 편향 가능성</strong></span>
    </div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">5.1</span><span class="sec-hd-title">6월 애드온 운영 판단</span></div>
    <div class="action-card" id="addon-decision"></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">5.2</span><span class="sec-hd-title">전체 합산 관찰값</span></div>
    <div class="lead" id="addon-lead-52">아래 수치는 관찰값입니다. 적용 광고가 비적용 광고보다 우수한 결과를 보이는 배경에는 선택 편향(애드온 적용 광고가 운영 관심이 높은 우수 소재일 가능성)이 포함될 수 있음을 함께 고려해 주시기 바랍니다.</div>
    <div class="g4" id="addon-overall" style="margin-bottom:14px"></div>
    <div class="evidence-card"><div class="card-title">전체 KPI 차이 (관찰값)</div><div class="card-sub">CPM 및 CPA는 부호를 반전하여 표기하였습니다 (낮을수록 양호하므로 양수 = 우세).</div><div style="position:relative;height:220px"><canvas id="addonOverallChart"></canvas></div></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">5.3</span><span class="sec-hd-title">지점별 관찰 차이</span></div>
    <div class="evidence-card" style="padding:0;overflow:hidden"><div class="tw"><table id="addon-branch-tbl"></table></div></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">5.4</span><span class="sec-hd-title">동일 매칭키 페어 비교</span></div>
    <div class="lead">동일 소재(매칭키) 내에서 애드온 적용 광고와 비적용 광고가 모두 운영된 경우만 비교 대상으로 설정하였습니다. 운영 시점 · 예산 · 타겟이 완전히 동일하지는 않으므로 통제된 A/B 테스트와는 차이가 있는 점 함께 고려해 주시기 바랍니다.</div>
    <div class="evidence-card" style="padding:0;overflow:hidden"><div class="tw"><table id="addon-pair-tbl"></table></div></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">5.5</span><span class="sec-hd-title">6월 애드온 실행 가이드</span></div>
    <div class="g3">
      <div class="action-card">
        <div class="card-title">1주차 — 통제된 A/B 진행</div>
        <div class="card-sub" style="margin-bottom:0">효율 양호 지점(서울 · 일산 · 대구) 중 1~2개 매칭키를 선정하여 애드온 적용·비적용 광고를 동시 집행합니다. 예산과 타겟은 동일하게 통제합니다.</div>
      </div>
      <div class="action-card">
        <div class="card-title">2주차 — 결과 평가</div>
        <div class="card-sub" style="margin-bottom:0">CVR · CPA 차이가 통계적으로 유의한지 확인합니다. 차이가 ±10% 이내인 경우 효과 불분명으로 판단하겠습니다.</div>
      </div>
      <div class="action-card">
        <div class="card-title">3~4주차 — 확대 또는 보류</div>
        <div class="card-sub" style="margin-bottom:0">CPA 개선이 확인되는 경우 효율 양호 지점을 중심으로 단계적 확대를 진행합니다. 효과가 확인되지 않거나 악화될 경우 운영을 보류하겠습니다.</div>
      </div>
    </div>
  </div>
</div></div>

<script>
const DATA = __DATA_JSON__;
__JS_BODY__
</script>
</body>
</html>
"""
