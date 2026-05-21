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
<script>
(function(){
  try{
    var t = localStorage.getItem('proposal-theme');
    if(t === 'dark') document.documentElement.setAttribute('data-theme','dark');
    var z = localStorage.getItem('proposal-zoom');
    if(z === 'lg') document.documentElement.setAttribute('data-zoom','lg');
  }catch(e){}
})();
</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>
:root{
  /* Light theme (default) */
  --bg:#ffffff;--s1:#ffffff;--s2:#f4f4f5;--s3:#e4e4e7;--bd:#e4e4e7;--bd2:#d4d4d8;
  --acc:#4f46e5;--blue:#0284c7;--pur:#7c3aed;--warn:#d97706;--red:#dc2626;
  --tx:#18181b;--tx2:#52525b;--tx3:#a1a1aa;
  --t1:#059669;--t2:#0284c7;--t3:#7c3aed;--t4:#dc2626;
  --primary:#d97706;     /* Primary KPI 강조 */
  --funnel:#4f46e5;      /* Funnel KPI 보조 */
  --insight:#4f46e5;
  --evidence:#e4e4e7;
  --action:#059669;
  --appendix:#a1a1aa;
  /* Surface helpers */
  --nav-bg:rgba(255,255,255,.92);
  --hover-bg:rgba(15,23,42,.035);
  --appx-open-bg:rgba(244,244,245,.7);
  --lead-bg:rgba(79,70,229,.06);
  --kpi-stretch-bg:rgba(217,119,6,.10);
  /* Chart-specific */
  --chart-text:#52525b;
  --chart-grid:#e4e4e7;
  --chart-strong:#18181b;
  color-scheme:light;
}
[data-theme="dark"]{
  --bg:#0a0a0c;--s1:#15151a;--s2:#1f1f25;--s3:#27272f;--bd:#2a2a32;--bd2:#3a3a45;
  --acc:#818cf8;--blue:#38bdf8;--pur:#a78bfa;--warn:#fbbf24;--red:#f87171;
  --tx:#f4f4f5;--tx2:#a1a1aa;--tx3:#6b6b75;
  --t1:#34d399;--t2:#38bdf8;--t3:#a78bfa;--t4:#f87171;
  --primary:#fbbf24;
  --funnel:#818cf8;
  --insight:#818cf8;
  --evidence:#3a3a45;
  --action:#34d399;
  --appendix:#52525b;
  --nav-bg:rgba(10,10,12,.96);
  --hover-bg:rgba(255,255,255,.02);
  --appx-open-bg:rgba(31,31,37,.55);
  --lead-bg:rgba(129,140,248,.05);
  --kpi-stretch-bg:rgba(251,191,36,.10);
  --chart-text:#a1a1aa;
  --chart-grid:#27272a;
  --chart-strong:#f4f4f5;
  color-scheme:dark;
}
html{transition:background-color .2s ease,color .2s ease}
[data-zoom="lg"]{zoom:1.25}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--tx);
  font-family:'Pretendard Variable',Pretendard,-apple-system,BlinkMacSystemFont,system-ui,'Noto Sans KR',sans-serif;
  font-size:13px;line-height:1.65;letter-spacing:-0.003em;
  -webkit-font-smoothing:antialiased;
  word-break:keep-all;overflow-wrap:break-word}
/* DM Mono 숫자/영문은 어절 단위 keep-all이 불필요 — break-word만 유지 */
.num,td.num,.kpi-primary-val,.kpi-funnel-val,.gap-txt,.t3-val,.t3-sub,.bp-meta,.rm-week{word-break:normal}
h1,h2,h3,h4{letter-spacing:-0.025em}

/* ==================== Cover & Nav ==================== */
.cover{background:var(--s2);border-bottom:1px solid var(--bd);padding:42px 32px 28px}
[data-theme="dark"] .cover{background:var(--bg)}
.cover-inner{max-width:1200px;margin:0 auto}
.cover-brand{font-size:11px;font-weight:800;letter-spacing:.12em;color:var(--acc);margin-bottom:14px;text-transform:uppercase}
.cover-title{font-size:32px;font-weight:900;letter-spacing:-.03em;margin-bottom:10px;line-height:1.2}
.cover-sub{font-size:14px;color:var(--tx2);margin-bottom:18px;line-height:1.5;font-weight:500}
.cover-meta{display:flex;gap:8px;flex-wrap:wrap}
.chip{background:var(--s2);border:1px solid var(--bd);border-radius:5px;padding:5px 12px;font-size:11px;color:var(--tx2);font-weight:500}
.chip span{color:var(--tx);font-weight:700}

nav{position:sticky;top:0;z-index:100;background:var(--nav-bg);backdrop-filter:blur(14px);border-bottom:1px solid var(--bd)}
.nav-bar{max-width:1200px;margin:0 auto;display:flex;align-items:stretch;gap:0}
.nav-inner{flex:1;display:flex;overflow-x:auto;scrollbar-width:none;min-width:0}
.nav-inner::-webkit-scrollbar{display:none}
.theme-toggle{display:inline-flex;align-items:center;justify-content:center;gap:6px;background:transparent;border:none;
  cursor:pointer;color:var(--tx2);padding:0 18px;height:52px;font-size:12px;font-weight:600;
  font-family:inherit;letter-spacing:-.01em;transition:color .2s;flex-shrink:0;border-left:1px solid var(--bd)}
.theme-toggle:hover{color:var(--tx)}
.theme-toggle svg{width:16px;height:16px;flex-shrink:0}
.theme-toggle .ti-dark{display:inline-flex}
.theme-toggle .ti-light{display:none}
.theme-toggle .tl-dark{display:inline}
.theme-toggle .tl-light{display:none}
[data-theme="dark"] .theme-toggle .ti-dark{display:none}
[data-theme="dark"] .theme-toggle .ti-light{display:inline-flex}
[data-theme="dark"] .theme-toggle .tl-dark{display:none}
[data-theme="dark"] .theme-toggle .tl-light{display:inline}
.zoom-toggle{display:inline-flex;align-items:center;justify-content:center;background:transparent;border:none;
  cursor:pointer;color:var(--tx2);padding:0 16px;height:52px;font-size:11px;font-weight:700;
  font-family:"DM Mono",monospace;letter-spacing:.04em;transition:color .2s;flex-shrink:0;border-left:1px solid var(--bd)}
.zoom-toggle:hover{color:var(--tx)}
.zoom-toggle .zl-sm{display:inline}
.zoom-toggle .zl-lg{display:none}
[data-zoom="lg"] .zoom-toggle .zl-sm{display:none}
[data-zoom="lg"] .zoom-toggle .zl-lg{display:inline}
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
  background:var(--lead-bg);border-left:3px solid var(--acc);border-radius:0 6px 6px 0}
.lead strong{color:var(--acc);font-weight:700}

/* ==================== Card Hierarchy ==================== */
.insight-card{background:linear-gradient(135deg,rgba(129,140,248,.10),rgba(129,140,248,.02));
  border:1px solid rgba(129,140,248,.25);border-left:4px solid var(--insight);border-radius:8px;padding:18px 22px}
.evidence-card{background:var(--s1);border:1px solid var(--bd);border-radius:8px;padding:18px 22px}
.action-card{background:var(--s1);border:1px solid var(--bd);border-left:4px solid var(--action);border-radius:8px;padding:18px 22px}
.appendix-card{background:var(--appx-open-bg);border:1px solid var(--bd);border-radius:8px;padding:14px 18px;color:var(--tx2)}

.card-title{font-size:14px;font-weight:800;letter-spacing:-.01em;margin-bottom:6px;color:var(--tx)}
.card-sub{font-size:11px;color:var(--tx2);margin-bottom:14px;line-height:1.6;font-weight:500}
.card-body{font-size:11px;color:var(--tx);line-height:1.65;margin-top:8px;display:flex;flex-direction:column;gap:6px}
.step-list,.bullet-list{font-size:11px;color:var(--tx);line-height:1.6;margin-top:8px;padding-left:0;list-style:none;display:flex;flex-direction:column;gap:6px}
.step-list{counter-reset:step}
.step-list>li{position:relative;padding-left:22px;counter-increment:step}
.step-list>li::before{content:counter(step);position:absolute;left:0;top:1px;width:16px;height:16px;border-radius:50%;
  background:var(--s2);color:var(--tx2);font-size:10px;font-weight:800;display:inline-flex;align-items:center;justify-content:center;
  font-family:"DM Mono",monospace;border:1px solid var(--bd)}
.bullet-list>li{position:relative;padding-left:14px}
.bullet-list>li::before{content:"";position:absolute;left:3px;top:9px;width:4px;height:4px;border-radius:50%;background:var(--tx3)}
.kv-row{display:flex;flex-wrap:wrap;gap:6px;align-items:baseline}
.kv-row strong{color:var(--tx);font-weight:700}

.g2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
@media(max-width:900px){.g2,.g3,.g4{grid-template-columns:1fr}}

/* ==================== Aligned card grids (subgrid 정렬) ====================
   동일 행 카드들의 같은 인덱스 자식이 같은 row line에 정렬되도록 부모 grid-template-rows
   + 자식 카드의 grid-template-rows:subgrid 패턴. 자식 수에 따라 .aligned-{N} 변형.
   주의: 자식 개수가 카드마다 동일해야 함. 결손 시 빈 자식으로 채울 것. */
.aligned-2{grid-template-rows:repeat(2,auto)}
.aligned-2 > *{display:grid;grid-template-rows:subgrid;grid-row:span 2;row-gap:0;align-content:start}
.aligned-3{grid-template-rows:repeat(3,auto)}
.aligned-3 > *{display:grid;grid-template-rows:subgrid;grid-row:span 3;row-gap:0;align-content:start}
.aligned-4{grid-template-rows:repeat(4,auto)}
.aligned-4 > *{display:grid;grid-template-rows:subgrid;grid-row:span 4;row-gap:0;align-content:start}
.aligned-5{grid-template-rows:repeat(5,auto)}
.aligned-5 > *{display:grid;grid-template-rows:subgrid;grid-row:span 5;row-gap:0;align-content:start}
.aligned-6{grid-template-rows:repeat(6,auto)}
.aligned-6 > *{display:grid;grid-template-rows:subgrid;grid-row:span 6;row-gap:0;align-content:start}
.aligned-7{grid-template-rows:repeat(7,auto)}
.aligned-7 > *{display:grid;grid-template-rows:subgrid;grid-row:span 7;row-gap:0;align-content:start}
@media(max-width:900px){
  .aligned-2,.aligned-3,.aligned-4,.aligned-5,.aligned-6,.aligned-7{grid-template-rows:none}
  .aligned-2 > *,.aligned-3 > *,.aligned-4 > *,.aligned-5 > *,.aligned-6 > *,.aligned-7 > *{display:block;row-gap:0}
}

/* ==================== Badges (다이어트 후) ==================== */
/* 양호·평균은 배경 없고 가벼운 텍스트로 / 주의·부진만 옅은 배경 */
.bd{display:inline-flex;align-items:center;padding:2px 7px;border-radius:3px;font-size:11px;font-weight:600;letter-spacing:0;line-height:1.4;font-family:inherit}
.bd-good{color:var(--t1);background:transparent}
.bd-mid {color:var(--tx2);background:transparent}
.bd-warn{color:var(--warn);background:rgba(251,191,36,.10)}
.bd-bad {color:var(--red);background:rgba(248,113,113,.10)}
.bd-new {color:var(--pur);background:transparent}
.bd-na  {color:var(--tx3);background:transparent}

/* 그룹 배지 - 행 좌측 컬러바로 대체되므로 텍스트만 (선택적 사용) */
.bd-A{color:var(--red);background:transparent;font-weight:700}
.bd-B{color:var(--t1);background:transparent;font-weight:700}
.bd-C{color:var(--pur);background:transparent;font-weight:700}

/* 우선순위 배지 - High만 시인성 ↑, 나머지는 옅게 */
.bd-pri-high{color:var(--red);background:rgba(248,113,113,.10);font-weight:700}
.bd-pri-mid {color:var(--warn);background:transparent}
.bd-pri-low {color:var(--tx2);background:transparent}
.bd-pri-new {color:var(--pur);background:transparent}

/* ==================== KPI Cards (P0) ====================
   subgrid 정렬: lbl · val · sub 3개 자식 (kpi-stretch는 absolute라 grid item에서 제외) */
.kpi-primary-row{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:16px;grid-template-rows:repeat(3,auto)}
.kpi-primary{background:var(--s1);border:1px solid var(--bd);border-top:4px solid var(--primary);
  border-radius:8px;padding:20px 22px;position:relative;
  display:grid;grid-template-rows:subgrid;grid-row:span 3;row-gap:8px;align-content:start}
.kpi-primary-lbl{font-size:10px;font-weight:800;letter-spacing:.12em;color:var(--primary);text-transform:uppercase}
.kpi-primary-val{font-size:30px;font-weight:900;font-family:"DM Mono",monospace;letter-spacing:-.025em;color:var(--tx);line-height:1.1}
.kpi-primary-unit{font-size:14px;font-weight:600;color:var(--tx2);margin-left:4px}
.kpi-primary-sub{font-size:11px;color:var(--tx2);line-height:1.5;align-self:end}
.kpi-primary-sub strong{color:var(--tx);font-weight:700}
.kpi-stretch{position:absolute;top:14px;right:18px;font-size:10px;font-weight:800;color:var(--warn);background:var(--kpi-stretch-bg);padding:3px 8px;border-radius:4px;letter-spacing:.04em}

.kpi-funnel-row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;grid-template-rows:repeat(3,auto)}
.kpi-funnel{background:var(--s1);border:1px solid var(--bd);border-left:3px solid var(--funnel);
  border-radius:6px;padding:14px 16px;
  display:grid;grid-template-rows:subgrid;grid-row:span 3;row-gap:6px;align-content:start}
.kpi-funnel-lbl{font-size:10px;font-weight:700;letter-spacing:.08em;color:var(--funnel);text-transform:uppercase}
.kpi-funnel-val{font-size:20px;font-weight:800;font-family:"DM Mono",monospace;letter-spacing:-.02em;color:var(--tx)}
.kpi-funnel-sub{font-size:10px;color:var(--tx2);align-self:end}
@media(max-width:700px){
  .kpi-primary-row,.kpi-funnel-row{grid-template-columns:1fr;grid-template-rows:none}
  .kpi-primary,.kpi-funnel{display:block;row-gap:0}
  .kpi-primary-lbl{margin-bottom:8px}
  .kpi-primary-sub{margin-top:8px}
  .kpi-funnel-lbl{margin-bottom:6px}
  .kpi-funnel-sub{margin-top:4px}
}

/* ==================== Judgement Cards (P0 3대 판단) ====================
   동일 행 카드의 같은 인덱스 자식이 같은 row line에 맞춰지도록 CSS subgrid 사용.
   카드 안 7개 자식: tag · decision · target · row×3 · impact (kpi-stretch는 absolute라 grid item에서 제외) */
.judg-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;grid-template-rows:repeat(7,auto)}
.judg{background:var(--s1);border:1px solid var(--bd);border-left:4px solid var(--cl);border-radius:8px;padding:18px 22px;
  display:grid;grid-template-rows:subgrid;grid-row:span 7;row-gap:8px;align-content:start}
.judg.expand{--cl:var(--t1)}
.judg.improve{--cl:var(--red)}
.judg.stabilize{--cl:var(--pur)}
.judg-tag{justify-self:start;font-size:10px;font-weight:800;color:var(--cl);background:rgba(255,255,255,.04);padding:2px 8px;border-radius:4px;letter-spacing:.04em;text-transform:uppercase}
.judg-decision{font-size:15px;font-weight:800;color:var(--tx);letter-spacing:-.01em}
.judg-target{font-size:12px;color:var(--tx2);line-height:1.5}
.judg-target strong{color:var(--tx);font-weight:700}
.judg-row{display:flex;align-items:flex-start;gap:8px;font-size:11px;color:var(--tx2);line-height:1.55}
.judg-row-lbl{font-weight:700;color:var(--tx);min-width:48px;flex-shrink:0}
.judg-impact{align-self:end;padding-top:10px;border-top:1px dashed var(--bd);font-size:11px;color:var(--cl);font-weight:700}
.judg-impact span{color:var(--tx2);font-weight:500;margin-left:4px}
@media(max-width:900px){
  .judg-grid{grid-template-columns:1fr;grid-template-rows:none}
  .judg{display:block;row-gap:0}
  .judg-tag{display:inline-block;margin-bottom:10px}
  .judg-decision,.judg-target{margin-bottom:6px}
  .judg-row{margin-top:6px}
  .judg-impact{margin-top:12px}
}

/* ==================== Tables ==================== */
.tw{overflow-x:auto;border-radius:8px;border:1px solid var(--bd)}
table{width:100%;border-collapse:collapse;font-size:13px}
/* 모든 테이블 셀 세로 중앙 정렬 (행 높이 차이 시 상중하 중 중앙) */
table th,table td{vertical-align:middle}
/* 4.1 지점×퍼널 매트릭스 — 콘텐츠 길이에 따라 유동 너비 + 가로 스크롤(.tw overflow-x:auto) */
/* table-layout:auto = 콘텐츠 기반 자동 분배. min-width로 가독성 floor만 설정. */
#exec-matrix{table-layout:auto}
#exec-matrix th:nth-child(1),#exec-matrix td:nth-child(1){min-width:96px}                       /* 지점 */
#exec-matrix th:nth-child(2),#exec-matrix td:nth-child(2){min-width:72px;text-align:center}     /* 우선 */
#exec-matrix th:nth-child(3),#exec-matrix td:nth-child(3),
#exec-matrix th:nth-child(4),#exec-matrix td:nth-child(4),
#exec-matrix th:nth-child(5),#exec-matrix td:nth-child(5){min-width:200px;white-space:normal;line-height:1.55}  /* CPM/CTR/CVR */
#exec-matrix th:nth-child(6),#exec-matrix td:nth-child(6){min-width:220px;white-space:normal;line-height:1.55}  /* 소재 역할 */
#exec-matrix th:nth-child(7),#exec-matrix td:nth-child(7){min-width:280px;white-space:normal;line-height:1.6}   /* 6월 콘텐츠 */
#exec-matrix .fcell{min-width:0}
#exec-matrix .fcell-kpi{white-space:normal;word-break:break-word;font-size:11px;line-height:1.45;margin-top:3px}
/* 가로 스크롤 시 좌측 지점 컬럼 고정 (sticky) — 비교 편의 */
#exec-matrix th:nth-child(1),#exec-matrix td:nth-child(1){position:sticky;left:0;background:var(--s1);z-index:2}
#exec-matrix thead th:nth-child(1){background:var(--s2);z-index:3}
/* sticky 컬럼이 #exec-matrix 특이도로 덮어써져 hover가 적용 안 되는 문제 보정 */
#exec-matrix tbody tr:hover td:nth-child(1){background:var(--hover-bg)}
/* 스크롤 힌트 */
.scroll-hint{font-size:10.5px;color:var(--tx2);margin-bottom:6px;display:flex;align-items:center;gap:6px}
.scroll-hint::before{content:'↔';font-weight:800;color:var(--acc)}
th{background:var(--s2);color:var(--tx2);font-weight:700;font-size:11px;letter-spacing:.04em;
  padding:12px 14px;text-align:left;border-bottom:1px solid var(--bd);white-space:nowrap;line-height:1.4;text-transform:uppercase}
td{padding:13px 14px;border-bottom:1px solid var(--bd);color:var(--tx);vertical-align:middle;white-space:nowrap;
  font-family:'Pretendard Variable',Pretendard,-apple-system,BlinkMacSystemFont,system-ui,sans-serif;font-size:13px;
  font-variant-numeric:tabular-nums;line-height:1.5}
td.lbl{color:var(--tx);font-size:13px;font-weight:700}
td.txt{color:var(--tx);font-size:12px;font-weight:500;white-space:normal;line-height:1.55}
td.num{font-family:"DM Mono",monospace;font-variant-numeric:tabular-nums}
td.muted{color:var(--tx2)}
tr:last-child td{border-bottom:none}
tr:hover td{background:var(--hover-bg)}

/* Master matrix - 지점별 행 좌측 컬러바로 그룹·우선순위 표시 */
.tbl-master tr td:first-child{font-weight:700;position:relative}
.tbl-master tr td:first-child::before{content:"";position:absolute;left:0;top:8px;bottom:8px;width:3px;border-radius:2px;background:var(--row-cl,transparent)}
.tbl-master tr.r-A td:first-child{--row-cl:var(--red)}
.tbl-master tr.r-B td:first-child{--row-cl:var(--t1)}
.tbl-master tr.r-C td:first-child{--row-cl:var(--pur)}

/* 인라인 갭% 텍스트 - 배지 대신 */
.gap-txt{font-size:11px;font-weight:600;margin-left:6px;font-family:"DM Mono",monospace}
.gap-txt.up{color:var(--t1)}
.gap-txt.down{color:var(--red)}
.gap-txt.flat{color:var(--tx3)}

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
.fcell{padding:10px 12px;border-radius:5px;background:transparent;border:1px solid transparent;
  font-family:'Pretendard Variable',Pretendard,sans-serif;font-size:12px;line-height:1.55;min-width:150px;white-space:normal;vertical-align:middle}
.fcell.good{background:transparent;border-color:transparent;opacity:.65}
.fcell.warn{background:rgba(251,191,36,.05);border-color:rgba(251,191,36,.18)}
.fcell.bad{background:rgba(248,113,113,.06);border-color:rgba(248,113,113,.22)}
.fcell-row{display:flex;align-items:center;gap:5px;margin-bottom:4px}
.fcell-action{color:var(--tx);font-weight:600;font-size:12px;line-height:1.5;margin:4px 0}
.fcell.good .fcell-action{color:var(--tx2);font-weight:500}
.fcell-role{color:var(--tx2);font-size:11px;line-height:1.4;margin-bottom:3px}
.fcell-role strong{color:var(--pur);font-weight:700}
.fcell-kpi{color:var(--tx3);font-size:11px;letter-spacing:-.01em}

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
.appx[open]{background:var(--appx-open-bg)}
.appx summary{cursor:pointer;padding:12px 18px;font-size:12px;font-weight:700;color:var(--tx2);list-style:none;
  display:flex;align-items:center;justify-content:space-between;transition:background .15s}
.appx summary:hover{background:var(--s2);color:var(--tx)}
.appx summary::-webkit-details-marker{display:none}
.appx summary::after{content:"▼";font-size:10px;color:var(--tx3);transition:transform .2s;margin-left:8px}
.appx[open] summary::after{transform:rotate(180deg)}
.appx-num{font-size:10px;font-weight:800;color:var(--acc);font-family:"DM Mono",monospace;margin-right:6px}
.appx-body{padding:16px 20px;border-top:1px solid var(--bd)}

/* ==================== R9·R10 추가 박스 ==================== */
.gap-caveat{padding:10px 14px;border:1px solid var(--bd);border-left:4px solid var(--warn);border-radius:6px;background:rgba(245,158,11,.05);font-size:11.5px;color:var(--tx);line-height:1.6}
.gap-caveat strong{color:var(--warn)}
.busan-box{padding:14px 16px;border:2px dashed var(--pur);border-radius:8px;background:rgba(167,139,250,.06)}
.busan-hdr{display:flex;align-items:baseline;gap:10px;margin-bottom:8px}
.busan-tag{font-size:10px;font-weight:800;color:var(--pur);letter-spacing:.06em;text-transform:uppercase;background:rgba(167,139,250,.12);padding:3px 8px;border-radius:4px}
.busan-title{font-size:14px;font-weight:800;color:var(--tx)}
.busan-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:8px}
.busan-row{font-size:11.5px;color:var(--tx);line-height:1.55}
.busan-row strong{color:var(--pur)}
.norm-box{padding:12px 14px;border:1px solid var(--bd);border-radius:6px;background:var(--s2)}
.norm-hdr{font-size:11px;font-weight:800;color:var(--tx2);text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px}
.norm-list{font-size:11.5px;color:var(--tx);line-height:1.7}
.norm-list li{margin-bottom:4px}
.tier-inline{margin-top:8px;padding:6px 10px;background:rgba(52,211,153,.06);border-left:3px solid var(--t1);border-radius:0 4px 4px 0;font-size:11.5px;color:var(--tx);line-height:1.55}
.tier-inline-lbl{font-size:10px;font-weight:800;color:var(--t1);letter-spacing:.06em;text-transform:uppercase;margin-right:6px}
.appx-tbl-section{margin-bottom:18px}
.appx-tbl-hdr{font-size:12px;font-weight:800;color:var(--tx);margin-bottom:6px;padding:6px 10px;background:var(--s2);border-radius:4px;border-left:3px solid var(--acc)}

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

/* ==================== 2.3.1 Funnel variance cards ====================
   각 카드는 헤더 · 메타 · 분해 묶음 · 보조 시그널 · 운영 함의 5개 자식 — subgrid 정렬 */
.fv-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;grid-template-rows:repeat(5,auto)}
.fv-card{background:var(--s1);border:1px solid var(--bd);border-left:4px solid var(--cl);border-radius:8px;
  padding:16px 18px;display:grid;grid-template-rows:subgrid;grid-row:span 5;row-gap:0;align-content:start}
.fv-card.cpm{--cl:var(--red)}
.fv-card.ctr{--cl:var(--blue)}
.fv-card.cvr{--cl:var(--pur)}
.fv-card.cvr-down{--cl:var(--warn)}
.fv-hdr{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin-bottom:6px}
.fv-hdr-branch{font-size:14px;font-weight:800;color:var(--tx)}
.fv-hdr-metric{font-size:12px;font-weight:700;color:var(--cl);letter-spacing:.04em;text-transform:uppercase}
.fv-hdr-delta{font-size:13px;font-weight:800;font-family:"DM Mono",monospace;color:var(--cl);margin-left:auto}
.fv-hdr-partial{font-size:9px;font-weight:800;color:var(--warn);background:var(--kpi-stretch-bg);padding:1px 6px;border-radius:3px;letter-spacing:.04em}
.fv-meta{font-size:10.5px;color:var(--tx2);margin-bottom:10px;font-family:"DM Mono",monospace;line-height:1.5}
.fv-meta-trend{margin-left:6px;color:var(--tx3)}
.fv-decomp{display:flex;flex-direction:column;gap:5px;margin-bottom:10px;padding:10px 12px;background:var(--s2);border-radius:5px}
.fv-decomp-row{display:flex;align-items:baseline;gap:8px;font-size:11px;line-height:1.5}
.fv-decomp-lbl{font-weight:700;color:var(--tx);min-width:88px;flex-shrink:0}
.fv-decomp-val{font-family:"DM Mono",monospace;font-weight:700;color:var(--cl);min-width:48px}
.fv-decomp-detail{color:var(--tx2);font-size:10.5px;flex:1;line-height:1.5}
.fv-aux{display:flex;flex-direction:column;gap:3px;margin-bottom:10px;font-size:10.5px;color:var(--tx2);line-height:1.5}
.fv-aux-row{padding-left:10px;border-left:2px solid var(--bd2)}
.fv-aux-row strong{color:var(--tx);font-weight:700}
.fv-imp{padding-top:10px;border-top:1px dashed var(--bd);font-size:11.5px;color:var(--tx);line-height:1.65}
.fv-imp strong{color:var(--cl);font-weight:700}
.fv-imp.soft{color:var(--tx2)}
.fv-imp.soft strong{color:var(--warn)}
@media(max-width:900px){
  .fv-grid{grid-template-columns:1fr;grid-template-rows:none}
  .fv-card{display:block;row-gap:0}
}
</style>
</head>
<body>

<div class="cover"><div class="cover-inner">
  <div class="cover-brand">다이트한의원 · TikTok Ads · 2026년 6월 운영 제안</div>
  <h1 class="cover-title">2026년 6월 TikTok 운영 방향 보고</h1>
  <div class="cover-sub">전 기간 운영 데이터 진단을 바탕으로 6월 목표·액션·타겟팅·콘텐츠 실행안을 정리하여 보고드립니다.</div>
  <div class="cover-meta" id="cover-meta"></div>
</div></div>

<nav><div class="nav-bar">
  <div class="nav-inner">
    <button class="tb on" data-tab="exec"><span class="tb-num">01</span>Executive Summary</button>
    <button class="tb" data-tab="diag"><span class="tb-num">02</span>성과 진단</button>
    <button class="tb" data-tab="plan"><span class="tb-num">03</span>6월 목표·액션</button>
    <button class="tb" data-tab="exec_plan"><span class="tb-num">04</span>타겟팅·콘텐츠 실행안</button>
    <button class="tb" data-tab="addon"><span class="tb-num">05</span>애드온 판단</button>
    <button class="tb" data-tab="targeting"><span class="tb-num">부록 A</span>성별·연령 검증</button>
    <button class="tb" data-tab="geo"><span class="tb-num">부록 B</span>지역 도달</button>
    <button class="tb" data-tab="creative-appx"><span class="tb-num">부록 C</span>소재 TIER 표</button>
  </div>
  <button class="theme-toggle" id="themeToggle" type="button" aria-label="테마 전환" title="라이트/다크 전환">
    <span class="ti-dark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg></span>
    <span class="ti-light" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg></span>
    <span class="tl-dark">다크</span><span class="tl-light">라이트</span>
  </button>
  <button class="zoom-toggle" id="zoomToggle" type="button" aria-label="배율 전환" title="100% / 125% 전환">
    <span class="zl-sm">100%</span><span class="zl-lg">125%</span>
  </button>
</div></nav>

<!-- ========================= 01 Executive Summary ========================= -->
<div id="pg-exec" class="pg on"><div class="wrap">
  <div class="page-hd">
    <div class="page-hd-num">01 · Executive Summary</div>
    <h2 class="page-hd-title">6월 운영 방향 요약</h2>
    <div class="page-hd-msg">6월 다이트한의원 TikTok 운영은 지점별 퍼널 병목에 따라 <strong style="color:var(--red)">A 효율 개선</strong> · <strong style="color:var(--t1)">B 예산 확대</strong> · <strong style="color:var(--pur)">C 신규 안정화</strong> 세 방향으로 분리 적용하며, 전환 목표는 <strong style="color:var(--primary)">762건(Stretch 822건)</strong>으로 설정하였습니다. CPA 변동의 원인을 <strong>소재 문제</strong>와 <strong>타겟 도달 문제</strong>로 분리하기 위해 성별·연령·지역 노출 품질을 함께 검증하였으며 — <strong style="color:var(--t1)">성별 타겟팅은 정상 작동</strong>, <strong>천안만 경기 노출 비중이 높아 세팅 확인 권고</strong>입니다 (상세는 부록 A·B).</div>
    <div class="page-hd-meta">
      <span>분석 기간 <strong id="meta-period"></strong></span>
      <span>대상 <strong id="meta-branches"></strong></span>
      <span>누적 KPI 베이스라인 <strong>전 기간 2~5월</strong> · 베스트월 비교 <strong>2~4월</strong></span>
    </div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">1.1</span><span class="sec-hd-title">6월 운영 목표</span><span class="sec-hd-sub">Primary KPI · 비즈니스 결과</span></div>
    <div class="lead">전환수 <strong>762건</strong>을 base target, <strong>822건</strong>을 stretch target으로 설정하였습니다. 평균 CPA는 <strong>27,278원</strong>을 가드레일로 운영하겠습니다. 모든 수치는 지점별 베스트월(2~4월) 재달성을 기준으로 산정된 값입니다.</div>
    <div class="kpi-primary-row" id="kpi-primary"></div>
    <div class="sec-hd" style="margin-top:18px"><span class="sec-hd-num">1.2</span><span class="sec-hd-title">목표 달성 조건</span><span class="sec-hd-sub">Funnel KPI · 조정 레버</span></div>
    <div class="kpi-funnel-row" id="kpi-funnel"></div>
    <div id="kpi-gap-caveat" style="margin-top:12px"></div>
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

    <!-- 2.3.1 변동 주원인 (히트맵 변동의 산술 분해 + 운영 정책) -->
    <div class="subsec" style="margin-top:24px">
      <div class="sec-hd" style="margin-bottom:10px">
        <span class="sec-hd-num">2.3.1</span>
        <span class="sec-hd-title">히트맵 변동 주원인 — 구성비 · 단위성과 효과 분해</span>
        <span class="sec-hd-sub">creative_type 기준 Shapley 분해</span>
      </div>
      <div class="lead" id="fv-trend"></div>
      <div id="fv-cards"></div>
      <details class="appx" id="fv-weak-wrap" style="margin-top:10px;display:none">
        <summary><span><span class="appx-num">2.3.1·W</span>설명력 부족 셀 (mix·within 모두 &lt;20%) — 자연 변동 가능성</span></summary>
        <div class="appx-body"><div id="fv-weak"></div></div>
      </details>
      <div class="appendix-card" style="margin-top:10px;font-size:11px;color:var(--tx2);line-height:1.6">
        <strong style="color:var(--tx)">분해 방법 안내.</strong>
        월별 KPI 변동을 (1) <strong>구성비 효과</strong>(소재유형 비중 변화) (2) <strong>단위성과 효과</strong>(같은 유형 내 단가·반응률 변화)로 산술 분해합니다.
        구성비 효과가 우세하면 소재 비중 조정으로 즉시 회복 가능하고,
        단위성과 효과가 우세하면 입찰 경쟁·랜딩·상담 응대 등 광고 외부 요인 점검이 필요합니다.
        분해 합은 정의상 변화량과 정확히 일치합니다.
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
    <div class="g3 aligned-6" id="funnel-action-cards"></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">3.3</span><span class="sec-hd-title">지점별 운영 처방 카드</span></div>
    <div class="lead">3.1이 목표 수치 비교라면, 본 섹션은 지점별 6월 운영 지시서입니다. 그룹 판단 · 핵심 병목 · 운영 액션 · 검증 KPI · 중단 조건을 한 카드로 정리하였습니다.</div>
    <div id="branch-action-cards"></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">3.4</span><span class="sec-hd-title">6월 예산 시나리오</span></div>
    <div class="lead" id="budget-lead-34"></div>
    <div class="g3 aligned-6" style="margin-bottom:16px" id="budget-scenarios"></div>
    <div class="evidence-card" style="padding:0;overflow:hidden"><div class="tw"><table id="budget-rec-tbl"></table></div></div>
    <div id="busan-learning-box" style="margin-top:16px"></div>
    <div id="normalize-18m-box" style="margin-top:16px"></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">3.5</span><span class="sec-hd-title">A/B 테스트 운영 가이드</span></div>
    <div class="lead">TikTok Ads는 예산이 캠페인 또는 광고 그룹(지점) 단위로 설정되며, 소재는 광고 단위 ON/OFF만 가능합니다. 따라서 A/B 검증은 <strong>광고 그룹을 복제하여 두 그룹에서 1개 변수만 다르게 운영</strong>하는 방식을 권고드립니다.</div>
    <div class="g3 aligned-2" id="ab-test-guide" style="margin-bottom:14px">
      <div class="action-card">
        <div class="card-title" style="font-size:14px;color:var(--action)">진행 방식</div>
        <ol class="step-list">
          <li>효율 양호 지점의 광고 그룹을 복제하여 두 그룹으로 분리합니다.</li>
          <li>한 번에 <strong>1개 변수만</strong> 변경합니다 (소재 묶음 또는 입찰 전략).</li>
          <li>다른 변수는 모두 동일하게 통제합니다 (예산 · 타겟 · 시간대).</li>
          <li>학습 종료 후 두 그룹의 결과를 비교하여 우세 변수를 채택합니다.</li>
        </ol>
      </div>
      <div class="action-card">
        <div class="card-title" style="font-size:14px;color:var(--action)">학습 조건</div>
        <ul class="bullet-list">
          <li>학습 기간 <strong>최소 2주</strong> 이상 확보 (알고리즘 안정화 목적)</li>
          <li>그룹별 누적 <strong>전환 30건 이상</strong> 확보 시 유의미한 비교 가능</li>
          <li>미달 시 추세 참고에 한정하고 확정 판단은 보류합니다.</li>
          <li>학습 모수 부족 시 그룹 통합 후 재시작을 권고드립니다.</li>
        </ul>
      </div>
      <div class="action-card">
        <div class="card-title" style="font-size:14px;color:var(--action)">우선 추천 지점 및 변수</div>
        <div class="card-body">
          <div class="kv-row"><strong>지점 후보</strong><span id="ab-priority-branches">효율 양호 및 학습 모수 충분 지점</span></div>
          <div class="kv-row"><strong>검증 변수 후보</strong></div>
          <ol class="step-list" style="margin-top:0">
            <li>소재 묶음 A(후기형) vs B(상담전환형)</li>
            <li>입찰 전략 (최대 전환 vs 비용 한도)</li>
            <li>노출 시간대 (전일 vs 피크 회피)</li>
          </ol>
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
          <div class="rm-row"><div class="rm-week">4주차<br>06/22-30</div><div class="rm-body"><strong>중간 점검 및 7월 방향 정리.</strong> 검증 KPI를 기준으로 지점별 회복 여부를 확인합니다. 6월 운영 결과를 토대로 7월 운영 방향을 조정하겠습니다. 5월 신 디자인(v2)은 부산 일부 미적용으로 동기간 비애드온 비교가 불가능했던 만큼, 6월 누적 데이터로 디자인 효과를 재측정하고 ① v2 표준화 ② v1 일부 복원 ③ 디자인 부분 변경 중 한 가지로 7월 표준 디자인을 결정합니다. 부산은 R10 학습 룰 결과를 별도 평가.</div></div>
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
    <div class="scroll-hint">좌우 스크롤로 모든 컬럼 확인 (지점 컬럼은 고정)</div>
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

<!-- ========================= 05 애드온 판단 (R11 보수적 압축) ========================= -->
<div id="pg-addon" class="pg"><div class="wrap">
  <div class="page-hd">
    <div class="page-hd-num">05 · Add-on Judgement</div>
    <h2 class="page-hd-title">애드온 운영 판단 — 디자인 변경 반영</h2>
    <div class="page-hd-msg">3~4월의 <strong>구 디자인(v1)</strong>과 5월의 <strong style="color:var(--t1)">신 디자인(v2)</strong>은 별개 소재로 보아 분리 분석합니다. 단, 5월에는 원래 전 캠페인·소재에 애드온을 적용할 예정이었으나 <strong style="color:var(--warn)">부산점만 운영 사유로 일부 미적용</strong>되어 5월 비애드온이 사실상 부산 단일 지점 데이터에 해당합니다. 따라서 본 5장은 <strong>부산을 제외</strong>한 8개 지점만을 대상으로, 평가축을 <strong>(1) v1 vs 3~4월 비애드온</strong>과 <strong>(2) v2 vs v1 직접 비교</strong>로 이원화하였습니다.</div>
    <div class="page-hd-meta">
      <span>v1 (구 디자인) <strong>2026-02 ~ 2026-04 노출</strong></span>
      <span>v2 (신 디자인) <strong>2026-05 ~ 노출 (cutoff 05-01)</strong></span>
      <span>분석 대상 <strong>부산 제외 8개 지점</strong></span>
    </div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">5.1</span><span class="sec-hd-title">6월 운영 권고</span><span class="sec-hd-sub">디자인 변경 효과 + 소재유형 처방</span></div>
    <div id="addon-judgement"></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">5.2</span><span class="sec-hd-title">판단 근거 — 두 평가축</span></div>
    <div class="lead" id="addon-lead-52">평가축 1은 애드온 자체의 효과(v1 시기, 양쪽 표본 충분)를, 평가축 2는 디자인 변경의 순효과(v2 vs v1 직접 비교)를 측정합니다. 5월 부산 일부 미적용으로 인해 v2를 동기간 비애드온과 직접 비교하는 것은 불가능합니다.</div>
    <div class="g2" id="addon-version-cards" style="margin-bottom:14px"></div>
    <div id="addon-v2-unmeasurable-box" style="margin-bottom:14px"></div>
    <div class="evidence-card" style="margin-bottom:14px"><div class="card-title">디자인 변경 효과 차트 (v2 vs v1)</div><div class="card-sub">동일 그룹(애드온 적용) 내 디자인 변경 전후 비교. CPM/CPA는 부호 반전(양수 = 신 디자인 우세). 시기 차이에 따른 시즌 효과가 일부 포함됩니다.</div><div style="position:relative;height:220px"><canvas id="addonOverallChart"></canvas></div></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">5.3</span><span class="sec-hd-title">6월 애드온 실행 가이드</span><span class="sec-hd-sub">디자인 변경 검증 처방</span></div>
    <div id="addon-execution-guide"></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">5.A</span><span class="sec-hd-title">Appendix · 디테일 자료</span><span class="sec-hd-sub">접힘 — 클릭하여 펼치기</span></div>
    <div id="addon-appendix">
      <details class="appx">
        <summary><span><span class="appx-num">A.1</span>소재유형별 디자인 효과 (v1 → v2)</span></summary>
        <div class="appx-body">
          <div class="lead" style="margin-bottom:10px;font-size:12px">동일 소재유형에서 v1·v2 디자인의 절대 KPI 비교. p-value는 v1·v2 CVR 비율 z-test 기준. v2 표본이 작은 유형은 신호로만 해석.</div>
          <div class="tw"><table id="addon-creative-type-tbl"></table></div>
        </div>
      </details>
      <details class="appx">
        <summary><span><span class="appx-num">A.2</span>시청 깔때기 + 인게이지먼트 가설 검증 (바이럴형 vs 전환형)</span></summary>
        <div class="appx-body">
          <div class="lead" style="margin-bottom:10px;font-size:12px">TikTok 애드온은 영상 3초+ 시점부터 노출되므로 6초 시청률이 도달률에 가장 근접한 지표. 시청 깊이와 인게이지먼트(공유율)로 콘텐츠 archetype을 분리 진단합니다.</div>
          <div id="addon-hypothesis-box" style="margin-bottom:14px"></div>
          <div class="tw"><table id="addon-watch-funnel-tbl"></table></div>
        </div>
      </details>
      <details class="appx">
        <summary><span><span class="appx-num">A.3</span>지점별 관찰 차이 (부산 제외 8개 지점)</span></summary>
        <div class="appx-body">
          <div class="lead" style="margin-bottom:10px;font-size:12px">v1 시기에는 동기간 비애드온이 충분하여 비교가 가능하나, v2 시기에는 동기간 비애드온이 사실상 부재하여 v2 vs v1 디자인 직접 비교 표로 대체합니다.</div>
          <div style="margin-bottom:14px"><div style="font-size:11px;color:var(--tx);margin-bottom:6px;font-weight:700">v1 vs 3~4월 비애드온 (지점별)</div><div class="tw"><table id="addon-branch-tbl-v1"></table></div></div>
          <div><div style="font-size:11px;color:var(--tx);margin-bottom:6px;font-weight:700">v2 vs v1 디자인 직접 비교 (지점별)</div><div class="tw"><table id="addon-branch-tbl-v2"></table></div></div>
        </div>
      </details>
      <details class="appx">
        <summary><span><span class="appx-num">A.4</span>월별 추세 (디자인 변경 시점, 부산 제외)</span></summary>
        <div class="appx-body">
          <div class="lead" style="margin-bottom:10px;font-size:12px">부산 제외 8개 지점 기준 월별 애드온 vs 비애드온 CVR. <strong>2026-05부터 신 디자인(v2)</strong>. 표본 부족 월(클릭 &lt;100)은 ⚠ 표시.</div>
          <div class="tw"><table id="addon-monthly-tbl"></table></div>
        </div>
      </details>
    </div>
  </div>
</div></div>

<!-- ========================= 부록 A · 성별·연령 타겟팅 검증 (기존 6장 강등) ========================= -->
<div id="pg-targeting" class="pg"><div class="wrap">
  <div class="page-hd">
    <div class="page-hd-num">부록 A · Targeting Health</div>
    <h2 class="page-hd-title">성별·연령 타겟팅 검증</h2>
    <div class="page-hd-msg">캠페인 타겟팅(성별=여성 고정)이 실제 노출에서 정상 작동하는지 검증한 부록입니다. <strong style="color:var(--t1)">결론: 성별 타겟팅 정상 / 25-34는 확대 제외</strong>로 본문 1장에서 요약되며, 본 부록은 상세 표와 caveat를 제공합니다.</div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">A.1</span><span class="sec-hd-title">진단 결과 요약</span></div>
    <div id="targeting-judgement"></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">A.2</span><span class="sec-hd-title">성별 노출 정합성</span></div>
    <div id="targeting-gender-cards" style="margin-bottom:12px"></div>
    <div id="targeting-none-anomaly"></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">A.3</span><span class="sec-hd-title">여성 연령별 효율 분포</span></div>
    <div class="evidence-card" style="padding:0;overflow:hidden;margin-bottom:12px"><div class="tw"><table id="targeting-age-tbl"></table></div></div>
    <div id="targeting-age-signal"></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">A.4</span><span class="sec-hd-title">지점별 노출 품질 + 분석 기준</span></div>
    <div class="evidence-card" style="padding:0;overflow:hidden;margin-bottom:12px"><div class="tw"><table id="targeting-branch-tbl"></table></div></div>
    <div id="targeting-note"></div>
  </div>
</div></div>

<!-- ========================= 부록 B · 지역 도달 정합성 (기존 7장 강등) ========================= -->
<div id="pg-geo" class="pg"><div class="wrap">
  <div class="page-hd">
    <div class="page-hd-num">부록 B · Geo Reach</div>
    <h2 class="page-hd-title">지역 도달 정합성</h2>
    <div class="page-hd-msg">9개 지점 광고가 의도한 생활권에 도달하는지 검증한 부록입니다. <strong style="color:var(--t1)">결론: 전체 지역 도달은 대체로 정합(누수 2.59%), 천안만 경기 노출 비중이 높아 세팅 확인 필요</strong>. TikTok province 메트릭은 추정·샘플링 성격이 있어 단정형이 아닌 누수 진단형으로 활용합니다.</div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">B.1</span><span class="sec-hd-title">진단 결과 요약</span></div>
    <div id="geo-judgement"></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">B.2</span><span class="sec-hd-title">전체 노출 분포 (정합/생활권/누수)</span></div>
    <div id="geo-overall-cards" style="margin-bottom:12px"></div>
  </div>

  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">B.3</span><span class="sec-hd-title">지점별 누수 진단 + 누수 지역 + 매칭 룰</span></div>
    <div class="evidence-card" style="padding:0;overflow:hidden;margin-bottom:12px"><div class="tw"><table id="geo-branch-tbl"></table></div></div>
    <details class="appx" style="margin-bottom:12px">
      <summary><span>누수 노출 지역 TOP</span></summary>
      <div class="appx-body"><div class="tw"><table id="geo-leakage-tbl"></table></div></div>
    </details>
    <div id="geo-note"></div>
  </div>
</div></div>

<!-- ========================= 부록 C · 소재 TIER 전체 표 (기존 5.D 강등) ========================= -->
<div id="pg-creative-appx" class="pg"><div class="wrap">
  <div class="page-hd">
    <div class="page-hd-num">부록 C · Creative Appendix</div>
    <h2 class="page-hd-title">지점별 소재 TIER 분류 전체 표</h2>
    <div class="page-hd-msg">3.3 운영 처방 카드는 핵심 TIER1/TIER4 소재 1~2개만 노출됩니다. 본 부록은 지점별 전체 소재의 TIER 분류·근거·권장 액션을 표 한 장으로 통합하여, 운영 의사결정 시 손실 없이 참조할 수 있도록 정리한 자료입니다. 시청 깊이·인게이지먼트 컬럼이 함께 노출되어 동일 TIER 내 콘텐츠 적합성 비교에도 활용 가능합니다.</div>
  </div>
  <div class="sec">
    <div id="appendix-creative-tbl"></div>
  </div>
  <div class="sec">
    <div class="sec-hd"><span class="sec-hd-num">C.E</span><span class="sec-hd-title">추정 기반 캐비엇</span></div>
    <div id="seasonality-caveat"></div>
  </div>
</div></div>

<script>
const DATA = __DATA_JSON__;
__JS_BODY__
</script>
</body>
</html>
"""
