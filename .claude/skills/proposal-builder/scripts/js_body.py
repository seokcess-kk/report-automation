"""HTML 템플릿용 JS 본문. __JS_BODY__ 자리에 삽입.

설계 원칙:
  - 페이지별 IIFE 분리
  - DATA.consulting_signals를 적극 사용
  - 헬퍼: fmt, fmtPct, fmtSigned, statusBadge, gapBadge
"""

JS_BODY = r"""
// ==================== Theme ====================
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const CHART_TEXT = cssVar('--chart-text') || '#a1a1aa';
const CHART_GRID = cssVar('--chart-grid') || '#27272a';
const CHART_STRONG = cssVar('--chart-strong') || '#f4f4f5';
(function(){
  const btn = document.getElementById('themeToggle');
  if(!btn) return;
  btn.addEventListener('click', () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const next = isDark ? 'light' : 'dark';
    if(next === 'dark') document.documentElement.setAttribute('data-theme','dark');
    else document.documentElement.removeAttribute('data-theme');
    try{ localStorage.setItem('proposal-theme', next); }catch(e){}
    // Charts cache resolved colors at init — reload to fully repaint
    location.reload();
  });
})();
(function(){
  const btn = document.getElementById('zoomToggle');
  if(!btn) return;
  btn.addEventListener('click', () => {
    const isLg = document.documentElement.getAttribute('data-zoom') === 'lg';
    if(isLg) document.documentElement.removeAttribute('data-zoom');
    else document.documentElement.setAttribute('data-zoom','lg');
    try{ localStorage.setItem('proposal-zoom', isLg ? 'sm' : 'lg'); }catch(e){}
  });
})();

// ==================== Helpers ====================
const fmt = (n, suffix = '') => (n === null || n === undefined) ? '-' : (Math.round(n).toLocaleString() + suffix);
const fmtPct = (n) => (n === null || n === undefined) ? '-' : (n.toFixed(2) + '%');
const fmtPct1 = (n) => (n === null || n === undefined) ? '-' : (n.toFixed(1) + '%');
const fmtSigned = (n) => {
  if (n === null || n === undefined) return '-';
  return (n > 0 ? '+' : '') + n.toFixed(1) + '%';
};
const statusBadge = (status, label) => {
  const lbl = label ?? ({good:'양호',warn:'주의',bad:'우려',mid:'평균',na:'-',new:'신규'}[status] || status);
  return `<span class="bd bd-${status}">${lbl}</span>`;
};
const gapBadge = (gap) => {
  if (gap === null || gap === undefined) return `<span class="bd bd-na">-</span>`;
  const s = gap >= 0 ? 'good' : (gap >= -10 ? 'warn' : 'bad');
  const sign = gap > 0 ? '+' : '';
  return `<span class="bd bd-${s}">${sign}${gap.toFixed(1)}%</span>`;
};
const priorityBadge = (p) => {
  const cls = {High:'pri-high',Mid:'pri-mid',Low:'pri-low',New:'pri-new'}[p] || 'na';
  return `<span class="bd bd-${cls}">${p}</span>`;
};
const groupBadge = (g) => `<span class="bd bd-${g}">${g}</span>`;
const heatClass = (val, allVals, direction) => {
  const finite = allVals.filter(v => v !== null && v !== undefined);
  if (finite.length === 0 || val === null || val === undefined) return 'h-na';
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  if (max === min) return 'h-mid';
  const norm = (val - min) / (max - min);
  if (direction === 'low') {
    if (norm < 0.33) return 'h-good';
    if (norm > 0.66) return 'h-bad';
    return 'h-mid';
  }
  if (norm > 0.66) return 'h-good';
  if (norm < 0.33) return 'h-bad';
  return 'h-mid';
};

// 그룹/그룹 라벨 정규화
const groupKey = (raw) => {
  if (!raw) return 'B';
  if (raw === 'A' || raw === 'B' || raw === 'C') return raw;
  return 'B';
};
const groupLabel = (g) => ({A:'A. 효율 개선 우선', B:'B. 예산 확대 후보', C:'C. 신규 모니터링'}[g] || g);

// ==================== Tab nav ====================
document.querySelectorAll('.tb').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tb').forEach(b => b.classList.remove('on'));
    document.querySelectorAll('.pg').forEach(p => p.classList.remove('on'));
    btn.classList.add('on');
    document.getElementById('pg-' + btn.dataset.tab).classList.add('on');
    window.scrollTo({top:0,behavior:'instant'});
  });
});

// ==================== Cover meta + page-hd meta ====================
(function renderMeta() {
  const m = DATA.meta;
  document.getElementById('cover-meta').innerHTML = `
    <div class="chip">데이터 기간 <span>${m.data_period}</span></div>
    <div class="chip">분석 지점 <span>${m.branches.length}개</span></div>
    <div class="chip">캠페인 목적 <span>${m.campaign_objective}</span></div>
  `;
  const periodEl = document.getElementById('meta-period');
  if (periodEl) periodEl.textContent = m.data_period;
  const brEl = document.getElementById('meta-branches');
  if (brEl) brEl.textContent = m.branches.length + '개 지점 (' + m.branches.join('·') + ')';
})();

// ==================== 01 Executive Summary ====================
(function renderExecSummary() {
  const t = DATA.june_targets.overall_targets;
  const cp = DATA.conversion_perspective || {};
  const branches = DATA.meta.branches;
  const cs = DATA.consulting_signals || {by_branch:{}, group_impact:{}};
  const at = DATA.action_table || {};
  const gs = at.groups_summary || {};
  const budget = DATA.budget || {baseline:{},june_scenarios:{optimistic:{},recommended:{},conservative:{}},by_branch:{},june_recommended_by_branch:{},june_recommended_total:0};
  const bb = budget.baseline || {};
  const recTotal = budget.june_recommended_total || 0;
  const recDelta = bb.avg_monthly_cost ? ((recTotal - bb.avg_monthly_cost) / bb.avg_monthly_cost * 100) : 0;

  // 1.1 핵심 KPI
  const conv = t.conversions || {};
  const cpa = t.cpa || {};
  const stretch = t.conversions_ambitious || {};
  const primaryHtml = `
    <div class="kpi-primary">
      <div class="kpi-stretch">상향 ${(stretch.value || 0).toLocaleString()}건</div>
      <div class="kpi-primary-lbl">전환수 · 기본 목표</div>
      <div class="kpi-primary-val">${(conv.value || 0).toLocaleString()}<span class="kpi-primary-unit">건</span></div>
      <div class="kpi-primary-sub">베스트월 <strong>${conv.source_month || '-'}</strong> · 전 기간 비교 <strong>${cp.overall ? cp.overall.conversions.toLocaleString() + '건' : '-'}</strong></div>
    </div>
    <div class="kpi-primary">
      <div class="kpi-primary-lbl">CPA 가드레일 · 평균</div>
      <div class="kpi-primary-val">${(cpa.value || 0).toLocaleString()}<span class="kpi-primary-unit">원</span></div>
      <div class="kpi-primary-sub">베스트월 <strong>${cpa.source_month || '-'}</strong> · 전 기간 평균 <strong>${cp.overall ? cp.overall.cpa.toLocaleString() + '원' : '-'}</strong></div>
    </div>
    <div class="kpi-primary" style="border-top-color:var(--funnel)">
      <div class="kpi-stretch" style="color:var(--funnel);background:rgba(129,140,248,.10)">정상월 평균 ${bb.avg_monthly_cost ? Math.round(bb.avg_monthly_cost/10000).toLocaleString() + '만' : '-'}</div>
      <div class="kpi-primary-lbl" style="color:var(--funnel)">6월 권장 예산</div>
      <div class="kpi-primary-val">${recTotal ? Math.round(recTotal/10000).toLocaleString() : '-'}<span class="kpi-primary-unit">만원</span></div>
      <div class="kpi-primary-sub">정상월 평균 대비 <strong style="color:${recDelta > 0 ? 'var(--t1)' : (recDelta < 0 ? 'var(--red)' : 'var(--tx2)')}">${recDelta > 0 ? '+' : ''}${recDelta.toFixed(1)}%</strong> · 시나리오 보수 ${budget.june_scenarios.conservative.total_budget ? Math.round(budget.june_scenarios.conservative.total_budget/10000).toLocaleString() + '만' : '-'} ~ 낙관 ${budget.june_scenarios.optimistic.total_budget ? Math.round(budget.june_scenarios.optimistic.total_budget/10000).toLocaleString() + '만' : '-'}</div>
    </div>
  `;
  document.getElementById('kpi-primary').innerHTML = primaryHtml;

  // 1.2 퍼널 KPI
  const funnelHtml = ['cpm','ctr','cvr'].map(m => {
    const tg = t[m] || {};
    const peer = (DATA.root_cause && DATA.root_cause.peer_avg) || {};
    const val = m === 'cpm' ? fmt(tg.value) + '원' : fmtPct(tg.value);
    const peerVal = m === 'cpm' ? fmt(peer.cpm) + '원' : fmtPct(peer[m]);
    return `<div class="kpi-funnel">
      <div class="kpi-funnel-lbl">${m.toUpperCase()} 목표</div>
      <div class="kpi-funnel-val">${val}</div>
      <div class="kpi-funnel-sub">베스트월 ${tg.source_month || '-'} · 전 기간 평균 ${peerVal}</div>
    </div>`;
  }).join('');
  document.getElementById('kpi-funnel').innerHTML = funnelHtml;

  // 1.3 지점 그룹별 운영 방향
  const grpImpact = cs.group_impact || {};
  const judgements = [
    {
      key: 'expand', tag: 'B 그룹 · 예산 확대', cl: 'expand',
      decision: '예산 확대 운영',
      target: '대상 지점 · <strong>' + (gs.B || []).join(' · ') + '</strong>',
      basis: 'CPA 목표 대비 양호하며 전환 기여도 상위',
      action: '광고 그룹 예산 +5~10% 점진 증액. CPM·CPA 일일 모니터링 병행',
      gate: 'CPA 목표 대비 +10% 초과 또는 CPM +15% 상승 시 증액 중단',
      impact: grpImpact.B ? `+${grpImpact.B.min}~${grpImpact.B.max}건` : '-',
    },
    {
      key: 'improve', tag: 'A 그룹 · 효율 개선', cl: 'improve',
      decision: '효율 개선 우선',
      target: '대상 지점 · <strong>' + (gs.A || []).join(' · ') + '</strong>',
      basis: 'CVR 병목 또는 CPA 평균 +20% 이상',
      action: 'CVR 원인 진단(소재↔랜딩 hero 정합성, 5단계 폼 이탈) 선행. 예산 증액 보류',
      gate: 'CVR 목표 갭 -5% 이내 회복 전까지 광고 그룹 예산 동결',
      impact: grpImpact.A ? `+${grpImpact.A.min}~${grpImpact.A.max}건` : '-',
    },
    {
      key: 'stabilize', tag: 'C 그룹 · 신규 안정화', cl: 'stabilize',
      decision: '신규 학습 안정화',
      target: '대상 지점 · <strong>' + (gs.C || []).join(' · ') + '</strong>',
      basis: '5월 신규 운영, 학습 기간 14일 미만',
      action: '학습 모수 확보를 위해 신뢰형 소재 중심으로 안정 학습',
      gate: 'CPA가 전 지점 평균 +15% 초과 시 학습 보류',
      impact: grpImpact.C ? `+${grpImpact.C.min}~${grpImpact.C.max}건` : '-',
    },
  ];
  document.getElementById('judg-cards').innerHTML = judgements.map(j => `
    <div class="judg ${j.cl}">
      <div class="judg-tag">${j.tag}</div>
      <div class="judg-decision">${j.decision}</div>
      <div class="judg-target">${j.target}</div>
      <div class="judg-row"><div class="judg-row-lbl">판단 근거</div><div>${j.basis}</div></div>
      <div class="judg-row"><div class="judg-row-lbl">운영 액션</div><div>${j.action}</div></div>
      <div class="judg-row"><div class="judg-row-lbl">중단 조건</div><div>${j.gate}</div></div>
      <div class="judg-impact">기대 효과 ${j.impact}<span>· 갭 회복률 30~70% 가정 기준</span></div>
    </div>
  `).join('');

  // 1.4 지점별 전환수 막대 차트
  const cpBy = cp.by_branch || {};
  const convs = branches.map(b => (cpBy[b] && cpBy[b].period_total) ? cpBy[b].period_total.conversions : 0);
  const colorByGrade = {
    'efficient': 'rgba(52,211,153,.85)',
    'average': 'rgba(56,189,248,.7)',
    'inefficient': 'rgba(248,113,113,.75)',
    'new': 'rgba(167,139,250,.65)',
    'unknown': 'rgba(82,82,91,.6)',
  };
  const bgColors = branches.map(b => colorByGrade[(cpBy[b] && cpBy[b].cpa_grade) ? cpBy[b].cpa_grade.grade : 'unknown']);
  new Chart(document.getElementById('branchConvChart'), {
    type: 'bar',
    data: { labels: branches, datasets: [{ data: convs, backgroundColor: bgColors }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => {
          const b = ctx.label;
          const d = cpBy[b];
          if (!d || !d.period_total) return `${b}: 신규 지점`;
          return `${b}: 전환 ${d.period_total.conversions}건 · CPA ${d.period_total.cpa.toLocaleString()}원 · ${d.cpa_grade.label}`;
        } } },
      },
      scales: {
        x: { ticks: { color: CHART_TEXT }, grid: { color: CHART_GRID } },
        y: { ticks: { color: CHART_TEXT }, grid: { color: CHART_GRID }, title: { display: true, text: '전환 수', color: CHART_TEXT } },
      },
    },
  });

  // Lead 갱신 (overview)
  const efficient = branches.filter(b => cpBy[b] && cpBy[b].cpa_grade && cpBy[b].cpa_grade.grade === 'efficient');
  const inefficient = branches.filter(b => cpBy[b] && cpBy[b].cpa_grade && cpBy[b].cpa_grade.grade === 'inefficient');
  const newB = branches.filter(b => cpBy[b] && cpBy[b].cpa_grade && cpBy[b].cpa_grade.grade === 'new');
  const leadEl = document.getElementById('overview-lead');
  if (leadEl) leadEl.innerHTML = `현재 운영 분포 — <strong>효율 우수</strong> ${efficient.length}개 지점, <strong>효율 부진</strong> ${inefficient.length}개 지점, <strong>신규</strong> ${newB.length}개 지점입니다. 색상은 CPA 효율 등급(전 지점 평균 ±15%)을 의미합니다.`;
})();

// ==================== 02 성과 진단 ====================
(function renderDiagnosis() {
  const branches = DATA.meta.branches;
  const cs = (DATA.consulting_signals && DATA.consulting_signals.by_branch) || {};
  const at = DATA.action_table || {};
  const rowByBranch = Object.fromEntries((at.rows || []).map(r => [r.branch, r]));

  // 2.1 매트릭스
  const heads = ['지점', '그룹', 'CPM', 'CTR', 'CVR', '핵심 병목', '6월 처방'];
  const fcell = (s) => s ? statusBadge(s.status) : statusBadge('na');
  let trs = '';
  let bottleneckCount = {CPM: 0, CTR: 0, CVR: 0, new: 0, none: 0};
  branches.forEach(b => {
    const bs = cs[b] || {};
    const ar = rowByBranch[b] || {};
    const grp = groupKey(ar.group);
    const fs = bs.funnel_status || {};
    const bt = bs.bottleneck_type || 'none';
    bottleneckCount[bt] = (bottleneckCount[bt] || 0) + 1;
    let prescription = '';
    if (bt === 'new') prescription = '신규 학습 안정화';
    else if (bt === 'CPM') prescription = '오디언스 폭 확장 · 고비용 타겟 축소';
    else if (bt === 'CTR') prescription = '후킹 강화 · 신규 소재 변주';
    else if (bt === 'CVR') prescription = 'CVR 병목 우선 진단 · 랜딩·CTA 점검';
    else prescription = grp === 'B' ? 'CPA 유지하며 증액' : '현 운영 유지';
    trs += `<tr>
      <td class="lbl">${b}</td>
      <td>${groupBadge(grp)}</td>
      <td>${fcell(fs.cpm)}</td>
      <td>${fcell(fs.ctr)}</td>
      <td>${fcell(fs.cvr)}</td>
      <td><span class="bd bd-${bt === 'new' ? 'new' : (bt === 'none' ? 'good' : 'bad')}">${bt === 'none' ? '없음' : (bt === 'new' ? '신규' : bt)}</span></td>
      <td class="txt">${prescription}</td>
    </tr>`;
  });
  document.getElementById('diag-matrix').innerHTML = `<thead><tr>${heads.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${trs}</tbody>`;

  // 2.1 lead
  const topBottleneck = Object.entries(bottleneckCount).filter(([k,v]) => k !== 'none' && k !== 'new' && v > 0).sort((a,b) => b[1]-a[1])[0];
  const leadEl = document.getElementById('diag-lead-21');
  if (leadEl) {
    const cvrIssue = bottleneckCount.CVR || 0;
    const ctrIssue = bottleneckCount.CTR || 0;
    const cpmIssue = bottleneckCount.CPM || 0;
    leadEl.innerHTML = `진단 결과, 병목 분포는 CVR ${cvrIssue}개 · CTR ${ctrIssue}개 · CPM ${cpmIssue}개 · 신규 ${bottleneckCount.new || 0}개 지점입니다. ${topBottleneck ? `<strong>${topBottleneck[0]} 병목 ${topBottleneck[1]}개 지점</strong>이 6월 우선 처방 대상으로 판단됩니다.` : '특이 병목 없이 안정 운영 상태입니다.'}`;
  }

  // 2.2 사분면 차트
  const cp = DATA.conversion_perspective || {};
  const cpBy = cp.by_branch || {};
  const scatterData = branches.map(b => {
    const d = cpBy[b];
    if (!d || !d.period_total) return null;
    const grade = (d.cpa_grade && d.cpa_grade.grade) || 'average';
    const color = {
      'efficient': 'rgba(52,211,153,.7)',
      'average': 'rgba(56,189,248,.6)',
      'inefficient': 'rgba(248,113,113,.65)',
    }[grade] || 'rgba(167,139,250,.6)';
    return {
      label: b,
      data: [{ x: d.period_total.cpa || 0, y: d.period_total.conversions || 0, r: Math.max(Math.sqrt((d.period_total.cost || 0) / 200000), 6) }],
      backgroundColor: color, borderColor: color.replace('.7','1').replace('.6','1').replace('.65','1'),
    };
  }).filter(x => x);
  const pointLabelPlugin = {
    id: 'pointLabel',
    afterDatasetsDraw(chart) {
      const ctx = chart.ctx;
      chart.data.datasets.forEach((ds, i) => {
        const meta = chart.getDatasetMeta(i);
        meta.data.forEach((point) => {
          if (!point) return;
          const r = point.options.radius || 6;
          ctx.save();
          ctx.fillStyle = CHART_STRONG;
          ctx.font = 'bold 11px "Pretendard Variable", Pretendard, sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'bottom';
          ctx.fillText(ds.label, point.x, point.y - r - 4);
          ctx.restore();
        });
      });
    },
  };
  new Chart(document.getElementById('quadChart'), {
    type: 'bubble',
    data: { datasets: scatterData },
    plugins: [pointLabelPlugin],
    options: {
      responsive: true, maintainAspectRatio: false,
      layout: { padding: { top: 24, right: 24, left: 12, bottom: 12 } },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: 전환 ${ctx.raw.y}건, CPA ${ctx.raw.x.toLocaleString()}원` } },
      },
      scales: {
        x: { ticks: { color: CHART_TEXT }, grid: { color: CHART_GRID }, title: { display: true, text: '평균 CPA (원) · 우측일수록 비쌈', color: CHART_TEXT } },
        y: { ticks: { color: CHART_TEXT }, grid: { color: CHART_GRID }, title: { display: true, text: '전 기간 누적 전환수 · 위쪽일수록 많음', color: CHART_TEXT } },
      },
    },
  });

  // 2.3 히트맵
  const months = DATA.funnel_by_month.months;
  const data = DATA.funnel_by_month.by_month_branch;
  const colTemplate = `100px ${months.map(() => '1fr').join(' ')}`;
  function build(metric, direction, fmtFn) {
    let html = `<div class="hm-row" style="grid-template-columns:${colTemplate}">
      <div class="hm-lbl-cell" style="background:var(--s2);font-weight:700;color:var(--tx)">지점 \\ 월</div>
      ${months.map(m => `<div class="hm-val" style="font-weight:700;color:var(--tx);background:var(--s2)">${m.slice(5)}월</div>`).join('')}
    </div>`;
    branches.forEach(b => {
      const rowVals = months.map(m => data[m] && data[m][b] && data[m][b][metric] !== undefined ? data[m][b][metric] : null);
      html += `<div class="hm-row" style="grid-template-columns:${colTemplate}">
        <div class="hm-lbl-cell">${b}</div>
        ${rowVals.map(v => {
          const cls = heatClass(v, rowVals, direction);
          return `<div class="hm-val ${cls}">${fmtFn(v)}</div>`;
        }).join('')}
      </div>`;
    });
    return html;
  }
  document.getElementById('hm-cpm').innerHTML = build('cpm', 'low', v => v === null ? '-' : v.toLocaleString());
  document.getElementById('hm-ctr').innerHTML = build('ctr', 'high', v => v === null ? '-' : v.toFixed(2) + '%');
  document.getElementById('hm-cvr').innerHTML = build('cvr', 'high', v => v === null ? '-' : v.toFixed(2) + '%');

  // ============ 2.3.1 히트맵 변동 주원인 (Shapley 분해 카드) ============
  (function renderFunnelVariance(){
    const fv = DATA.funnel_variance;
    if (!fv) return;
    const fmtMetric = (m, v) => v === null || v === undefined ? '-'
      : (m === 'cpm' ? Math.round(v).toLocaleString() + '원' : v.toFixed(2) + '%');
    const fmtPP = (v) => (v >= 0 ? '+' : '') + v.toFixed(2) + '%p';
    const fmtSign = (v, suffix='%') => (v >= 0 ? '+' : '') + v.toFixed(1) + suffix;

    // overall trend 한 줄
    const t = fv.overall_trend || {};
    const trendParts = ['cpm','ctr','cvr'].map(m => {
      const tt = t[m]; if (!tt) return null;
      return `<strong style="color:var(--tx)">${m.toUpperCase()}</strong> ${tt.first_month.slice(5)}월 ${fmtMetric(m, tt.first_value)} → ${tt.last_month.slice(5)}월 ${fmtMetric(m, tt.last_value)} (<span class="${tt.delta_pct > 0 ? 'delta-up' : 'delta-down'}">${fmtSign(tt.delta_pct)}</span>)${tt.partial_flag_last ? ' <span style="color:var(--warn);font-size:10px">⚠️ 5월 부분월</span>' : ''}`;
    }).filter(Boolean);
    document.getElementById('fv-trend').innerHTML = `전 지점 평균 추이 · ${trendParts.join(' · ')}`;

    // 카드 렌더
    const cards = fv.cards || [];
    const grid = document.createElement('div');
    grid.className = 'fv-grid';
    cards.forEach(c => {
      const cardEl = document.createElement('div');
      const metricCl = c.metric === 'cvr' && c.direction === 'down' ? 'cvr-down' : c.metric;
      cardEl.className = `fv-card ${metricCl}`;

      const arrow = c.direction === 'up' ? '↑' : '↓';
      const metricLabel = c.metric.toUpperCase();
      const monthStr = c.month.slice(5) + '월';
      const baseStr = c.baseline.months.map(m => m.slice(5)+'월').join('·');

      // 헤더
      const hdr = `<div class="fv-hdr">
        <div class="fv-hdr-branch">${c.branch}</div>
        <div class="fv-hdr-metric">${metricLabel} ${arrow}</div>
        ${c.partial_month_flag ? '<div class="fv-hdr-partial">⚠️ 부분월</div>' : ''}
        <div class="fv-hdr-delta">${fmtSign(c.delta_pct)}</div>
      </div>`;

      // 메타 (월 수치 + vs prev)
      const vsPrev = c.vs_prev_month_pct !== null && c.vs_prev_month_pct !== undefined ? ` <span class="fv-meta-trend">(vs 전월 ${fmtSign(c.vs_prev_month_pct)})</span>` : '';
      const meta = `<div class="fv-meta">
        ${monthStr} ${fmtMetric(c.metric, c.month_value)} · ${baseStr} 평균 ${fmtMetric(c.metric, c.baseline.value)}${vsPrev}
      </div>`;

      // 분해
      const d = c.decomposition;
      const mixTop = (c.mix_drivers && c.mix_drivers[0]) || null;
      const withinTop = (c.within_drivers && c.within_drivers[0]) || null;
      let decompRows = '';
      // mix 라인
      let mixDetail = '';
      if (mixTop) {
        const dir = mixTop.share_delta_pp >= 0 ? '증가' : '감소';
        mixDetail = `${mixTop.type} 비중 ${fmtPP(mixTop.share_delta_pp)} ${dir}`;
        if (mixTop.type_metric_value !== null && mixTop.basket_metric_value) {
          mixDetail += ` · ${mixTop.type} ${fmtMetric(c.metric, mixTop.type_metric_value)} vs 평균 ${fmtMetric(c.metric, mixTop.basket_metric_value)}`;
        }
      }
      decompRows += `<div class="fv-decomp-row">
        <div class="fv-decomp-lbl">구성비 효과</div>
        <div class="fv-decomp-val">${d.mix_contribution_pct.toFixed(0)}%</div>
        <div class="fv-decomp-detail">${mixDetail || '소재유형 비중 변화 미미'}</div>
      </div>`;
      // within 라인
      let withinDetail = '';
      if (withinTop) {
        const dir = withinTop.metric_delta_pct >= 0 ? '상승' : '하락';
        const absStr = c.metric === 'cpm'
          ? `${withinTop.metric_delta_abs >= 0 ? '+' : ''}${Math.round(withinTop.metric_delta_abs).toLocaleString()}원`
          : `${fmtPP(withinTop.metric_delta_abs)}`;
        withinDetail = `${withinTop.type} 자체 ${absStr} ${dir} (${fmtSign(withinTop.metric_delta_pct)})`;
      }
      decompRows += `<div class="fv-decomp-row">
        <div class="fv-decomp-lbl">단위성과 효과</div>
        <div class="fv-decomp-val">${d.within_contribution_pct.toFixed(0)}%</div>
        <div class="fv-decomp-detail">${withinDetail || '동일 유형 내 변화 미미'}</div>
      </div>`;
      // interaction (Shapley라 항상 0 — 본문 생략)
      const decomp = `<div class="fv-decomp">${decompRows}</div>`;

      // aux signals
      let auxHtml = '';
      if (c.aux_signals && c.aux_signals.length) {
        const auxRows = c.aux_signals.map(s => {
          if (s.key === 'new_resumed_share') {
            return `<div class="fv-aux-row">신규·재개 광고 노출 비중 <strong>${s.value_pct.toFixed(1)}%</strong> (신규 ${s.new_ad_count}개·재개 ${s.resumed_ad_count}개)</div>`;
          }
          if (s.key === 'off_impact') {
            return `<div class="fv-aux-row">우수 광고 OFF — 직전월 전환 비중 <strong>${s.prev_conversion_share_pct.toFixed(1)}%</strong>를 차지하던 광고 ${s.off_creative_count}개가 OFF</div>`;
          }
          if (s.key === 'avg_daily_cost') {
            return `<div class="fv-aux-row">일평균 비용 <strong>${fmtSign(s.value_pct)}</strong> (${s.baseline_daily_cost.toLocaleString()}원 → ${s.current_daily_cost.toLocaleString()}원)</div>`;
          }
          if (s.key === 'active_ad_count') {
            return `<div class="fv-aux-row">활성 광고 수 <strong>${fmtSign(s.value_pct)}</strong> (${s.baseline_count}개 → ${s.current_count}개)</div>`;
          }
          return '';
        }).filter(Boolean).join('');
        if (auxRows) auxHtml = `<div class="fv-aux">${auxRows}</div>`;
      } else {
        auxHtml = `<div class="fv-aux"></div>`; // grid row 유지
      }

      // 운영 함의
      const impCls = c.implication_strength === 'soft' ? 'fv-imp soft' : 'fv-imp';
      const imp = `<div class="${impCls}"><strong>운영 함의 · </strong>${c.operation_implication}</div>`;

      cardEl.innerHTML = hdr + meta + decomp + auxHtml + imp;
      // 6번째 자식 자리(혹시 부족) — grid subgrid에 맞춰 자식 수 6개 유지: header / meta / decomp / aux / imp → 5개
      // aligned-6 격자는 우리가 자식 6개를 요구하지 않음. fv-grid에서 grid-template-rows:repeat(6,auto)지만 자식 5개여도 5 row 사용.
      // 명세상 'aligned-N'은 정확한 N. 카드 자식 = 5라 grid-row span도 5로 맞춤.
      cardEl.style.gridRow = `span 5`;
      grid.appendChild(cardEl);
    });
    // 부모 grid template rows도 자식 수에 맞춰 5로 보정
    grid.style.gridTemplateRows = 'repeat(5,auto)';
    const wrap = document.getElementById('fv-cards');
    wrap.innerHTML = '';
    if (cards.length === 0) {
      wrap.innerHTML = `<div class="appendix-card" style="text-align:center;padding:24px">변동 임계를 통과한 셀이 없습니다. 모든 지점이 안정 운영 구간입니다.</div>`;
    } else {
      wrap.appendChild(grid);
    }

    // weak appendix
    const weak = fv.appendix_weak_cells || [];
    if (weak.length) {
      const weakWrap = document.getElementById('fv-weak-wrap');
      weakWrap.style.display = 'block';
      document.getElementById('fv-weak').innerHTML = weak.map(w =>
        `<div style="display:flex;align-items:baseline;gap:8px;padding:5px 0;border-bottom:1px dashed var(--bd);font-size:11px">
          <span style="font-weight:700;min-width:48px">${w.branch}</span>
          <span style="font-weight:700;color:var(--tx2);min-width:60px">${w.metric.toUpperCase()} ${w.delta_pct >= 0 ? '↑' : '↓'} ${fmtSign(w.delta_pct)}</span>
          <span style="font-family:'DM Mono',monospace;color:var(--tx2);min-width:64px">${w.month.slice(5)}월</span>
          <span style="color:var(--tx2);font-size:10.5px">${w.reason}</span>
        </div>`
      ).join('');
    }
  })();

  // Appendix A.1 - conv summary
  const sumHeads = ['지점','누적 전환','전환 비중','평균 CPA','일평균 전환','효율 등급','집행일수'];
  let sumTrs = '';
  branches.forEach(b => {
    const d = cpBy[b];
    const pt = d && d.period_total;
    if (!pt) {
      const partial = d && d.partial_may;
      const partialStr = partial ? `5월 부분 ${partial.conversions}건 / CPA ${fmt(partial.cpa)}원` : '운영 데이터 없음';
      sumTrs += `<tr><td class="lbl">${b} ${statusBadge('new', '신규')}</td><td colspan="5" class="txt muted" style="text-align:center">${partialStr} (참고)</td><td>${statusBadge('new', '신규 지점')}</td></tr>`;
      return;
    }
    const g = d.cpa_grade;
    const ratio = g.ratio_pct;
    const ratioStr = (ratio !== null && ratio !== undefined) ? ` ${ratio > 0 ? '+' : ''}${ratio.toFixed(0)}%` : '';
    sumTrs += `<tr>
      <td class="lbl">${b}</td>
      <td><strong>${fmt(pt.conversions)}</strong>건</td>
      <td>${d.conv_share_pct}%</td>
      <td>${fmt(pt.cpa)}원</td>
      <td>${pt.daily_conversions}건</td>
      <td>${statusBadge({efficient:'good',average:'mid',inefficient:'bad',new:'new'}[g.grade], g.label + ratioStr)}</td>
      <td>${pt.days_active}일</td>
    </tr>`;
  });
  document.getElementById('conv-summary-tbl').innerHTML = `<thead><tr>${sumHeads.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${sumTrs}</tbody>`;

  // Appendix A.2 - peer avg + comparison
  const rc = DATA.root_cause;
  const peer = rc.peer_avg;
  document.getElementById('root-peer-avg-tbl').innerHTML = `
    <thead><tr><th>지표</th><th>CPM</th><th>CTR</th><th>CVR</th><th>CPA</th><th>LPV/클릭</th></tr></thead>
    <tbody><tr>
      <td class="lbl">전 지점 평균 (전 기간 2~5월 누적)</td>
      <td>${fmt(peer.cpm)}원</td><td>${fmtPct(peer.ctr)}</td><td>${fmtPct(peer.cvr)}</td><td>${fmt(peer.cpa)}원</td><td>${fmtPct(peer.lpv_rate)}</td>
    </tr></tbody>
  `;
  const cmpHeads = ['지점','CPM','CTR','CVR','CPA','LPV/클릭'];
  let cmpTrs = '';
  branches.forEach(b => {
    const bd = rc.by_branch[b];
    if (!bd.is_diagnosable) { cmpTrs += `<tr><td class="lbl">${b}</td><td colspan="5" class="txt muted" style="text-align:center">전 기간 데이터 부족 (신규 지점)</td></tr>`; return; }
    const pt = bd.period_total;
    const cell = (val, peerVal, dir, fmtFn) => {
      if (val === null || val === undefined || !peerVal) return '<td>-</td>';
      const ratio = val / peerVal;
      let cls = '';
      if (dir === 'low_is_weak') cls = ratio <= 0.85 ? 'delta-down' : (ratio >= 1.15 ? 'delta-up' : '');
      else cls = ratio >= 1.15 ? 'delta-down' : (ratio <= 0.85 ? 'delta-up' : '');
      const delta = ((ratio - 1) * 100).toFixed(0);
      const sign = delta > 0 ? '+' : '';
      return `<td class="${cls}">${fmtFn(val)} <span style="font-size:10px;color:var(--tx2)">(${sign}${delta}%)</span></td>`;
    };
    cmpTrs += `<tr>
      <td class="lbl">${b}</td>
      ${cell(pt.cpm, peer.cpm, 'high_is_weak', v => fmt(v) + '원')}
      ${cell(pt.ctr, peer.ctr, 'low_is_weak', fmtPct)}
      ${cell(pt.cvr, peer.cvr, 'low_is_weak', fmtPct)}
      ${cell(pt.cpa, peer.cpa, 'high_is_weak', v => fmt(v) + '원')}
      ${cell(pt.lpv_rate, peer.lpv_rate, 'low_is_weak', fmtPct)}
    </tr>`;
  });
  document.getElementById('root-comparison-tbl').innerHTML = `<thead><tr>${cmpHeads.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${cmpTrs}</tbody>`;

  // Appendix A.3 - 약점 진단
  let diagHtml = '';
  branches.forEach(b => {
    const bd = rc.by_branch[b];
    if (!bd.is_diagnosable) { diagHtml += `<div class="appendix-card" style="margin-bottom:8px"><div class="card-title">${b} ${statusBadge('new','신규')}</div><div class="muted">전 기간 데이터 없음 - 6월 운영 후 다음 달 재진단 권장</div></div>`; return; }
    const weaknesses = bd.peer_weaknesses || [];
    const items = weaknesses.length > 0
      ? weaknesses.map(w => `<div style="background:var(--s2);border-radius:5px;padding:8px 12px;margin-bottom:6px;border-left:3px solid var(--warn)"><div style="font-size:12px;font-weight:700;color:var(--warn)">${w.label}</div><div style="font-size:11px;color:var(--tx2);font-family:'DM Mono',monospace;margin-top:3px">${w.evidence}</div><div style="font-size:10px;color:var(--tx2);margin-top:3px">→ ${w.action_hint}</div></div>`).join('')
      : `<div class="muted">전 지점 평균 대비 특이 약점 없음 - 예산 확대 후보</div>`;
    const trends = bd.trends || {};
    let trendHtml = '';
    ['cpm','ctr','cvr','cpa'].forEach(m => {
      const t = trends[m];
      if (!t) return;
      if (t.class === 'consistent_up' || t.class === 'consistent_down') {
        const color = t.class === 'consistent_up' ? (m === 'cpm' || m === 'cpa' ? 'var(--red)' : 'var(--t1)') : (m === 'cpm' || m === 'cpa' ? 'var(--t1)' : 'var(--red)');
        trendHtml += `<div style="font-size:10px;color:var(--tx2);margin:3px 0;padding-left:10px;border-left:2px solid ${color}">${m.toUpperCase()} 추세: <strong style="color:${color}">${t.label}</strong> (${t.first.toFixed(2)} → ${t.last.toFixed(2)})</div>`;
      }
    });
    diagHtml += `<div class="evidence-card" style="margin-bottom:8px;padding:14px 18px"><div class="card-title" style="margin-bottom:8px">${b}</div>${items}${trendHtml ? '<div style="margin-top:10px"><div style="font-size:10px;font-weight:700;color:var(--tx2);margin-bottom:4px">추세 가드레일 (정상월 2~4월 기준)</div>' + trendHtml + '</div>' : ''}</div>`;
  });
  document.getElementById('root-diag-list').innerHTML = diagHtml;

  // Appendix A.4 - 월별 전환
  const partialMonth = cp.partial_month;
  const monthHeads = ['지점', ...months.map(m => {
    const mm = m.slice(5);
    return m === partialMonth ? `<span style="color:var(--warn)">${mm}월</span><br><span style="font-size:9px;color:var(--warn)">중단·부분</span>` : `${mm}월`;
  }), '<span>전 기간 누적</span><br><span style="font-size:9px;color:var(--tx2);font-weight:400">2~5월</span>'];
  let mTrs = '';
  branches.forEach(b => {
    const d = cpBy[b];
    const cells = months.map(m => {
      const k = (d && d.monthly_history) ? d.monthly_history[m] : null;
      if (m === partialMonth) {
        const pm = d && d.partial_may;
        const val = pm ? fmt(pm.conversions) : '-';
        return `<td style="color:var(--warn);background:rgba(251,146,60,.05);font-style:italic">${val}</td>`;
      }
      return `<td>${k ? fmt(k.conversions) : '-'}</td>`;
    });
    const totalConv = (d && d.period_total) ? d.period_total.conversions : '-';
    mTrs += `<tr><td class="lbl">${b}</td>${cells.join('')}<td><strong>${totalConv === '-' ? '-' : fmt(totalConv)}</strong></td></tr>`;
  });
  document.getElementById('conv-monthly-tbl').innerHTML = `<thead><tr>${monthHeads.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${mTrs}</tbody>`;

  // ===== 2.4 비용·예산 효율 =====
  const budget = DATA.budget || {};
  const bb = budget.baseline || {};
  const bByB = budget.by_branch || {};
  const monthlyTotal = budget.monthly_total || {};

  // Lead
  const sortedByEff = branches.filter(b => bByB[b] && !bByB[b].no_data && !bByB[b].is_new_branch).sort((a, b) => (bByB[b].efficiency_ratio || 0) - (bByB[a].efficiency_ratio || 0));
  const goodList = sortedByEff.filter(b => bByB[b].efficiency_grade === 'good').slice(0, 3);
  const badList = sortedByEff.filter(b => bByB[b].efficiency_grade === 'bad').slice(0, 3).reverse();
  const leadBudgetEl = document.getElementById('budget-lead-24');
  if (leadBudgetEl) leadBudgetEl.innerHTML = `정상월 평균 월간 집행은 <strong>${bb.avg_monthly_cost ? bb.avg_monthly_cost.toLocaleString() : '-'}원</strong>이며, 100만원당 평균 전환은 <strong>${bb.avg_conv_per_million || '-'}건</strong>입니다. 비용 비중 대비 전환 비중을 비교하면 ${goodList.length > 0 ? `<strong style="color:var(--t1)">${goodList.join('·')}</strong>이 예산 효율 우수 그룹` : ''}${goodList.length > 0 && badList.length > 0 ? ', ' : ''}${badList.length > 0 ? `<strong style="color:var(--red)">${badList.join('·')}</strong>이 비용 대비 전환 회수가 부진한 그룹으로 확인됩니다` : ''}.`;

  // 월별 추이 차트
  const monthsBudget = Object.keys(monthlyTotal);
  const costs = monthsBudget.map(m => Math.round(monthlyTotal[m].cost / 10000));
  const convs2 = monthsBudget.map(m => monthlyTotal[m].conversions);
  const cpasArr = monthsBudget.map(m => monthlyTotal[m].cpa);
  const isPartialArr = monthsBudget.map(m => monthlyTotal[m].is_partial);
  new Chart(document.getElementById('monthlyBudgetChart'), {
    type: 'bar',
    data: {
      labels: monthsBudget.map((m, i) => isPartialArr[i] ? `${m.slice(5)}월*` : `${m.slice(5)}월`),
      datasets: [
        { type: 'bar', label: '비용 (만원)', data: costs, backgroundColor: months.map((_, i) => isPartialArr[i] ? 'rgba(251,146,60,.45)' : 'rgba(56,189,248,.7)'), yAxisID: 'y' },
        { type: 'line', label: '전환수', data: convs2, borderColor: '#34d399', backgroundColor: 'rgba(52,211,153,.1)', tension: 0.3, yAxisID: 'y1', pointRadius: 5, pointBackgroundColor: '#34d399', borderDash: isPartialArr[isPartialArr.length-1] ? undefined : [] },
        { type: 'line', label: 'CPA (원)', data: cpasArr, borderColor: '#f87171', tension: 0.3, yAxisID: 'y2', pointRadius: 4, pointBackgroundColor: '#f87171' },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: CHART_TEXT, font: { size: 10 } } } },
      scales: {
        x: { ticks: { color: CHART_TEXT }, grid: { color: CHART_GRID } },
        y: { type: 'linear', position: 'left', ticks: { color: '#38bdf8', font: { size: 10 } }, grid: { color: CHART_GRID }, title: { display: true, text: '비용 (만원)', color: '#38bdf8', font: { size: 10 } } },
        y1: { type: 'linear', position: 'right', ticks: { color: '#34d399', font: { size: 10 } }, grid: { drawOnChartArea: false }, title: { display: true, text: '전환', color: '#34d399', font: { size: 10 } } },
        y2: { display: false },
      },
    },
  });

  // 100만원당 전환수 비교 차트
  const cpmlBranches = branches.filter(b => bByB[b] && !bByB[b].no_data);
  const cpmlVals = cpmlBranches.map(b => bByB[b].conv_per_million || 0);
  const cpmlColors = cpmlBranches.map(b => {
    const g = bByB[b].efficiency_grade;
    return g === 'good' ? 'rgba(52,211,153,.75)' : (g === 'bad' ? 'rgba(248,113,113,.7)' : (g === 'new' ? 'rgba(167,139,250,.6)' : 'rgba(56,189,248,.55)'));
  });
  new Chart(document.getElementById('convPerMillionChart'), {
    type: 'bar',
    data: {
      labels: cpmlBranches,
      datasets: [
        { label: '100만원당 전환수', data: cpmlVals, backgroundColor: cpmlColors },
      ],
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        annotation: false,
        tooltip: { callbacks: { label: (ctx) => {
          const b = ctx.label;
          const bd = bByB[b] || {};
          return `${b}: ${ctx.parsed.x}건/100만원 · 효율 ${bd.efficiency_ratio || '-'} · ${bd.efficiency_label || ''}`;
        } } },
      },
      scales: {
        x: { ticks: { color: CHART_TEXT, font: { size: 10 } }, grid: { color: CHART_GRID }, title: { display: true, text: '100만원당 전환수', color: CHART_TEXT, font: { size: 10 } } },
        y: { ticks: { color: CHART_TEXT, font: { size: 10 } }, grid: { color: CHART_GRID } },
      },
    },
  });

  // 지점별 비용·전환 매칭 표 — 색상 다이어트 적용
  const beHeads = ['지점', '평균 월 집행', '100만원당 전환', '비용/전환 비중', '효율 지수', '등급', '6월 권장'];
  const rec = budget.june_recommended_by_branch || {};
  let beTrs = '';
  const gradeText = (grade, label) => {
    const cls = grade === 'good' ? 'good' : (grade === 'bad' ? 'bad' : (grade === 'new' ? 'new' : 'mid'));
    return `<span class="bd bd-${cls}">${(label || '').split(' (')[0]}</span>`;
  };
  branches.forEach(b => {
    const bd = bByB[b];
    if (!bd) return;
    if (bd.no_data) {
      beTrs += `<tr><td class="lbl">${b}</td><td colspan="6" class="txt muted" style="text-align:center">데이터 없음</td></tr>`;
      return;
    }
    if (bd.is_new_branch) {
      beTrs += `<tr>
        <td class="lbl">${b} <span class="bd bd-new" style="font-size:10px;margin-left:4px">신규</span></td>
        <td>5월 부분 ${fmt(bd.partial_may_cost)}원</td>
        <td colspan="3" class="txt muted">정상월 데이터 없음 · 학습 안정화 단계</td>
        <td>${gradeText('new','신규')}</td>
        <td>${fmt(rec[b] ? rec[b].recommended_june_budget : 0)}원</td>
      </tr>`;
      return;
    }
    const grade = bd.efficiency_grade;
    const deltaPct = rec[b] ? rec[b].delta_pct : null;
    const deltaInline = (deltaPct !== null && deltaPct !== undefined)
      ? ` <span class="gap-txt ${deltaPct > 0 ? 'up' : (deltaPct < 0 ? 'down' : 'flat')}">${deltaPct > 0 ? '+' : ''}${deltaPct.toFixed(1)}%</span>`
      : '';
    beTrs += `<tr>
      <td class="lbl">${b}</td>
      <td>${fmt(bd.avg_monthly_cost)}원</td>
      <td>${bd.conv_per_million || '—'}건</td>
      <td>${bd.cost_share_pct}% / ${bd.conv_share_pct}%</td>
      <td><strong>${bd.efficiency_ratio || '—'}</strong></td>
      <td>${gradeText(grade, bd.efficiency_label)}</td>
      <td>${fmt(rec[b] ? rec[b].recommended_june_budget : 0)}원${deltaInline}</td>
    </tr>`;
  });
  // 합계 행
  const sumRec = budget.june_recommended_total || 0;
  const sumDelta = bb.avg_monthly_cost ? ((sumRec - bb.avg_monthly_cost) / bb.avg_monthly_cost * 100) : 0;
  const sumDeltaInline = ` <span class="gap-txt ${sumDelta > 0 ? 'up' : (sumDelta < 0 ? 'down' : 'flat')}">${sumDelta > 0 ? '+' : ''}${sumDelta.toFixed(1)}%</span>`;
  beTrs += `<tr style="background:rgba(255,255,255,.025);border-top:2px solid var(--bd)">
    <td class="lbl">합계</td>
    <td>${fmt(bb.avg_monthly_cost)}원</td>
    <td>${bb.avg_conv_per_million || '—'}건</td>
    <td>100% / 100%</td>
    <td>—</td>
    <td class="muted">—</td>
    <td>${fmt(sumRec)}원${sumDeltaInline}</td>
  </tr>`;
  document.getElementById('budget-efficiency-tbl').innerHTML = `<thead><tr>${beHeads.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${beTrs}</tbody>`;
})();

// ==================== 03 6월 목표·액션 ====================
(function renderPlan() {
  const branches = DATA.meta.branches;
  const cs = (DATA.consulting_signals && DATA.consulting_signals.by_branch) || {};
  const at = DATA.action_table || {};
  const rowByBranch = Object.fromEntries((at.rows || []).map(r => [r.branch, r]));
  const targets = (DATA.june_targets.by_branch) || {};

  // 3.1 Master Table — 색상 다이어트 적용
  //  · 행 좌측 컬러바: 그룹(A/B/C) 표시
  //  · 갭%: 배지 ✕ → 인라인 작은 컬러 텍스트
  //  · 퍼널 상태: 양호=무색 텍스트 / 주의=주황 옅게 / 우려=빨강 옅게 (양호는 시선 X)
  //  · 우선순위: High만 강조, 나머지는 옅은 텍스트
  const heads = ['지점', '전환 목표', 'CPA 목표', 'CPM', 'CTR', 'CVR', '우선'];
  let trs = '';
  let highCount = 0, midCount = 0, lowCount = 0, newCount = 0;

  // 갭 인라인 텍스트 (배지 대체)
  const gapInline = (gap) => {
    if (gap === null || gap === undefined) return '';
    const cls = gap >= 0 ? 'up' : (gap >= -10 ? 'flat' : 'down');
    const sign = gap > 0 ? '+' : '';
    return ` <span class="gap-txt ${cls}">${sign}${gap.toFixed(1)}%</span>`;
  };
  // 퍼널 상태 셀 (양호는 색·시각 강조 없음, 부진만 시인성)
  const fcell2 = (s) => {
    const status = (s && s.status) || 'na';
    const label = {good:'양호',mid:'평균',warn:'주의',bad:'우려',na:'—',new:'신규'}[status] || status;
    return `<span class="bd bd-${status}">${label}</span>`;
  };

  branches.forEach(b => {
    const bs = cs[b] || {};
    const ar = rowByBranch[b] || {};
    const grp = groupKey(ar.group);
    const tg = (targets[b] || {}).targets || {};
    const pg = bs.primary_gap || {};
    const fs = bs.funnel_status || {};
    const pri = bs.priority_level || 'Mid';
    if (pri === 'High') highCount++;
    else if (pri === 'Mid') midCount++;
    else if (pri === 'Low') lowCount++;
    else newCount++;
    trs += `<tr class="r-${grp}">
      <td class="lbl">${b} <span class="bd bd-${grp}" style="font-size:10px;margin-left:4px">${grp}</span></td>
      <td>${tg.conversions ? tg.conversions.value.toLocaleString() + '건' : '—'}${gapInline(pg.conversions && pg.conversions.gap_pct)}</td>
      <td>${tg.cpa ? fmt(tg.cpa.value) + '원' : '—'}${gapInline(pg.cpa && pg.cpa.gap_pct)}</td>
      <td>${fcell2(fs.cpm)}</td>
      <td>${fcell2(fs.ctr)}</td>
      <td>${fcell2(fs.cvr)}</td>
      <td>${priorityBadge(pri)}</td>
    </tr>`;
  });
  document.getElementById('plan-master-tbl').innerHTML = `<thead><tr>${heads.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${trs}</tbody>`;
  const leadEl = document.getElementById('plan-lead-31');
  if (leadEl) leadEl.innerHTML = `9개 지점의 운영 우선순위 분포는 High ${highCount}개 · Mid ${midCount}개 · Low ${lowCount}개 · New ${newCount}개입니다. 행 좌측 컬러바는 그룹(<span style="color:var(--red)">A 효율 개선</span> · <span style="color:var(--t1)">B 예산 확대</span> · <span style="color:var(--pur)">C 신규 안정화</span>)을 의미하며, 전환 또는 CPA 갭이 음수(개선 필요)인 지점이 6월 처방 우선 대상입니다.`;

  // 3.2 Funnel Action Cards
  const peer = (DATA.root_cause && DATA.root_cause.peer_avg) || {};
  const funnelConfigs = [
    {
      key: 'cpm', label: 'CPM 병목', color: 'var(--red)',
      objective: '노출 단가 완화',
      signalFn: () => {
        const issues = branches.filter(b => cs[b] && cs[b].funnel_status && ['bad','warn'].includes(cs[b].funnel_status.cpm && cs[b].funnel_status.cpm.status));
        return `<strong>${issues.length}개 지점</strong>이 전 지점 평균(${fmt(peer.cpm)}원) 대비 +10% 이상 비쌈 · ${issues.join('·') || '없음'}`;
      },
      cause: '지점별 지역 타겟팅 구조 특성상 모수가 제한됨. 단일 광고 그룹에 좁은 지역+추가 조건이 결합되면 학습 부족으로 단가 상승. 피크 시간 경쟁 과열 가능성.',
      action: '<strong>오디언스 폭 확장은 광고 그룹 복제 OR 분리 방식</strong>으로 진행 (지역만 그룹 + 지역+관심사 그룹 별개 운영). 노출 위치 확장 (Pangle·Spark 추가), 시간대·요일 분산, 입찰 전략 점검(최대 전환 vs 비용 한도), 지점 인근 시·군까지 지역 범위 확장 검토. 단일 광고 그룹 내 관심사 AND 추가는 풀을 더 좁히므로 금지.',
      kpi: '7일 내 CPM 목표 회귀 (-10% 이상), CTR/CVR 급락 없음. 단 지역 캠페인 구조상 CPM 개선 폭은 제한적 — CTR/CVR로 보완 가능',
    },
    {
      key: 'ctr', label: 'CTR 병목', color: 'var(--blue)',
      objective: '클릭 반응 회복',
      signalFn: () => {
        const issues = branches.filter(b => cs[b] && cs[b].funnel_status && ['bad','warn'].includes(cs[b].funnel_status.ctr && cs[b].funnel_status.ctr.status));
        return `<strong>${issues.length}개 지점</strong>이 전 지점 평균(${fmtPct(peer.ctr)}) 대비 -10% 이상 낮음 · ${issues.join('·') || '없음'}`;
      },
      cause: '첫 3초 후킹 약화, 소재 피로 누적, 지점별 메시지 적합도 차이. 라이프사이클상 장기 노출 소재에서 자주 발생.',
      action: '고CTR 소재 재가공, 후킹 문구 변주 신규 제작, 낮은 CTR 소재 <strong>광고 단위 OFF</strong>. 후기형·결과수치형 메시지 우선. 동일 광고 그룹 내 신규 소재 ON / 저성과 OFF 교체로 운영 (예산은 광고 그룹 단위라 별도 조정 불필요)',
      kpi: 'CTR 목표 달성 + 클릭 볼륨 유지 (-15% 이내)',
    },
    {
      key: 'cvr', label: 'CVR 병목', color: 'var(--t1)',
      objective: '전환율 개선',
      signalFn: () => {
        const issues = branches.filter(b => cs[b] && cs[b].funnel_status && ['bad','warn'].includes(cs[b].funnel_status.cvr && cs[b].funnel_status.cvr.status));
        return `<strong>${issues.length}개 지점</strong>이 전 지점 평균(${fmtPct(peer.cvr)}) 대비 -10% 이상 낮음 · ${issues.join('·') || '없음'}. 광고 측 외 상담 응대·5단계 폼 이탈도 영향.`;
      },
      cause: '소재 메시지와 랜딩 hero("첫 달 9만원") 톤 불일치, 5단계 폼 이탈, 상담 응대 부재콜. 광고 단계만으로 풀 수 없는 지점이 있음.',
      action: '<strong>소재 단위 ON/OFF로만 운영</strong> (예산은 광고 그룹/지점 단위라 소재별 예산 조정 불가). 고CVR 소재 ON 유지·저CVR 소재 OFF, 광고 그룹 단위로 지점 예산 조정. <strong>A/B 검증은 광고 그룹 복제</strong>로 (3.5 가이드 참고). CVR 회복 전 지점 예산 증액 보류. 상담전환형 신규 소재로 hero 정합성 ↑',
      kpi: 'CVR 목표 달성 + CPA 전 지점 평균 수준 회귀',
    },
  ];
  document.getElementById('funnel-action-cards').innerHTML = funnelConfigs.map(c => `
    <div class="evidence-card" style="border-left:4px solid ${c.color}">
      <div class="card-title" style="color:${c.color};font-size:15px;margin-bottom:8px">${c.label}</div>
      <div style="font-size:11px;color:var(--tx2);font-weight:700;margin-bottom:10px;letter-spacing:.04em;text-transform:uppercase">6월 목표 · ${c.objective}</div>
      <div style="background:var(--s2);border-radius:5px;padding:8px 12px;margin-bottom:10px;font-size:11px;color:var(--tx);line-height:1.55"><strong style="color:${c.color}">관측 시그널.</strong> ${c.signalFn()}</div>
      <div style="font-size:11px;color:var(--tx);line-height:1.6;margin-bottom:10px"><strong>원인 해석.</strong> ${c.cause}</div>
      <div style="font-size:11px;color:var(--tx);line-height:1.6;margin-bottom:10px"><strong>실행 액션.</strong> ${c.action}</div>
      <div style="padding-top:10px;border-top:1px dashed var(--bd);font-size:11px;color:${c.color};line-height:1.5"><strong>검증 KPI.</strong> ${c.kpi}</div>
    </div>
  `).join('');

  // 3.3 그룹별 지점 처방 카드
  const byGroup = {A: [], B: [], C: []};
  (at.rows || []).forEach(r => byGroup[groupKey(r.group)].push(r));
  let cardsHtml = '';
  ['A','B','C'].forEach(g => {
    const list = byGroup[g] || [];
    if (list.length === 0) return;
    const def = ({A:'A. 효율 개선 우선',B:'B. 예산 확대 후보',C:'C. 신규 모니터링'}[g]) || g;
    const crit = ({A:'약점 심각도 큰 그룹 - CVR/CPA/CTR 등 약점 다발',B:'전반 효율 양호 - 단계 확대 후 전환 추가 확보 가능',C:'5월 신규 운영 지점 - 운영 패턴 안정화 우선'}[g]) || '';
    cardsHtml += `<div style="margin-bottom:24px"><div style="display:flex;align-items:baseline;gap:10px;margin-bottom:10px;padding:10px 14px;border-radius:6px;background:rgba(${g==='A'?'248,113,113':(g==='B'?'52,211,153':'167,139,250')},.08);border-left:4px solid var(--${g==='A'?'red':(g==='B'?'t1':'pur')})"><div style="font-size:14px;font-weight:800;color:var(--${g==='A'?'red':(g==='B'?'t1':'pur')})">${def}</div><div style="font-size:11px;color:var(--tx2)">${crit}</div></div>`;
    list.forEach(r => {
      const b = r.branch;
      const bs = cs[b] || {};
      const bt = bs.bottleneck_type || 'none';
      const guardrail = bs.guardrail || '-';
      const impact = bs.expected_impact;
      const impactStr = impact ? `+${impact.conversion_gain_min}~${impact.conversion_gain_max}건` : '-';
      const role = bs.creative_role || {};
      cardsHtml += `<div class="bp ${g}">
        <div class="bp-hdr">
          <div class="bp-name">${b}</div>
          ${groupBadge(g)}
          ${priorityBadge(bs.priority_level || 'Mid')}
          <div class="bp-meta">${r.period_summary || '-'}</div>
        </div>
        <div class="g2" style="gap:12px">
          <div>
            <div class="bp-section-lbl">진단 및 핵심 병목</div>
            <div style="font-size:12px;color:var(--tx);line-height:1.6"><span class="bd bd-${bt === 'new' ? 'new' : (bt === 'none' ? 'good' : 'bad')}">${bt === 'none' ? '없음' : (bt === 'new' ? '신규' : bt)}</span> · ${(r.diagnoses || []).join(' · ') || '특이 약점 없음'}</div>
          </div>
          <div>
            <div class="bp-section-lbl">권고 소재 역할</div>
            <div style="font-size:12px;color:var(--tx);line-height:1.6"><strong style="color:var(--pur)">${role.role || '-'}</strong> · ${role.reason || '-'}</div>
          </div>
        </div>
        <div class="bp-section">
          <div class="bp-section-lbl">6월 핵심 운영 액션</div>
          <div style="font-size:12px;color:var(--tx);line-height:1.65;background:rgba(129,140,248,.05);border-left:3px solid var(--acc);padding:8px 12px;border-radius:0 5px 5px 0">${r.headline || '-'}</div>
          ${(() => {
            const ti = r.creative_tier_inline || {tier1:[], tier4:[]};
            const t1 = (ti.tier1 || []).slice(0,2);
            const t4 = (ti.tier4 || []).slice(0,2);
            if (t1.length === 0 && t4.length === 0) return '';
            const t1Html = t1.length > 0
              ? `<div class="tier-inline"><span class="tier-inline-lbl">TIER1 (확대)</span>${t1.map(x => `<strong>${x.name}</strong>${x.cpa ? ` <span class="muted">(CPA ${fmt(x.cpa)}원·CVR ${fmtPct(x.cvr)})</span>` : ''}`).join(' · ')}</div>`
              : '';
            const t4Html = t4.length > 0
              ? `<div class="tier-inline" style="background:rgba(248,113,113,.06);border-left-color:var(--red)"><span class="tier-inline-lbl" style="color:var(--red)">TIER4 (OFF 우선)</span>${t4.map(x => `<strong>${x.name}</strong>${x.cpa ? ` <span class="muted">(CPA ${fmt(x.cpa)}원·CVR ${fmtPct(x.cvr)})</span>` : ''}`).join(' · ')}</div>`
              : '';
            return t1Html + t4Html + '<div style="font-size:10px;color:var(--tx2);margin-top:4px;text-align:right">전체 소재 분류는 Appendix D 참조</div>';
          })()}
        </div>
        <div class="g2" style="gap:12px;margin-top:10px">
          <div>
            <div class="bp-section-lbl">검증 KPI</div>
            <div style="font-size:11px;color:var(--tx2);line-height:1.55">${r.verify_kpi || '-'}</div>
          </div>
          <div>
            <div class="bp-section-lbl">중단 조건 (가드레일)</div>
            <div style="font-size:11px;color:var(--warn);line-height:1.55">${guardrail}</div>
          </div>
        </div>
        <div style="margin-top:10px;padding-top:10px;border-top:1px dashed var(--bd);display:flex;justify-content:space-between;font-size:11px"><span style="color:var(--tx2)">기대 효과 (갭 회복률 30~70% 가정)</span><strong style="color:var(--t1)">${impactStr}</strong></div>
      </div>`;
    });
    cardsHtml += `</div>`;
  });
  document.getElementById('branch-action-cards').innerHTML = cardsHtml;

  // B.2 요일별
  const wd = DATA.weekday_performance || {};
  const wdHeads = ['지점', '베스트 요일', '약한 요일', '권장 액션'];
  let wdTrs = '';
  const wdByBranch = wd.by_branch || {};
  branches.forEach(b => {
    const r = wdByBranch[b] || {};
    if (!r.best && !r.weak) {
      wdTrs += `<tr><td class="lbl">${b}</td><td colspan="3" class="txt muted" style="text-align:center">데이터 부족</td></tr>`;
      return;
    }
    const bs = r.best ? `${r.best.weekday}요일 · CPA ${fmt(r.best.cpa)}원` : '-';
    const ws = r.weak ? `${r.weak.weekday}요일 · CPA ${fmt(r.weak.cpa)}원` : '-';
    const action = r.best && r.weak ? `${r.best.weekday}요일 예산 +10%, ${r.weak.weekday}요일 -10% 조정 후 회복 여부 확인` : '데이터 충분도 확보 후 적용';
    wdTrs += `<tr><td class="lbl">${b}</td><td>${bs}</td><td>${ws}</td><td class="txt">${action}</td></tr>`;
  });
  document.getElementById('weekday-action-tbl').innerHTML = `<thead><tr>${wdHeads.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${wdTrs}</tbody>`;

  // ===== 3.4 6월 예산 시나리오 =====
  const budget = DATA.budget || {};
  const sc = budget.june_scenarios || {};
  const bb = budget.baseline || {};
  const recAll = budget.june_recommended_by_branch || {};
  const sumRec = budget.june_recommended_total || 0;
  const sumDelta = bb.avg_monthly_cost ? ((sumRec - bb.avg_monthly_cost) / bb.avg_monthly_cost * 100) : 0;

  const leadEl34 = document.getElementById('budget-lead-34');
  if (leadEl34) leadEl34.innerHTML = `6월 목표 달성을 위한 예산을 낙관 · 권장 · 보수 세 시나리오로 정리하였습니다. 권장 시나리오는 정상월 평균 집행을 기준으로 지점별 효율 등급에 따라 ±10% 범위에서 조정한 값입니다. 6월 권장 예산 합계는 <strong style="color:var(--primary)">${fmt(sumRec)}원</strong>으로, 정상월 평균 대비 <strong style="color:${sumDelta > 0 ? 'var(--t1)' : (sumDelta < 0 ? 'var(--red)' : 'var(--tx2)')}">${sumDelta > 0 ? '+' : ''}${sumDelta.toFixed(1)}%</strong> 수준입니다.`;

  const scenarioCards = [
    { key: 'optimistic', cl: 'var(--warn)', tag: '낙관' },
    { key: 'recommended', cl: 'var(--t1)', tag: '권장' },
    { key: 'conservative', cl: 'var(--blue)', tag: '보수' },
  ];
  document.getElementById('budget-scenarios').innerHTML = scenarioCards.map(c => {
    const s = sc[c.key] || {};
    return `<div class="evidence-card" style="border-left:4px solid ${c.cl}">
      <div style="font-size:10px;font-weight:800;color:${c.cl};letter-spacing:.06em;margin-bottom:6px;text-transform:uppercase">${c.tag}</div>
      <div class="card-title" style="font-size:14px;margin-bottom:8px">${(s.label || '').replace(/\(([^)]+)\)/, '<small style="font-weight:500;color:var(--tx2);font-size:11px"> $1</small>').replace('(','').replace(')','')}</div>
      <div style="font-size:22px;font-weight:900;font-family:'DM Mono',monospace;color:var(--tx);margin-bottom:6px">${fmt(s.total_budget)}원</div>
      <div style="font-size:11px;color:var(--tx2);margin-bottom:8px">예상 전환 <strong>${typeof s.expected_conv === 'number' ? s.expected_conv + '건' : (s.expected_conv || '-')}</strong></div>
      <div style="font-size:10.5px;color:var(--tx);line-height:1.55;padding-top:8px;border-top:1px dashed var(--bd)"><strong>전제 가정.</strong> ${s.assumption || '-'}</div>
      <div style="font-size:10.5px;color:var(--warn);line-height:1.55;margin-top:6px"><strong>운영 리스크.</strong> ${s.risk || '-'}</div>
    </div>`;
  }).join('');

  // 지점별 권장 예산 표 — 색상 다이어트 적용 + 행 좌측 컬러바
  const recHeads = ['지점', '평균 월 집행 (정상월)', '6월 권장', '증감', '근거'];
  let recTrs = '';
  branches.forEach(b => {
    const ar = rowByBranch[b] || {};
    const grp = groupKey(ar.group);
    const r = recAll[b];
    if (!r) return;
    const deltaPct = r.delta_pct;
    const deltaInline = (deltaPct !== null && deltaPct !== undefined)
      ? `<span class="gap-txt ${deltaPct > 0 ? 'up' : (deltaPct < 0 ? 'down' : 'flat')}" style="margin-left:0">${deltaPct > 0 ? '+' : ''}${deltaPct.toFixed(1)}%</span>`
      : '<span class="muted">—</span>';
    recTrs += `<tr class="r-${grp}">
      <td class="lbl">${b} <span class="bd bd-${grp}" style="font-size:10px;margin-left:4px">${grp}</span></td>
      <td>${fmt(r.base_avg_monthly_cost)}원</td>
      <td><strong>${fmt(r.recommended_june_budget)}원</strong></td>
      <td>${deltaInline}</td>
      <td class="txt muted">${r.reason}</td>
    </tr>`;
  });
  const sumDeltaInline = `<span class="gap-txt ${sumDelta > 0 ? 'up' : (sumDelta < 0 ? 'down' : 'flat')}" style="margin-left:0">${sumDelta > 0 ? '+' : ''}${sumDelta.toFixed(1)}%</span>`;
  recTrs += `<tr style="background:rgba(255,255,255,.025);border-top:2px solid var(--bd)">
    <td class="lbl">합계</td>
    <td>${fmt(bb.avg_monthly_cost)}원</td>
    <td><strong>${fmt(sumRec)}원</strong></td>
    <td>${sumDeltaInline}</td>
    <td class="txt muted">정상월 평균 ${fmt(bb.avg_monthly_cost)}원 → 6월 ${fmt(sumRec)}원</td>
  </tr>`;
  document.getElementById('budget-rec-tbl').innerHTML = `<thead><tr>${recHeads.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody class="tbl-master">${recTrs}</tbody>`;
  // tbl-master는 첫 칸 좌측 컬러바 표시용. 헤더 클래스 대신 tbody에 적용.

  // 3.5 A/B 우선 추천 지점 — budget 효율 양호 + 학습 모수(전환수 ≥ 50건/월) 충족
  const bbyB = (DATA.budget && DATA.budget.by_branch) || {};
  const abBranches = branches.filter(b => {
    const bd = bbyB[b];
    return bd && bd.efficiency_grade === 'good' && (bd.avg_monthly_conv || 0) >= 50;
  });
  const abEl = document.getElementById('ab-priority-branches');
  if (abEl) abEl.textContent = abBranches.length > 0 ? abBranches.join(' · ') : '효율 양호 지점 (모수 누적 후 재평가)';
})();

// ==================== 04 타겟팅·콘텐츠 실행안 ====================
(function renderExecPlan() {
  const branches = DATA.meta.branches;
  const cs = (DATA.consulting_signals && DATA.consulting_signals.by_branch) || {};
  const at = DATA.action_table || {};
  const rowByBranch = Object.fromEntries((at.rows || []).map(r => [r.branch, r]));
  const recBy = (DATA.recommendations && DATA.recommendations.by_branch) || {};
  const topBy = (DATA.top_creatives && DATA.top_creatives.by_branch) || {};
  const tgBy = (DATA.june_targets.by_branch) || {};

  // 소재 역할 추천 룰 (병목 기반, 랜딩 hero "9만원 할인" 정합성 고려)
  const roleForFunnel = {
    cpm: { role: '할인혜택형', action: '광고 그룹 복제 OR 분리 · 노출 위치·시간대 분산 (지역+관심사 AND 추가 금지)' },
    ctr: { role: '후기형', action: '후기·결과수치 신규 ON · 저성과 광고 OFF (광고 그룹 내 교체)' },
    cvr: { role: '상담전환형', action: '소재 ↔ 랜딩 hero 정합성 · 5단계 폼 이탈 점검 · 광고 그룹 예산 증액 보류' },
  };

  // 추천 소재 picker (병목 기반 + recommendations fallback)
  const pickCreativeForFunnel = (branch, funnel) => {
    const rec = recBy[branch] || {};
    const top = topBy[branch] || {};
    // 1. 우선 recommendations.keep[0]
    if (rec.keep && rec.keep.length > 0) return { name: rec.keep[0].creative_name, source: '본인 우수' };
    // 2. 해당 퍼널 TOP
    const arr = top[funnel] || [];
    if (arr.length > 0) return { name: arr[0].creative_name, source: `${funnel.toUpperCase()} TOP` };
    return null;
  };

  // 4.1 통합 실행 매트릭스
  const heads = ['지점', '우선', 'CPM', 'CTR', 'CVR', '소재 역할', '6월 콘텐츠'];
  let trs = '';
  const fcellHtml = (branch, funnel) => {
    const bs = cs[branch] || {};
    const fs = (bs.funnel_status || {})[funnel] || {};
    const status = fs.status || 'na';
    const isBottleneck = (bs.bottleneck_type || '').toLowerCase() === funnel;
    let action = '유지';
    let role = '';
    if (status === 'bad' || status === 'warn') {
      const r = roleForFunnel[funnel];
      action = r.action;
      role = r.role;
    }
    const pick = isBottleneck ? pickCreativeForFunnel(branch, funnel) : null;
    const cellCls = (status === 'good' || status === 'mid') ? 'good' : (status === 'warn' ? 'warn' : (status === 'bad' ? 'bad' : ''));
    return `<td class="fcell ${cellCls}">
      <div class="fcell-row">${statusBadge(status)}</div>
      <div class="fcell-action">${action}</div>
      ${role ? `<div class="fcell-role"><strong>${role}</strong></div>` : ''}
      ${pick ? `<div class="fcell-kpi">${pick.name}</div>` : ''}
    </td>`;
  };
  branches.forEach(b => {
    const bs = cs[b] || {};
    const ar = rowByBranch[b] || {};
    const grp = groupKey(ar.group);
    const role = bs.creative_role || {};
    const rec = recBy[b] || {};
    const contentBrief = [];
    // 가로 스크롤 + 넓은 컬럼이라 잘림 해제 — 줄바꿈으로 자연스럽게 펼침
    if (rec.keep && rec.keep[0]) contentBrief.push(`<span style="color:var(--t1);font-weight:700">유지</span> ${rec.keep[0].creative_name}`);
    if (rec.expand && rec.expand[0]) contentBrief.push(`<span style="color:var(--warn);font-weight:700">확대</span> ${rec.expand[0].creative_name}`);
    if (rec.new_intro && rec.new_intro[0]) contentBrief.push(`<span style="color:var(--acc);font-weight:700">신규</span> ${rec.new_intro[0].creative_name}`);
    trs += `<tr class="r-${grp}">
      <td class="lbl">${b} <span class="bd bd-${grp}" style="font-size:10px;margin-left:4px">${grp}</span></td>
      <td>${priorityBadge(bs.priority_level || 'Mid')}</td>
      ${fcellHtml(b, 'cpm')}
      ${fcellHtml(b, 'ctr')}
      ${fcellHtml(b, 'cvr')}
      <td class="txt"><strong style="color:var(--pur)">${role.role || '—'}</strong><div style="font-size:11px;color:var(--tx2);margin-top:3px;font-weight:400;line-height:1.5">${role.reason || ''}</div></td>
      <td class="txt" style="font-size:11px;color:var(--tx2)">${contentBrief.join('<br>') || '—'}</td>
    </tr>`;
  });
  document.getElementById('exec-matrix').innerHTML = `<thead><tr>${heads.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody class="tbl-master">${trs}</tbody>`;
  const leadEl = document.getElementById('ep-lead-41');
  if (leadEl) leadEl.innerHTML = `각 셀은 다음 순서로 정보를 제공합니다 — 상태 배지(양호 / 주의 / 우려) · 운영 액션 한 줄 · 권고 소재 역할 · 추천 소재. 주의 및 우려 셀에 대해서만 소재 역할과 추천 소재가 표시되며, 양호 셀은 현 상태 유지가 기본 처방입니다.`;

  // 4.2 콘텐츠 큐레이션 (지점별)
  const byGroup = {A: [], B: [], C: []};
  (at.rows || []).forEach(r => byGroup[groupKey(r.group)].push(r.branch));
  let curHtml = '';
  ['A','B','C'].forEach(g => {
    const list = byGroup[g] || [];
    if (list.length === 0) return;
    const def = ({A:'A. 효율 개선 우선',B:'B. 예산 확대 후보',C:'C. 신규 모니터링'}[g]) || g;
    curHtml += `<div style="margin-bottom:20px"><div style="display:flex;align-items:baseline;gap:10px;margin-bottom:10px;padding:8px 14px;border-radius:6px;background:rgba(${g==='A'?'248,113,113':(g==='B'?'52,211,153':'167,139,250')},.08);border-left:4px solid var(--${g==='A'?'red':(g==='B'?'t1':'pur')})"><div style="font-size:14px;font-weight:800;color:var(--${g==='A'?'red':(g==='B'?'t1':'pur')})">${def}</div></div>`;
    list.forEach(b => {
      const rec = recBy[b] || {};
      const renderItems = (arr, focus, extraFn) => {
        if (!arr || arr.length === 0) return `<div class="reco-item muted">추천 없음</div>`;
        return arr.slice(0, 4).map(c => `<div class="reco-item"><strong>${c.creative_name}</strong>${c.is_off ? ' <span class="bd bd-warn" style="font-size:9px">OFF</span>' : ''}<div class="reco-item-meta">${focus.toUpperCase()} ${focus === 'cpm' ? fmt(c.focus_value) + '원' : fmtPct(c.focus_value)} · 전환 ${c.conversions}건${extraFn ? extraFn(c) : ''}</div></div>`).join('');
      };
      const focus = rec.focus_funnel || 'cvr';
      curHtml += `<div class="bp ${g}">
        <div class="bp-hdr">
          <div class="bp-name">${b}</div>
          ${groupBadge(g)}
          <div class="bp-meta">우선 ${focus.toUpperCase()} · ${rec.focus_reason || ''}</div>
        </div>
        <div class="reco-rail">
          <div class="reco-col keep">
            <div class="reco-col-lbl">유지 · 본인 우수</div>
            ${renderItems(rec.keep, focus)}
          </div>
          <div class="reco-col expand">
            <div class="reco-col-lbl">확대 · 타지점 검증</div>
            ${renderItems(rec.expand, focus, c => ` · 더 우수: ${(c.better_in_branches || []).join(', ')}`)}
          </div>
          <div class="reco-col new">
            <div class="reco-col-lbl">신규 도입 · 미운영</div>
            ${renderItems(rec.new_intro, focus, c => ` · 출처: ${c.source_branch || '-'}`)}
          </div>
        </div>
      </div>`;
    });
    curHtml += `</div>`;
  });
  document.getElementById('content-curation').innerHTML = curHtml;

  // 4.3 퍼널별 TOP3 (지점별)
  let topHtml = '';
  branches.forEach(b => {
    const bd = topBy[b];
    if (!bd) return;
    const renderTop3Col = (list, funnel, cls) => {
      if (!list || list.length === 0) return `<div class="top3-col ${cls}"><div class="top3-col-lbl">${funnel.toUpperCase()} TOP3</div><div class="muted">데이터 부족</div></div>`;
      return `<div class="top3-col ${cls}"><div class="top3-col-lbl">${funnel.toUpperCase()} TOP3</div>${list.map((c, i) => `<div class="t3-card">
        <div class="t3-rank">#${i+1}</div>
        <div class="t3-name">${c.creative_name}${c.is_off ? '<span class="t3-tag">OFF</span>' : ''}</div>
        <div class="t3-val">${funnel === 'cpm' ? fmt(c.metric_value) + '원' : fmtPct(c.metric_value)}</div>
        <div class="t3-sub">전환 ${c.conversions}건 · CPA ${fmt(c.cpa || 0)}원 · ${c.days_active}일</div>
      </div>`).join('')}</div>`;
    };
    topHtml += `<div style="margin-bottom:18px">
      <div style="font-size:14px;font-weight:800;color:var(--tx);margin-bottom:8px;padding-left:12px;border-left:3px solid var(--acc)">${b}</div>
      <div class="top3-rail">
        ${renderTop3Col(bd.cpm, 'cpm', 'cpm')}
        ${renderTop3Col(bd.ctr, 'ctr', 'ctr')}
        ${renderTop3Col(bd.cvr, 'cvr', 'cvr')}
      </div>
    </div>`;
  });
  document.getElementById('top-by-branch').innerHTML = topHtml;

  // C.1 소재유형 인사이트
  const ct = DATA.creative_type;
  if (ct) {
    const summaryHeads = ['소재유형', '전환', '비중', 'CPA', 'CVR', '광고', '효율'];
    let sumTrs = '';
    Object.entries(ct.by_type || {}).forEach(([type, d]) => {
      const g = d.cpa_grade || {};
      const cls = g.grade === 'efficient' ? 'good' : (g.grade === 'inefficient' ? 'bad' : 'mid');
      sumTrs += `<tr><td class="lbl">${type}</td><td><strong>${fmt(d.conversions)}</strong>건</td><td>${d.conv_share_pct}%</td><td>${fmt(d.cpa)}원</td><td>${fmtPct(d.cvr)}</td><td>${d.ad_count}개</td><td>${statusBadge(cls, g.label)}</td></tr>`;
    });
    document.getElementById('ctype-summary-tbl').innerHTML = `<thead><tr>${summaryHeads.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${sumTrs}</tbody>`;

    // 매트릭스
    const matrix = ct.branch_type_matrix || {};
    const usedTypes = new Set();
    branches.forEach(b => { const m = matrix[b]; if (m && m.by_type) Object.entries(m.by_type).forEach(([t, v]) => { if (v) usedTypes.add(t); }); });
    const types = Object.keys(ct.by_type || {}).filter(t => usedTypes.has(t));
    let matHtml = `<div style="display:grid;grid-template-columns:80px ${types.map(() => '1fr').join(' ')};background:var(--bd);border-radius:6px;overflow:hidden;border:1px solid var(--bd)">`;
    matHtml += `<div style="background:var(--s2);padding:8px;text-align:center;font-size:10px;font-weight:700;color:var(--tx2)">지점</div>`;
    types.forEach(t => { matHtml += `<div style="background:var(--s2);padding:8px;text-align:center;font-size:10px;font-weight:700;color:var(--tx2)">${t}</div>`; });
    branches.forEach(b => {
      matHtml += `<div style="background:var(--s2);padding:8px;font-size:11px;font-weight:700;color:var(--tx)">${b}</div>`;
      const m = matrix[b];
      types.forEach(t => {
        const v = m && m.by_type ? m.by_type[t] : null;
        if (!v) { matHtml += `<div style="background:var(--s1);padding:6px;text-align:center;font-size:10px;color:var(--tx3)">-</div>`; return; }
        const overallCpa = ct.overall ? ct.overall.cpa : null;
        let bgColor = 'var(--s1)';
        let txColor = 'var(--tx)';
        if (overallCpa && v.cpa) {
          const r = v.cpa / overallCpa;
          if (r <= 0.85) { bgColor = 'rgba(52,211,153,.10)'; txColor = 'var(--t1)'; }
          else if (r >= 1.15) { bgColor = 'rgba(248,113,113,.10)'; txColor = 'var(--red)'; }
        }
        matHtml += `<div style="background:${bgColor};padding:6px;text-align:center;font-size:11px;color:${txColor};font-family:'DM Mono',monospace"><div style="font-weight:800">${v.conversions}건</div><div style="font-size:9px;opacity:.85">${fmt(v.cpa)}원</div></div>`;
      });
    });
    matHtml += `</div>`;
    document.getElementById('ctype-matrix').innerHTML = matHtml;

    // insights
    document.getElementById('ctype-insights').innerHTML = (ct.insights || []).map(ins => `<div class="insight-card" style="margin-bottom:8px"><div class="card-title" style="color:var(--acc)">${ins.label}</div><div style="font-size:12px;color:var(--tx);line-height:1.6">${ins.detail}</div><div style="font-size:11px;color:var(--tx2);margin-top:6px;padding-top:6px;border-top:1px dashed var(--bd)">→ ${ins.action}</div></div>`).join('');

    // 신규 vs 재가공
    const kc = ct.kind_compare || {};
    if (kc['신규'] && kc['재가공']) {
      const newer = kc['신규'].cpa < kc['재가공'].cpa;
      const diff = Math.abs(((kc['신규'].cpa - kc['재가공'].cpa) / kc['재가공'].cpa * 100)).toFixed(1);
      const winner = newer ? '신규' : '재가공';
      const renderMini = (label, d, isWinner) => `<div style="flex:1;background:var(--s2);border:1px solid var(--bd);border-left:3px solid ${isWinner?'var(--t1)':'var(--tx3)'};border-radius:6px;padding:12px 14px;position:relative">${isWinner ? `<div style="position:absolute;top:8px;right:10px;font-size:9px;font-weight:800;padding:1px 6px;border-radius:3px;background:rgba(52,211,153,.18);color:var(--t1)">우세</div>` : ''}<div style="font-size:10px;color:var(--tx2);font-weight:700;letter-spacing:.04em">${label} · ${d.ad_count}개 광고</div><div style="font-size:22px;font-weight:900;font-family:'DM Mono',monospace;color:var(--tx);margin-top:6px">${fmt(d.cpa)}원</div><div style="font-size:10px;color:var(--tx2);margin-top:3px">전환 ${fmt(d.conversions)}건 (${d.conv_share_pct}%)</div></div>`;
      document.getElementById('ctype-kind-cards').innerHTML = `<div style="display:flex;gap:12px;align-items:center;margin-bottom:12px">${renderMini('신규', kc['신규'], newer)}<div style="font-size:18px;color:var(--tx3);font-weight:700">vs</div>${renderMini('재가공', kc['재가공'], !newer)}</div><div style="padding:10px 14px;background:rgba(52,211,153,.06);border-left:3px solid var(--t1);border-radius:0 5px 5px 0;font-size:12px;color:var(--tx)"><strong style="color:var(--t1)">${winner} 소재 CPA ${diff}% 우세</strong> · 6월에 ${winner} 비중 확대 테스트 권장 (점진적으로 5~10%p 상향)</div>`;
    }
  }

  // C.3 키워드
  const kw = DATA.keyword_analysis;
  if (kw) {
    document.getElementById('kw-insights').innerHTML = (kw.insights || []).map(ins => `<div class="insight-card" style="border-left-color:var(--pur);margin-bottom:8px"><div class="card-title" style="color:var(--pur)">${ins.label}</div><div style="font-size:12px;color:var(--tx);line-height:1.6">${ins.detail}</div><div style="font-size:11px;color:var(--tx2);margin-top:6px">→ ${ins.action}</div></div>`).join('');
    const quad = kw.quadrants || {};
    const quadLabels = {
      main:{name:'주력 메시지',sub:'많이 + 효율 우수',color:'var(--t1)'},
      expand:{name:'확대 후보',sub:'적게 + 효율 우수',color:'var(--acc)'},
      fix:{name:'개선 시급',sub:'많이 + 효율 부진',color:'var(--red)'},
      reduce:{name:'축소 검토',sub:'적게 + 효율 부진',color:'var(--warn)'},
    };
    document.getElementById('kw-quadrants').innerHTML = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">${['main','expand','fix','reduce'].map(k => {
      const items = quad[k] || [];
      const m = quadLabels[k];
      const body = items.length > 0 ? items.map(it => `<div style="padding:6px 0;border-bottom:1px dashed var(--bd);font-size:11px"><strong>${it.category}</strong><span style="font-size:10px;color:var(--tx2);margin-left:6px;font-family:'DM Mono',monospace">광고 ${it.ad_count}개 · 전환 ${it.conversions} · CPA ${fmt(it.cpa)}원</span></div>`).join('') : `<div class="muted">없음</div>`;
      return `<div style="background:var(--s2);border-radius:6px;padding:12px 14px;border-left:4px solid ${m.color}"><div style="font-size:12px;font-weight:800;color:${m.color};margin-bottom:8px">${m.name} <small style="font-size:9px;color:var(--tx2);font-weight:500">· ${m.sub}</small></div>${body}</div>`;
    }).join('')}</div>`;
    const kwHeads = ['카테고리', '광고', '전환', '비중', 'CPA', 'CTR', 'CVR', '효율'];
    let kwTrs = '';
    Object.entries(kw.by_keyword || {}).forEach(([cat, d]) => {
      const g = d.cpa_grade || {};
      const cls = g.grade === 'efficient' ? 'good' : (g.grade === 'inefficient' ? 'bad' : 'mid');
      kwTrs += `<tr><td class="lbl">${cat}</td><td>${d.ad_count}개</td><td><strong>${fmt(d.conversions)}</strong>건</td><td>${d.conv_share_pct}%</td><td>${fmt(d.cpa)}원</td><td>${fmtPct(d.ctr)}</td><td>${fmtPct(d.cvr)}</td><td>${statusBadge(cls, g.label)}</td></tr>`;
    });
    document.getElementById('kw-summary-tbl').innerHTML = `<thead><tr>${kwHeads.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${kwTrs}</tbody>`;
  }

  // C.4 라이프사이클
  const lc = DATA.lifecycle;
  if (lc) {
    document.getElementById('lc-insights').innerHTML = (lc.insights || []).map(ins => `<div class="insight-card" style="border-left-color:var(--warn);margin-bottom:8px"><div class="card-title" style="color:var(--warn)">${ins.label}</div><div style="font-size:12px;color:var(--tx);line-height:1.6">${ins.detail}</div><div style="font-size:11px;color:var(--tx2);margin-top:6px">→ ${ins.action}</div></div>`).join('');
    const stats = lc.stage_stats || {};
    const totalCount = Object.values(stats).reduce((s, v) => s + (v.count || 0), 0);
    const stageInfo = { fresh: {label:'신선 · ~14일',color:'var(--t1)'}, mature: {label:'성숙 · 15~45일',color:'var(--blue)'}, long: {label:'장기 · 46일+',color:'var(--warn)'} };
    let stagesHtml = '';
    ['fresh','mature','long'].forEach(s => {
      const st = stats[s] || {count:0,avg_cpa:null,total_conv:0};
      const pct = totalCount > 0 ? (st.count/totalCount*100) : 0;
      stagesHtml += `<div style="display:grid;grid-template-columns:120px 60px 1fr 100px;gap:10px;align-items:center;padding:8px 12px;border-radius:5px;background:var(--s2);margin-bottom:6px;border-left:3px solid ${stageInfo[s].color}"><div style="font-size:11px;font-weight:700;color:var(--tx)">${stageInfo[s].label}</div><div style="font-size:14px;font-weight:900;font-family:'DM Mono',monospace">${st.count}개</div><div style="background:var(--s1);border-radius:3px;height:6px;overflow:hidden"><div style="height:100%;background:${stageInfo[s].color};width:${pct}%"></div></div><div style="font-size:10px;color:var(--tx2);font-family:'DM Mono',monospace;text-align:right">평균 CPA ${st.avg_cpa ? fmt(st.avg_cpa) + '원' : '-'}<br>전환 ${fmt(st.total_conv)}건</div></div>`;
    });
    document.getElementById('lc-stage-stats').innerHTML = stagesHtml;
    const offC = lc.off_candidates || [];
    const wins = lc.long_winners || [];
    let actHtml = `<div style="font-size:11px;font-weight:800;color:var(--red);margin:6px 0">▼ OFF 권장 (${offC.length}건)</div>`;
    actHtml += offC.length > 0 ? offC.map(it => `<div style="background:var(--s2);border:1px solid var(--bd);border-left:3px solid var(--red);border-radius:5px;padding:8px 12px;margin-bottom:5px"><div style="font-size:11px;font-weight:700;color:var(--tx);line-height:1.45">${it.creative_name}</div><div style="font-size:10px;color:var(--tx2);font-family:'DM Mono',monospace;margin-top:3px">활성 ${it.span_days}일 · 전환 ${it.total.conversions}건 · CPA ${fmt(it.total.cpa)}원</div><div style="font-size:10px;color:var(--tx2);margin-top:3px">${it.reason}</div></div>`).join('') : '<div class="muted">즉시 OFF 권장 없음</div>';
    actHtml += `<div style="font-size:11px;font-weight:800;color:var(--t1);margin:10px 0 6px">▼ 장수 우수 (${wins.length}건)</div>`;
    actHtml += wins.length > 0 ? wins.map(it => `<div style="background:var(--s2);border:1px solid var(--bd);border-left:3px solid var(--t1);border-radius:5px;padding:8px 12px;margin-bottom:5px"><div style="font-size:11px;font-weight:700;color:var(--tx);line-height:1.45">${it.creative_name}</div><div style="font-size:10px;color:var(--tx2);font-family:'DM Mono',monospace;margin-top:3px">활성 ${it.span_days}일 · 전환 ${it.total.conversions}건 · CPA ${fmt(it.total.cpa)}원</div><div style="font-size:10px;color:var(--tx2);margin-top:3px">${it.reason}</div></div>`).join('') : '<div class="muted">장수 우수 없음</div>';
    document.getElementById('lc-action-cards').innerHTML = actHtml;
    const vg = lc.variant_guide || {};
    if (vg.source_count > 0) {
      const patHtml = vg.patterns.map(p => `<div style="display:grid;grid-template-columns:80px 1fr 50px;gap:10px;align-items:center;padding:8px 12px;border-radius:4px;background:var(--s2);margin-bottom:5px"><div style="font-size:11px;color:var(--tx2);font-weight:700">${p.kind}</div><div style="font-size:11px;color:var(--tx);font-weight:600">${p.value}</div><div style="font-size:10px;color:var(--tx2);font-family:'DM Mono',monospace;text-align:right">${p.count}건</div></div>`).join('');
      const actHtml2 = (vg.variant_actions || []).map(a => `<div style="background:rgba(167,139,250,.06);border-left:3px solid var(--pur);border-radius:0 5px 5px 0;padding:8px 12px;margin-bottom:5px"><div style="font-size:11px;font-weight:700;color:var(--pur)">${a.axis}</div><div style="font-size:10.5px;color:var(--tx2);margin-top:3px;line-height:1.5">${a.guide}</div></div>`).join('');
      document.getElementById('lc-variant-guide').innerHTML = `<div style="margin-bottom:12px"><div style="font-size:10px;font-weight:700;color:var(--tx2);margin-bottom:6px;letter-spacing:.04em">장수 우수 ${vg.source_count}건 공통 패턴</div>${patHtml}</div><div><div style="font-size:10px;font-weight:700;color:var(--tx2);margin-bottom:6px;letter-spacing:.04em">6월 신규 제작 변주 축</div>${actHtml2}</div>`;
    } else {
      document.getElementById('lc-variant-guide').innerHTML = '<div class="muted">장수 우수 소재가 없어 변주 가이드 도출 불가</div>';
    }
    const lcHeads = ['소재','단계','활성','전환','CPA','CTR Δ','CVR Δ','액션'];
    const allItems = [...(lc.by_stage.long || []), ...(lc.by_stage.mature || []), ...(lc.by_stage.fresh || [])];
    const priority = (r) => r === 'OFF 권장' ? 0 : (r.includes('피로') ? 1 : (r.startsWith('장수 우수') ? 2 : (r.includes('조기 점검') ? 3 : 4)));
    allItems.sort((a, b) => priority(a.recommendation) - priority(b.recommendation));
    let lcTrs = '';
    allItems.forEach(it => {
      const sc = it.stage === 'long' ? 'var(--warn)' : (it.stage === 'mature' ? 'var(--blue)' : 'var(--t1)');
      const ctrCls = it.ctr_change_pct !== null ? (it.ctr_change_pct < -15 ? 'delta-down' : (it.ctr_change_pct > 15 ? 'delta-up' : '')) : '';
      const cvrCls = it.cvr_change_pct !== null ? (it.cvr_change_pct < -15 ? 'delta-down' : (it.cvr_change_pct > 15 ? 'delta-up' : '')) : '';
      const recCls = it.recommendation === 'OFF 권장' ? 'delta-down' : (it.recommendation.startsWith('장수 우수') ? 'delta-up' : '');
      lcTrs += `<tr><td class="txt" style="max-width:280px">${it.creative_name}</td><td><span style="color:${sc};font-weight:700">${it.stage_label}</span></td><td>${it.span_days}일</td><td>${fmt(it.total.conversions)}건</td><td>${fmt(it.total.cpa)}원</td><td class="${ctrCls}">${it.ctr_change_pct !== null ? (it.ctr_change_pct > 0 ? '+' : '') + it.ctr_change_pct + '%' : '-'}</td><td class="${cvrCls}">${it.cvr_change_pct !== null ? (it.cvr_change_pct > 0 ? '+' : '') + it.cvr_change_pct + '%' : '-'}</td><td class="${recCls}" style="font-size:10px">${it.recommendation}</td></tr>`;
    });
    document.getElementById('lc-detail-tbl').innerHTML = `<thead><tr>${lcHeads.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${lcTrs}</tbody>`;
  }

  // C.5 OFF 분석
  const off = DATA.off_analysis;
  if (off && off.has_data) {
    document.getElementById('off-insights').innerHTML = (off.insights || []).map(ins => `<div class="insight-card" style="border-left-color:var(--blue);margin-bottom:8px"><div class="card-title" style="color:var(--blue)">${ins.label}</div><div style="font-size:12px;color:var(--tx);line-height:1.6">${ins.detail}</div><div style="font-size:11px;color:var(--tx2);margin-top:6px">→ ${ins.action}</div></div>`).join('');
    const reasonLabels = {'low_volume':'학습 미완','early_off':'조기 OFF','fatigue':'CTR 피로','cpa_poor':'CPA 부진','reusable':'재활용 후보'};
    const reasonColors = {'low_volume':'var(--tx2)','early_off':'var(--warn)','fatigue':'var(--red)','cpa_poor':'var(--red)','reusable':'var(--t1)'};
    const stats = off.stats.by_reason || {};
    const total = off.stats.total_off || 1;
    let rHtml = '';
    Object.entries(reasonLabels).forEach(([code, label]) => {
      const count = stats[code] || 0;
      const pct = total > 0 ? (count/total*100) : 0;
      rHtml += `<div style="display:grid;grid-template-columns:90px 50px 1fr 60px;gap:10px;align-items:center;padding:8px 12px;border-radius:4px;background:var(--s2);margin-bottom:5px;border-left:3px solid ${reasonColors[code]}"><div style="font-size:11px;color:var(--tx);font-weight:700">${label}</div><div style="font-size:13px;font-weight:900;font-family:'DM Mono',monospace">${count}건</div><div style="background:var(--s1);border-radius:3px;height:5px;overflow:hidden"><div style="height:100%;background:${reasonColors[code]};width:${pct}%"></div></div><div style="font-size:10px;color:var(--tx2);font-family:'DM Mono',monospace;text-align:right">${pct.toFixed(0)}%</div></div>`;
    });
    document.getElementById('off-reason-stats').innerHTML = rHtml;
    const reusable = off.reusable_candidates || [];
    let reHtml = '';
    if (reusable.length === 0) reHtml = '<div class="muted">재활용 후보 없음</div>';
    else reHtml = reusable.slice(0, 5).map(it => `<div style="background:var(--s2);border:1px solid var(--bd);border-left:3px solid var(--t1);border-radius:5px;padding:8px 12px;margin-bottom:5px"><div style="font-size:11px;font-weight:700;color:var(--tx);line-height:1.45">${it.ad_name}</div><div style="font-size:10px;color:var(--tx2);font-family:'DM Mono',monospace;margin-top:3px">[${it.branch || '-'}] OFF ${it.off_date} · 활성 ${it.span_days}일 · 전환 ${it.total.conversions}건 · CPA ${fmt(it.total.cpa)}원</div><div style="font-size:10px;color:var(--tx2);margin-top:3px">${it.reason_text}</div></div>`).join('');
    document.getElementById('off-reusable').innerHTML = reHtml;
  }

  // C.6 동일 소재 지점간 변동
  const cv = DATA.cross_variance;
  if (cv) {
    document.getElementById('cv-insights').innerHTML = (cv.insights || []).map(ins => `<div class="insight-card" style="border-left-color:var(--warn);margin-bottom:8px"><div class="card-title" style="color:var(--warn)">${ins.label}</div><div style="font-size:12px;color:var(--tx);line-height:1.6">${ins.detail}</div><div style="font-size:11px;color:var(--tx2);margin-top:6px">→ ${ins.action}</div></div>`).join('');
    const stats = cv.by_grade || {};
    const total = cv.items_count || 1;
    const labels = { high: {name:'큰 차이 (≥100%)',color:'var(--red)'}, mid: {name:'중간 (50~100%)',color:'var(--warn)'}, low: {name:'안정 (<50%)',color:'var(--t1)'} };
    let gradeHtml = '';
    ['high','mid','low'].forEach(g => {
      const list = stats[g] || [];
      const count = list.length;
      const pct = total > 0 ? (count/total*100) : 0;
      gradeHtml += `<div style="display:grid;grid-template-columns:120px 50px 1fr 60px;gap:10px;align-items:center;padding:8px 12px;border-radius:4px;background:var(--s2);margin-bottom:5px;border-left:3px solid ${labels[g].color}"><div style="font-size:11px;color:var(--tx);font-weight:700">${labels[g].name}</div><div style="font-size:13px;font-weight:900;font-family:'DM Mono',monospace">${count}건</div><div style="background:var(--s1);border-radius:3px;height:5px;overflow:hidden"><div style="height:100%;background:${labels[g].color};width:${pct}%"></div></div><div style="font-size:10px;color:var(--tx2);font-family:'DM Mono',monospace;text-align:right">${pct.toFixed(0)}%</div></div>`;
    });
    document.getElementById('cv-grade-stats').innerHTML = gradeHtml;
    const top = (cv.items || []).slice(0, 10);
    let topCardsHtml = top.length === 0 ? '<div class="muted">다지점 운영 소재 부족</div>' : top.map(it => `<div style="background:var(--s2);border:1px solid var(--bd);border-left:3px solid ${it.variance_grade === 'high' ? 'var(--red)' : (it.variance_grade === 'mid' ? 'var(--warn)' : 'var(--t1)')};border-radius:5px;padding:8px 12px;margin-bottom:5px"><div style="font-size:11px;font-weight:700;color:var(--tx);line-height:1.4;margin-bottom:6px">${it.creative_name}</div><div style="display:flex;align-items:center;justify-content:space-between;gap:8px;font-family:'DM Mono',monospace;font-size:10px"><div><div style="font-size:9px;color:var(--tx2);font-weight:700">베스트</div><div style="color:var(--t1)">${it.best_branch} ${fmt(it.best_cpa)}원</div></div><div style="font-size:11px;font-weight:900;color:var(--red);background:rgba(248,113,113,.12);padding:3px 8px;border-radius:3px">+${it.gap_pct}%</div><div style="text-align:right"><div style="font-size:9px;color:var(--tx2);font-weight:700">워스트</div><div style="color:var(--red)">${it.worst_branch} ${fmt(it.worst_cpa)}원</div></div></div><div style="font-size:9px;color:var(--tx2);margin-top:5px">${it.n_branches}개 지점 · 누적 전환 ${it.total_conversions}건</div></div>`).join('');
    document.getElementById('cv-top-cards').innerHTML = topCardsHtml;
    const heads = ['소재', '운영 지점', 'CPA 차이', '베스트', '워스트', '운영 권장'];
    let cvTrs = '';
    (cv.items || []).forEach(it => {
      const gc = it.variance_grade === 'high' ? 'var(--red)' : (it.variance_grade === 'mid' ? 'var(--warn)' : 'var(--t1)');
      cvTrs += `<tr><td class="txt" style="max-width:280px">${it.creative_name}</td><td>${it.n_branches}개</td><td style="color:${gc};font-weight:700">+${it.gap_pct}%</td><td><strong>${it.best_branch}</strong> ${fmt(it.best_cpa)}원</td><td><strong>${it.worst_branch}</strong> ${fmt(it.worst_cpa)}원</td><td class="txt" style="font-size:10px;max-width:340px">${it.recommendation}</td></tr>`;
    });
    document.getElementById('cv-detail-tbl').innerHTML = `<thead><tr>${heads.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${cvTrs}</tbody>`;
  }
})();

// ==================== 05 애드온 판단 (R12 — 부산 제외 + v2 vs v1 메인 비교) ====================
(function renderAddon() {
  const A = DATA.addon_effect || {};
  const ms = A.meta_summary || {};
  const judge = A.judgement || {};
  const v1Block = A.v1_vs_period || {};
  const v2Block = A.v2_vs_period || {};
  const v2v1Block = A.v2_vs_v1 || {};
  const designByType = A.design_by_type || {};

  const cls = (v, dir) => v === null || v === undefined ? '' : (dir === 'low' ? (v < 0 ? 'delta-up' : 'delta-down') : (v > 0 ? 'delta-up' : 'delta-down'));
  const sigBadge = (p) => (p !== null && p !== undefined && p < 0.05) ? '<span style="color:var(--t1);font-weight:800;margin-left:4px" title="통계적으로 유의 (p<0.05)">★</span>' : '';
  const verdictColorMap = {
    v2_expand:'var(--t1)', v1_partial_restore:'var(--red)', mixed:'var(--warn)', verify:'var(--warn)',
    positive:'var(--t1)', negative:'var(--red)', noop:'var(--warn)',
    v2_better:'var(--t1)', v1_better:'var(--red)', unmeasurable:'var(--tx3)', low_sample:'var(--tx3)',
  };

  // ============ 5.1 6월 운영 권고 ============
  const rec = judge.recommended_action || {};
  const recColor = verdictColorMap[rec.verdict] || 'var(--tx2)';
  const v1Verdict = judge.v1_vs_non || {};
  const dcVerdict = judge.design_change || {};
  const v1c = verdictColorMap[v1Verdict.verdict] || 'var(--tx2)';
  const dcc = verdictColorMap[dcVerdict.verdict] || 'var(--tx2)';
  const dt = judge.by_design_type || {};
  const v2Better = dt.v2_better || [];
  const v1Better = dt.v1_better || [];
  const dtNoop = dt.noop || [];
  const dtLow = dt.low_sample || [];

  document.getElementById('addon-judgement').innerHTML = `
    <div style="background:linear-gradient(135deg, var(--s2) 0%, var(--s1) 100%);border-left:5px solid ${recColor};border-radius:8px;padding:18px 22px;margin-bottom:14px">
      <div style="font-size:10px;font-weight:800;color:${recColor};letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px">6월 결론 — 한 문단</div>
      <div style="font-size:14.5px;color:var(--tx);line-height:1.65;font-weight:600">
        구 디자인(v1) 애드온 효과는 검증되었으나, <strong style="color:var(--warn)">5월 신 디자인(v2)은 부산 제외 시 동기간 비애드온 비교가 불가능</strong>합니다. 6월에는 <strong style="color:var(--t1)">v2 유지 그룹</strong>과 <strong style="color:var(--red)">v1 복원·부분 변경 그룹</strong>으로 나눠 운영하고, 7월에 표준 디자인을 결정합니다.
      </div>
    </div>
    <div class="gap-caveat" style="margin-bottom:14px;border-left-color:var(--tx3);background:rgba(148,163,184,.05);font-size:11px;line-height:1.55;color:var(--tx2)">
      <strong>분석 범위 안내.</strong> ${ms.exclusion_reason || ''} 적용 광고 v1 ${ms.addon_ads_v1}개 / v2 ${ms.addon_ads_v2}개 (부산 제외 전체 ${ms.total_ads_in_data}개).
    </div>
    <div class="g3" style="gap:8px;margin-bottom:6px">
      ${[
        { lbl: 'v2 디자인 우세 → 확대', items: v2Better, color: 'var(--t1)', icon: '▲' },
        { lbl: 'v1 디자인 우세 → 복원 검토', items: v1Better, color: 'var(--red)', icon: '▼' },
        { lbl: '표본 부족·미미 → 보류', items: [...dtNoop, ...dtLow], color: 'var(--tx3)', icon: '◦' },
      ].map(c => `<div style="background:var(--s2);border-left:3px solid ${c.color};border-radius:5px;padding:8px 12px">
        <div style="font-size:9px;font-weight:800;color:${c.color};letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px">${c.icon} ${c.lbl}</div>
        <div style="font-size:11.5px;color:var(--tx);font-weight:700;line-height:1.5">${c.items.length > 0 ? c.items.join(' · ') : '<span class="muted">해당 없음</span>'}</div>
      </div>`).join('')}
    </div>
  `;

  // ============ 5.2 평가축 카드 ============
  const v1d = v1Block.delta_pct || {};
  const v2v1d = v2v1Block.delta_pct || {};

  const kpiCell = (lbl, val, dirClass, sub) => `<div style="background:var(--s2);border-radius:4px;padding:6px 8px">
    <div style="font-size:9px;color:var(--tx2);font-weight:700">${lbl}</div>
    <div style="font-size:13px;font-weight:800;font-family:'DM Mono',monospace" class="${dirClass}">${val}</div>
    ${sub ? `<div style="font-size:9px;color:var(--tx2);margin-top:2px">${sub}</div>` : ''}
  </div>`;

  // 평가축 1 카드: v1 vs 3~4월 비애드온
  const v1a = v1Block.addon || {}; const v1n = v1Block.non_addon || {};
  const card1 = `<div style="background:var(--s1);border:1px solid var(--bd);border-left:4px solid #94a3b8;border-radius:7px;padding:14px 16px">
    <div style="margin-bottom:8px">
      <div style="font-size:9.5px;font-weight:800;color:#94a3b8;letter-spacing:.08em;text-transform:uppercase">평가축 1 · v1 (구 디자인) vs 3~4월 비애드온</div>
      <div style="font-size:10.5px;color:var(--tx2);margin-top:2px">애드온 자체의 효과 — 양쪽 표본 충분</div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px">
      <div><div style="font-size:9px;color:var(--tx2);font-weight:700">v1 애드온 (클릭/전환)</div><div style="font-size:11.5px;font-weight:800;font-family:'DM Mono',monospace">${(v1a.clicks||0).toLocaleString()} / ${v1a.conversions||0}</div><div style="font-size:9.5px;color:var(--tx2)">CVR ${v1a.cvr || '-'}% · CPA ${v1a.cpa ? fmt(v1a.cpa) : '-'}원</div></div>
      <div><div style="font-size:9px;color:var(--tx2);font-weight:700">3~4월 비애드온 (클릭/전환)</div><div style="font-size:11.5px;font-weight:800;font-family:'DM Mono',monospace">${(v1n.clicks||0).toLocaleString()} / ${v1n.conversions||0}</div><div style="font-size:9.5px;color:var(--tx2)">CVR ${v1n.cvr || '-'}% · CPA ${v1n.cpa ? fmt(v1n.cpa) : '-'}원</div></div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px">
      ${kpiCell('CTR Δ', fmtSigned(v1d.ctr), cls(v1d.ctr, 'high'))}
      ${kpiCell('CVR Δ', fmtSigned(v1d.cvr) + sigBadge(v1d.cvr_p), cls(v1d.cvr, 'high'))}
      ${kpiCell('CPA Δ', fmtSigned(v1d.cpa), cls(v1d.cpa, 'low'))}
      ${kpiCell('p-value', v1d.cvr_p !== null && v1d.cvr_p !== undefined ? v1d.cvr_p : '-', 'muted')}
    </div>
  </div>`;

  // 평가축 2 카드: v2 vs v1
  const v2k = v2v1Block.v2 || {}; const v1k = v2v1Block.v1 || {};
  const card2 = `<div style="background:var(--s1);border:1px solid var(--bd);border-left:4px solid #a78bfa;border-radius:7px;padding:14px 16px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
      <div>
        <div style="font-size:9.5px;font-weight:800;color:#a78bfa;letter-spacing:.08em;text-transform:uppercase">평가축 2 · v2 (신 디자인) vs v1 (구 디자인)</div>
        <div style="font-size:10.5px;color:var(--tx2);margin-top:2px">디자인 변경의 직접 효과 — 시즌 confound 일부 포함</div>
      </div>
      <div style="font-size:9px;font-weight:800;background:rgba(167,139,250,.18);color:#a78bfa;padding:3px 8px;border-radius:3px">디자인 효과</div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px">
      <div><div style="font-size:9px;color:var(--tx2);font-weight:700">v2 신 디자인 (클릭/전환)</div><div style="font-size:11.5px;font-weight:800;font-family:'DM Mono',monospace">${(v2k.clicks||0).toLocaleString()} / ${v2k.conversions||0}</div><div style="font-size:9.5px;color:var(--tx2)">CVR ${v2k.cvr || '-'}% · CPA ${v2k.cpa ? fmt(v2k.cpa) : '-'}원</div></div>
      <div><div style="font-size:9px;color:var(--tx2);font-weight:700">v1 구 디자인 (클릭/전환)</div><div style="font-size:11.5px;font-weight:800;font-family:'DM Mono',monospace">${(v1k.clicks||0).toLocaleString()} / ${v1k.conversions||0}</div><div style="font-size:9.5px;color:var(--tx2)">CVR ${v1k.cvr || '-'}% · CPA ${v1k.cpa ? fmt(v1k.cpa) : '-'}원</div></div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px">
      ${kpiCell('CTR Δ', fmtSigned(v2v1d.ctr), cls(v2v1d.ctr, 'high'))}
      ${kpiCell('CVR Δ', fmtSigned(v2v1d.cvr) + sigBadge(v2v1d.cvr_p), cls(v2v1d.cvr, 'high'))}
      ${kpiCell('CPA Δ', fmtSigned(v2v1d.cpa), cls(v2v1d.cpa, 'low'))}
      ${kpiCell('p-value', v2v1d.cvr_p !== null && v2v1d.cvr_p !== undefined ? v2v1d.cvr_p : '-', 'muted')}
    </div>
  </div>`;

  document.getElementById('addon-version-cards').innerHTML = card1 + card2;

  // v2 vs 5월 비애드온 비교 불가 안내 박스
  const v2nonClicks = (v2Block.non_addon || {}).clicks || 0;
  document.getElementById('addon-v2-unmeasurable-box').innerHTML = `
    <div class="gap-caveat" style="border-left-color:var(--tx3);background:rgba(148,163,184,.06);font-size:11.5px;line-height:1.6">
      <strong>v2 vs 5월 비애드온 — 동기간 비교 불가.</strong> 부산 제외 후 5월 비애드온 클릭은 <strong>${v2nonClicks.toLocaleString()}건</strong>에 불과하여 (창원 일부 잔여만 존재) 동기간 비교는 통계적으로 의미가 없습니다. ${v2Block.note || ''}
    </div>
  `;

  // 디자인 변경 효과 차트 (v2 vs v1)
  const chartLabels = ['CPM (낮을수록 ↑)','CTR','CVR','CPA (낮을수록 ↑)'];
  const chartVals = [v2v1d.cpm === null || v2v1d.cpm === undefined ? 0 : -v2v1d.cpm,
                     v2v1d.ctr === null || v2v1d.ctr === undefined ? 0 : v2v1d.ctr,
                     v2v1d.cvr === null || v2v1d.cvr === undefined ? 0 : v2v1d.cvr,
                     v2v1d.cpa === null || v2v1d.cpa === undefined ? 0 : -v2v1d.cpa];
  const chartColors = chartVals.map(v => v >= 0 ? 'rgba(52,211,153,.85)' : 'rgba(248,113,113,.85)');
  new Chart(document.getElementById('addonOverallChart'), {
    type: 'bar',
    data: { labels: chartLabels, datasets: [{ data: chartVals, backgroundColor: chartColors }] },
    options: { responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false},tooltip:{callbacks:{label: (ctx) => `${ctx.label}: ${ctx.parsed.y.toFixed(1)}%`}}}, scales:{x:{ticks:{color:CHART_TEXT},grid:{color:CHART_GRID}}, y:{ticks:{color:CHART_TEXT,callback:v => v+'%'},grid:{color:CHART_GRID}}} },
  });

  // ============ 5.3 소재유형별 디자인 효과 (v1 → v2) ============
  const ctOrder = Object.keys(designByType).sort((a, b) => {
    const order = { v2_better:0, v1_better:1, noop:2, low_sample:3, unmeasurable:3 };
    return (order[designByType[a].verdict.verdict] ?? 9) - (order[designByType[b].verdict.verdict] ?? 9);
  });
  let ctRows = '';
  ctOrder.forEach(ct => {
    const b = designByType[ct];
    const v = b.verdict || {};
    const d = b.delta_pct || {};
    const v1 = b.v1 || {}; const v2 = b.v2 || {};
    const vc = verdictColorMap[v.verdict] || 'var(--tx2)';
    ctRows += `<tr>
      <td class="lbl">${ct}</td>
      <td><strong style="color:${vc}">${v.label || '-'}</strong></td>
      <td>${(v1.clicks||0).toLocaleString()} / ${(v2.clicks||0).toLocaleString()}</td>
      <td>${v1.cvr !== null && v1.cvr !== undefined ? v1.cvr + '%' : '-'} → ${v2.cvr !== null && v2.cvr !== undefined ? v2.cvr + '%' : '-'}</td>
      <td>${v1.cpa ? fmt(v1.cpa) + '원' : '-'} → ${v2.cpa ? fmt(v2.cpa) + '원' : '-'}</td>
      <td class="${cls(d.cvr,'high')}">${fmtSigned(d.cvr)}${sigBadge(d.cvr_p)}</td>
      <td class="${cls(d.cpa,'low')}">${fmtSigned(d.cpa)}</td>
      <td class="muted">${d.cvr_p !== null && d.cvr_p !== undefined ? 'p=' + d.cvr_p : '-'}</td>
    </tr>`;
  });
  document.getElementById('addon-creative-type-tbl').innerHTML =
    `<thead><tr><th>소재유형</th><th>디자인 효과 판단</th><th>v1/v2 클릭</th><th>v1 → v2 CVR</th><th>v1 → v2 CPA</th><th>CVR Δ</th><th>CPA Δ</th><th>p-value</th></tr></thead><tbody>${ctRows}</tbody>`;

  // ============ 5.4 시청 깔때기 가설 검증 (R12 신규) ============
  const wf = A.watch_funnel || {};
  const hyp = wf.hypothesis || null;
  if (hyp) {
    const infl = hyp.infl || {};
    const self = hyp.self || {};
    const inflDepth = infl.v6s_v2 !== null && infl.v6s_v1 !== null ? (infl.v6s_v2 - infl.v6s_v1) : null;
    const selfDepth = self.v6s_v2 !== null && self.v6s_v1 !== null ? (self.v6s_v2 - self.v6s_v1) : null;
    const inflCvr = infl.cvr_v2 !== null && infl.cvr_v1 !== null ? (infl.cvr_v2 - infl.cvr_v1) : null;
    const selfCvr = self.cvr_v2 !== null && self.cvr_v1 !== null ? (self.cvr_v2 - self.cvr_v1) : null;
    const dirArrow = (v, unit) => v === null ? '-' : (v >= 0 ? `<span class="delta-up">▲ ${Math.abs(v).toFixed(2)}${unit||'pp'}</span>` : `<span class="delta-down">▼ ${Math.abs(v).toFixed(2)}${unit||'pp'}</span>`);
    const depthTop3 = (hyp.depth_ranking_by_v6s || []).slice(0, 3);
    const shareTop3 = (hyp.share_ranking || []).slice(0, 3);
    const archetype = hyp.archetype || {};

    document.getElementById('addon-hypothesis-box').innerHTML = `
      <div style="background:var(--s1);border:1px solid var(--bd);border-left:4px solid #a78bfa;border-radius:8px;padding:14px 18px">
        <div style="font-size:10px;font-weight:800;color:#a78bfa;letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px">가설 검증 · 시청 깊이 + 인게이지먼트 동시 검증</div>
        <div style="font-size:12px;color:var(--tx);line-height:1.65;margin-bottom:12px">${hyp.hypothesis}</div>
        <div class="g2" style="gap:10px;margin-bottom:12px">
          <div style="background:var(--s2);border-radius:6px;padding:10px 12px">
            <div style="font-size:9.5px;font-weight:800;color:var(--tx2);letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px">시청 깊이 1위 (6초 시청률)</div>
            <div style="font-size:11.5px;color:var(--tx);line-height:1.5">${depthTop3.map((t, i) => `${i+1}. <strong>${t[0]}</strong> ${t[1]}%`).join(' · ')}</div>
          </div>
          <div style="background:var(--s2);border-radius:6px;padding:10px 12px">
            <div style="font-size:9.5px;font-weight:800;color:var(--tx2);letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px">공유율 1위 (바이럴 지수)</div>
            <div style="font-size:11.5px;color:var(--tx);line-height:1.5">${shareTop3.map((t, i) => `${i+1}. <strong>${t[0]}</strong> ${(t[1] || 0).toFixed(4)}%`).join(' · ')}</div>
          </div>
        </div>
        <div style="background:var(--s2);border-radius:6px;padding:12px 14px;margin-bottom:12px">
          <div style="font-size:9.5px;font-weight:800;color:var(--tx2);letter-spacing:.06em;text-transform:uppercase;margin-bottom:8px">두 콘텐츠 깔때기 비교 (디자인 변경 v1 → v2)</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
            <div style="border-left:3px solid var(--blue, #60a5fa);padding-left:10px">
              <div style="font-size:11px;font-weight:800;color:var(--tx);margin-bottom:4px">진료셀프캠 — ${archetype['진료셀프캠'] || ''}</div>
              <div style="font-size:10.5px;color:var(--tx2);line-height:1.7;font-family:'DM Mono',monospace">
                공유율: ${(self.share_v1 || 0).toFixed(4)}% → ${(self.share_v2 || 0).toFixed(4)}%<br>
                6s 시청률: ${self.v6s_v1}% → ${self.v6s_v2}% ${dirArrow(selfDepth)}<br>
                15s 시청률: ${self.eng15s_v1}% → ${self.eng15s_v2}%<br>
                CVR(클릭→전환): ${self.cvr_v1}% → ${self.cvr_v2}% ${dirArrow(selfCvr)}
              </div>
            </div>
            <div style="border-left:3px solid var(--t1);padding-left:10px">
              <div style="font-size:11px;font-weight:800;color:var(--tx);margin-bottom:4px">인플방문후기 — ${archetype['인플방문후기'] || ''}</div>
              <div style="font-size:10.5px;color:var(--tx2);line-height:1.7;font-family:'DM Mono',monospace">
                공유율: ${(infl.share_v1 || 0).toFixed(4)}% → ${(infl.share_v2 || 0).toFixed(4)}%<br>
                6s 시청률: ${infl.v6s_v1}% → ${infl.v6s_v2}% ${dirArrow(inflDepth)}<br>
                15s 시청률: ${infl.eng15s_v1}% → ${infl.eng15s_v2}%<br>
                CVR(클릭→전환): ${infl.cvr_v1}% → ${infl.cvr_v2}% ${dirArrow(inflCvr)}
              </div>
            </div>
          </div>
        </div>
        <div style="background:rgba(167,139,250,.08);border-left:3px solid #a78bfa;border-radius:4px;padding:10px 12px">
          <div style="font-size:9.5px;font-weight:800;color:#a78bfa;letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px">결론 — 바이럴형 vs 전환형</div>
          <div style="font-size:12px;color:var(--tx);line-height:1.6">${hyp.finding}</div>
        </div>
        <div style="font-size:9.5px;color:var(--tx2);margin-top:8px;line-height:1.5">${wf.note || ''}</div>
      </div>
    `;
  } else {
    document.getElementById('addon-hypothesis-box').innerHTML = '';
  }

  // 시청 깔때기 테이블 (인게이지먼트 컬럼 포함)
  const wfByType = wf.by_creative_type || {};
  let wfRows = '';
  const wfOrder = Object.keys(wfByType).sort((a, b) => ((wfByType[b].v2 || wfByType[b].v1 || {}).v6s_rate || 0) - ((wfByType[a].v2 || wfByType[a].v1 || {}).v6s_rate || 0));
  wfOrder.forEach(ct => {
    const b = wfByType[ct];
    [['v1', b.v1, '구 v1'], ['v2', b.v2, '신 v2']].forEach(([key, k, lbl]) => {
      if (!k || !k.impressions) return;
      const badge = key === 'v2' ? '<span style="font-size:8.5px;font-weight:800;background:rgba(52,211,153,.15);color:var(--t1);padding:2px 6px;border-radius:3px;margin-left:4px">신 v2</span>' : '<span style="font-size:8.5px;font-weight:800;background:rgba(148,163,184,.15);color:var(--tx2);padding:2px 6px;border-radius:3px;margin-left:4px">구 v1</span>';
      wfRows += `<tr>
        <td class="lbl">${ct}${badge}</td>
        <td>${k.impressions.toLocaleString()}</td>
        <td>${k.v6s_rate !== null && k.v6s_rate !== undefined ? k.v6s_rate + '%' : '-'}</td>
        <td>${k.eng15s_rate !== null && k.eng15s_rate !== undefined ? k.eng15s_rate + '%' : '-'}</td>
        <td>${k.p50_rate !== null && k.p50_rate !== undefined ? k.p50_rate + '%' : '-'}</td>
        <td>${k.p100_rate !== null && k.p100_rate !== undefined ? k.p100_rate + '%' : '-'}</td>
        <td>${k.avg_video_sec !== null && k.avg_video_sec !== undefined ? k.avg_video_sec + 's' : '-'}</td>
        <td>${k.like_rate !== null && k.like_rate !== undefined ? k.like_rate + '%' : '-'}</td>
        <td>${k.share_rate !== null && k.share_rate !== undefined ? k.share_rate.toFixed(4) + '%' : '-'}</td>
        <td>${k.cvr !== null && k.cvr !== undefined ? k.cvr + '%' : '-'}</td>
      </tr>`;
    });
  });
  document.getElementById('addon-watch-funnel-tbl').innerHTML =
    `<thead><tr><th>소재유형 (디자인)</th><th>노출수</th><th>6s 시청</th><th>15s 시청</th><th>50% 도달</th><th>100% 완료</th><th>평균 시청</th><th>좋아요율</th><th>공유율</th><th>CVR</th></tr></thead><tbody>${wfRows}</tbody>`;

  // ============ 5.5 실행 가이드 — 부산 제외 + 디자인 변경 반영 ============
  const v1RatioNote = v1Verdict.verdict === 'positive'
    ? '구 디자인 시기의 애드온 효과는 명확하게 검증됨 (CVR 우위 + 통계적 유의)'
    : '구 디자인 시기 효과도 명확하지 않으므로 디자인 외 요인 점검 필요';
  const designV = dcVerdict.verdict;
  const guideHtml = `
    <div class="g4 aligned-2" style="gap:10px">
      <div class="action-card">
        <div class="card-title">W1 (6/1~6/7) — 소재유형 처방 적용</div>
        <div class="card-sub" style="margin-bottom:0">
          ${v2Better.length > 0 ? `<strong style="color:var(--t1)">${v2Better.join(' · ')}</strong>는 v2 신 디자인 계속·확대 운영.<br>` : ''}
          ${v1Better.length > 0 ? `<strong style="color:var(--red)">${v1Better.join(' · ')}</strong>는 v2 → v1 일부 복원 또는 디자인 콘셉트 재검토.<br>` : ''}
          ${(dtNoop.length > 0 || dtLow.length > 0) ? `<span class="muted">${[...dtNoop, ...dtLow].join('·')}은 광고 단위 누적 후 다음 라운드 재판단.</span>` : ''}
        </div>
      </div>
      <div class="action-card">
        <div class="card-title">W1 (6/1~6/7) — 부산 단독 학습 룰</div>
        <div class="card-sub" style="margin-bottom:0">
          부산은 5월 일부 미적용 + R10 학습 룰 대상이므로 본 5장 분석에서 분리. 부산 학습 안정화는 3.4 부산 학습 박스 기준으로 별도 모니터링하며, 6월 안정화 이후 표준 디자인 통합 검토.
        </div>
      </div>
      <div class="action-card">
        <div class="card-title">W2~W3 (6/8~6/21) — 디자인 효과 재측정</div>
        <div class="card-sub" style="margin-bottom:0">
          ${designV === 'v1_better'
            ? '디자인 변경이 전체 CVR에 부정적 영향을 준 신호. v1 복원 그룹과 v2 유지 그룹의 6월 추가 데이터로 재검정. v1 복원 그룹이 v2 유지 그룹보다 CVR 우세하면 7월 전면 v1 복원.'
            : (designV === 'v2_better'
              ? 'v2 신 디자인 우세 — 7월 표준화를 위해 6월 누적 표본 확보. p-value가 0.05 이하로 안정되면 표준화 결정.'
              : '디자인 효과 미미 — 소재유형 처방을 우선시하며 디자인 변경 자체에는 결정 보류.')}
        </div>
      </div>
      <div class="action-card">
        <div class="card-title">W4 (6/22~6/30) — 7월 디자인 결정</div>
        <div class="card-sub" style="margin-bottom:0">
          ${v1RatioNote}. 6월 데이터를 누적하여 ① v2 표준화 ② v1 부분 복원 ③ v2 디자인 부분 변경(클릭 vs 전환 트레이드오프 조정) 중 택일.
          ${dtLow.length > 0 ? `<br><span class="muted">표본 부족 그룹(${dtLow.join('·')})은 다음 라운드 재판단.</span>` : ''}
        </div>
      </div>
    </div>
  `;
  document.getElementById('addon-execution-guide').innerHTML = guideHtml;

  // ============ 5.A.1 부록 — 지점별 v1 / v2 (부산 제외) ============
  const branches = (DATA.meta.branches || []).filter(b => !(ms.excluded_branches || []).includes(b));

  // v1 vs 3~4월 비애드온 — 지점별
  let trsV1 = '';
  branches.forEach(b => {
    const r = (A.by_branch_v1 || {})[b];
    if (!r) return;
    const d = r.delta_pct;
    const warn = r.sample_warning ? ' <span style="color:var(--warn)" title="표본 부족 (클릭 <100)">⚠</span>' : '';
    trsV1 += `<tr><td class="lbl">${b}${warn}</td><td>${r.addon.ad_count}/${r.non_addon.ad_count}</td><td>${r.addon.clicks.toLocaleString()}/${r.non_addon.clicks.toLocaleString()}</td><td class="${cls(d.cpm,'low')}">${fmtSigned(d.cpm)}</td><td class="${cls(d.ctr,'high')}">${fmtSigned(d.ctr)}</td><td class="${cls(d.cvr,'high')}">${fmtSigned(d.cvr)}${sigBadge(d.cvr_p)}</td><td class="${cls(d.cpa,'low')}">${fmtSigned(d.cpa)}</td></tr>`;
  });
  document.getElementById('addon-branch-tbl-v1').innerHTML = `<thead><tr><th>지점</th><th>광고 (v1/비)</th><th>클릭 (v1/비)</th><th>CPM Δ</th><th>CTR Δ</th><th>CVR Δ</th><th>CPA Δ</th></tr></thead><tbody>${trsV1}</tbody>`;

  // v2 vs v1 — 지점별 디자인 직접 비교
  let trsV2 = '';
  branches.forEach(b => {
    const r = (A.by_branch_v2 || {})[b];
    if (!r) return;
    const d = r.delta_pct;
    const warn = r.sample_warning ? ' <span style="color:var(--warn)" title="표본 부족 (클릭 <100)">⚠</span>' : '';
    trsV2 += `<tr><td class="lbl">${b}${warn}</td><td>${(r.v1.clicks||0).toLocaleString()} → ${(r.v2.clicks||0).toLocaleString()}</td><td>${r.v1.cvr !== null && r.v1.cvr !== undefined ? r.v1.cvr + '%' : '-'} → ${r.v2.cvr !== null && r.v2.cvr !== undefined ? r.v2.cvr + '%' : '-'}</td><td>${r.v1.cpa ? fmt(r.v1.cpa) : '-'} → ${r.v2.cpa ? fmt(r.v2.cpa) : '-'}</td><td class="${cls(d.ctr,'high')}">${fmtSigned(d.ctr)}</td><td class="${cls(d.cvr,'high')}">${fmtSigned(d.cvr)}${sigBadge(d.cvr_p)}</td><td class="${cls(d.cpa,'low')}">${fmtSigned(d.cpa)}</td></tr>`;
  });
  document.getElementById('addon-branch-tbl-v2').innerHTML = `<thead><tr><th>지점</th><th>클릭 (v1→v2)</th><th>CVR (v1→v2)</th><th>CPA (v1→v2)</th><th>CTR Δ</th><th>CVR Δ</th><th>CPA Δ</th></tr></thead><tbody>${trsV2}</tbody>`;

  // ============ 5.A.2 부록 — 월별 추세 ============
  const monthly = A.monthly_trend || [];
  let mtrs = '';
  monthly.forEach(m => {
    const d = m.delta_pct;
    const warn = m.sample_warning ? ' <span style="color:var(--warn)" title="표본 부족 (클릭 <100)">⚠</span>' : '';
    const vBadge = m.design_version === 'v2'
      ? '<span style="font-size:8.5px;font-weight:800;background:rgba(52,211,153,.15);color:var(--t1);padding:2px 6px;border-radius:3px;margin-left:4px">신 v2</span>'
      : '<span style="font-size:8.5px;font-weight:800;background:rgba(148,163,184,.15);color:var(--tx2);padding:2px 6px;border-radius:3px;margin-left:4px">구 v1</span>';
    mtrs += `<tr><td class="lbl">${m.month}${vBadge}${warn}</td><td>${m.addon.clicks.toLocaleString()} / ${m.non_addon.clicks.toLocaleString()}</td><td>${m.addon.cvr !== null && m.addon.cvr !== undefined ? m.addon.cvr + '%' : '-'}</td><td>${m.non_addon.cvr !== null && m.non_addon.cvr !== undefined ? m.non_addon.cvr + '%' : '-'}</td><td class="${cls(d.cvr,'high')}">${fmtSigned(d.cvr)}${sigBadge(d.cvr_p)}</td><td class="muted">${d.cvr_p !== null && d.cvr_p !== undefined ? 'p=' + d.cvr_p : '-'}</td></tr>`;
  });
  document.getElementById('addon-monthly-tbl').innerHTML = `<thead><tr><th>월 (디자인)</th><th>클릭 (애드/비)</th><th>애드 CVR</th><th>비애드 CVR</th><th>CVR Δ%</th><th>p-value</th></tr></thead><tbody>${mtrs}</tbody>`;
})();

// ==================== R9 Q2 — 1.2 KPI Gap Caveat ====================
(function renderKpiGapCaveat() {
  const el = document.getElementById('kpi-gap-caveat');
  if (!el) return;
  const gap = (DATA.meta_caveats && DATA.meta_caveats.kpi_gap) || null;
  if (!gap) { el.style.display = 'none'; return; }
  el.innerHTML = `<div class="gap-caveat">
    <strong>KPI 갭 — 권장 ${gap.recommended_conv}건 vs KPI 목표 ${gap.kpi_target}건 (${gap.gap_amount > 0 ? '-' : '+'}${Math.abs(gap.gap_amount)}건, ${gap.gap_pct}%).</strong>
    ${gap.caveat}
  </div>`;
})();

// ==================== R10 — 3.4 부산 학습 박스 ====================
(function renderBusanLearningBox() {
  const el = document.getElementById('busan-learning-box');
  if (!el) return;
  const rec = (DATA.budget && DATA.budget.june_recommended_by_branch) || {};
  const busan = rec['부산'];
  if (!busan || !busan.learning_rule) { el.style.display = 'none'; return; }
  const lr = busan.learning_rule;
  const range = lr.pass_budget_range || [];
  el.innerHTML = `<div class="busan-box">
    <div class="busan-hdr">
      <span class="busan-tag">신규 학습 — 정상 산식 미적용</span>
      <span class="busan-title">부산 (codex R10 학습 룰)</span>
    </div>
    <div class="busan-row">기본 <strong>${fmt(lr.min_budget)}원</strong> · ${lr.observation_weeks}주 관찰 (6/1~6/21)</div>
    <div class="busan-grid">
      <div class="busan-row">통과 기준 <strong>CPA ≤ ${lr.cpa_pass_threshold ? fmt(lr.cpa_pass_threshold) + '원' : '-'}</strong> ${lr.pass_combine} <strong>CVR ≥ ${lr.cvr_pass_threshold !== null ? lr.cvr_pass_threshold + '%' : '-'}</strong></div>
      <div class="busan-row">통과 시 <strong>${range.length === 2 ? fmt(range[0]) + '~' + fmt(range[1]) + '원' : '-'}</strong> 정상 산식 편입</div>
      <div class="busan-row">미통과 시 ${lr.fail_action || '-'}</div>
      <div class="busan-row" style="color:var(--tx2)">※ ${lr.measurement_note || ''}</div>
    </div>
  </div>`;
})();

// ==================== R9 Q1 — 3.4 normalize 18M 보조 표 ====================
(function renderNormalize18mBox() {
  const el = document.getElementById('normalize-18m-box');
  if (!el) return;
  const nm = (DATA.budget && DATA.budget.normalize_18m_table) || null;
  if (!nm) { el.style.display = 'none'; return; }
  const dp = nm.deduction_priority || [];
  el.innerHTML = `<div class="norm-box">
    <div class="norm-hdr">18M cap 적용 시 (${nm.guideline_type} guideline) — 감액 우선순위</div>
    <div style="font-size:11px;color:var(--tx2);margin-bottom:8px">권장 ${fmt(nm.recommended_total)}원 vs cap ${fmt(nm.guideline_cap)}원 → 초과 ${fmt(nm.overage_amount)}원 (${nm.overage_pct > 0 ? '+' : ''}${nm.overage_pct}%). 18M 적용 시 아래 순위로 감액합니다.</div>
    <ol class="norm-list">${dp.map(d => `<li><strong>${d.priority}. ${d.target}</strong> — <span class="muted">${d.rationale}</span></li>`).join('')}</ol>
    <div style="font-size:10.5px;color:var(--tx2);margin-top:8px;padding-top:8px;border-top:1px dashed var(--bd)">${nm.note || ''}</div>
  </div>`;
})();

// ==================== R9 Q3 — 5.D Appendix 부록 소재 표 ====================
(function renderAppendixCreatives() {
  const el = document.getElementById('appendix-creative-tbl');
  if (!el) return;
  const ca = DATA.creative_appendix || {branches:{}, tier_rationale:{}};
  const branches = ca.branches || {};
  const tr = ca.tier_rationale || {};
  if (Object.keys(branches).length === 0) { el.innerHTML = '<div class="muted">소재 분류 데이터 없음</div>'; return; }
  // 데이터 출처 안내 (현재 부분월에 TIER 분류 대상이 없어 직전 dir에서 가져온 경우)
  let dataSourceNotice = '';
  if (ca.data_source_dir) {
    const dsd = ca.data_source_dir;
    const formatted = dsd.length === 8 ? `${dsd.slice(0,4)}-${dsd.slice(4,6)}-${dsd.slice(6,8)}` : dsd;
    dataSourceNotice = `<div class="gap-caveat" style="margin-bottom:14px;border-left-color:var(--warn);background:rgba(248,191,79,.06);font-size:11.5px;line-height:1.6">현재 분석 기간(5월 부분월)은 ON 광고가 적어 TIER 분류 대상이 부족합니다. 본 부록은 직전 분류 결과(<strong>${formatted} 기준</strong>)를 표시하여 운영 의사결정 데이터 손실을 막습니다. 시청 깊이·인게이지먼트 컬럼은 신규 수집 항목이라 직전 기준에서는 공란일 수 있습니다.</div>`;
  }
  // 시청 깊이 + 인게이지먼트 데이터 유무 확인
  const hasDepth = Object.values(branches).some(items => (items || []).some(it => it.v6s_rate !== null && it.v6s_rate !== undefined));
  const hasEng = Object.values(branches).some(items => (items || []).some(it => it.share_rate !== null && it.share_rate !== undefined));
  let heads = ['소재명', 'TIER', '근거', '권장 액션', '비용', '전환'];
  if (hasDepth) heads = heads.concat(['6s 시청률', '100% 완료', '평균 시청']);
  if (hasEng) heads = heads.concat(['좋아요율', '공유율']);
  let html = dataSourceNotice;
  // 상단 TIER 설명 + 시청률·인게이지먼트 안내
  const extraNote = (hasDepth || hasEng) ? `<div style="font-size:10.5px;color:var(--tx2);margin-top:8px;padding-top:8px;border-top:1px dashed var(--bd);line-height:1.5">
    ${hasDepth ? '<strong>시청률 지표:</strong> 6s 시청률 = 6초 이상 시청 / 노출수 (애드온 노출 시점 도달률 추정). 100% 완료 = 영상 끝까지 본 비율. 평균 시청 = 평균 재생 시간(초).<br>' : ''}
    ${hasEng ? '<strong>인게이지먼트:</strong> 좋아요율·공유율 = 노출수 대비 좋아요·공유 비율. 공유율이 높은 소재는 바이럴형, 클릭→전환 CVR이 높은 소재는 전환형으로 구분 가능합니다.' : ''}
  </div>` : '';
  html += `<div class="evidence-card" style="margin-bottom:14px;padding:12px 14px"><div style="font-size:10px;font-weight:800;color:var(--acc);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">TIER 분류 기준</div>${Object.entries(tr).map(([k,v]) => `<div style="font-size:11px;color:var(--tx);margin-bottom:3px"><strong>${k}</strong> — ${v}</div>`).join('')}${extraNote}</div>`;
  html += `<div class="gap-caveat" style="margin-bottom:14px;border-left-color:var(--tx3);background:rgba(148,163,184,.05);font-size:11.5px;line-height:1.6">본 부록은 발표·공유 시 가독성을 위해 지점별로 <strong>접힘 상태</strong>로 제공됩니다. 필요한 지점만 펼쳐서 참고하시면 됩니다. 본문에서 소재 의사결정은 3.3 운영 처방 카드와 4장 콘텐츠 큐레이션으로 충분하며, 본 부록은 손실 없는 운영 데이터 참조용입니다.</div>`;
  // 지점별 표 (접힘)
  (DATA.meta.branches || []).forEach(b => {
    const items = branches[b];
    if (!items || items.length === 0) return;
    let trs = '';
    items.forEach(it => {
      const depthCells = hasDepth ? `<td>${it.v6s_rate !== null && it.v6s_rate !== undefined ? it.v6s_rate.toFixed(1) + '%' : '-'}</td><td>${it.p100_rate !== null && it.p100_rate !== undefined ? it.p100_rate.toFixed(1) + '%' : '-'}</td><td>${it.avg_video_sec !== null && it.avg_video_sec !== undefined ? it.avg_video_sec.toFixed(1) + 's' : '-'}</td>` : '';
      const engCells = hasEng ? `<td>${it.like_rate !== null && it.like_rate !== undefined ? it.like_rate.toFixed(2) + '%' : '-'}</td><td>${it.share_rate !== null && it.share_rate !== undefined ? it.share_rate.toFixed(4) + '%' : '-'}</td>` : '';
      trs += `<tr><td class="lbl">${it.name}</td><td><strong>${it.tier}</strong></td><td class="muted">${it.evidence}</td><td>${it.recommended_action}</td><td>${it.cost !== null ? fmt(it.cost) + '원' : '-'}</td><td>${it.conversions !== null ? it.conversions + '건' : '-'}</td>${depthCells}${engCells}</tr>`;
    });
    // 지점별 TIER 분포 요약
    const tierCount = items.reduce((a, it) => { a[it.tier] = (a[it.tier] || 0) + 1; return a; }, {});
    const tierSummary = Object.entries(tierCount).map(([k,v]) => `${k} ${v}`).join(' · ');
    html += `<details class="appx" style="margin-bottom:8px"><summary><span><span class="appx-num">${b}</span>${items.length}개 소재 (${tierSummary})</span></summary><div class="appx-body"><div class="evidence-card" style="padding:0;overflow:hidden"><div class="tw"><table><thead><tr>${heads.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${trs}</tbody></table></div></div></div></details>`;
  });
  el.innerHTML = html;
})();

// ==================== R9 종합 누락 — 5.E 시즌성 캐비엇 ====================
(function renderSeasonalityCaveat() {
  const el = document.getElementById('seasonality-caveat');
  if (!el) return;
  const seas = (DATA.meta_caveats && DATA.meta_caveats.seasonality) || null;
  if (!seas) { el.style.display = 'none'; return; }
  el.innerHTML = `<div class="gap-caveat" style="border-left-color:var(--blue);background:rgba(96,165,250,.05)"><strong>시즌성 · 외부 변수.</strong> ${seas.caveat}</div>`;
})();

// ==================== 06 타겟팅 정합성 진단 (Phase 1A) ====================
(function renderTargetingHealth() {
  const th = DATA.targeting_health || {};
  if (!th.available) {
    const j = document.getElementById('targeting-judgement');
    if (j) j.innerHTML = `<div class="muted">${th.note || '오디언스 데이터 없음 — 6장 데이터 수집 필요'}</div>`;
    return;
  }
  const gv = th.gender_verdict || {};
  const gs = th.gender_summary || {};
  const an = th.none_anomaly;
  const ageSig = th.age_signal;
  const rec = th.recommendation || {};
  const total = th.total || {};

  const verdictColor = {
    aligned: 'var(--t1)', minor_leak: 'var(--warn)', leak: 'var(--red)',
    attribution_unidentified: 'var(--warn)',
    inefficient: 'var(--red)', undersupplied: 'var(--t1)', noop: 'var(--tx3)',
  };
  const gc = verdictColor[gv.verdict] || 'var(--tx2)';
  const ageColor = ageSig ? (verdictColor[ageSig.verdict] || 'var(--tx2)') : 'var(--tx2)';

  // 6.1 진단 결과 헤더
  document.getElementById('targeting-judgement').innerHTML = `
    <div style="background:linear-gradient(135deg, var(--s2) 0%, var(--s1) 100%);border-left:5px solid ${gc};border-radius:8px;padding:16px 20px;margin-bottom:14px">
      <div style="font-size:10px;font-weight:800;color:${gc};letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px">진단 헤드라인</div>
      <div style="font-size:16px;font-weight:900;color:var(--tx);margin-bottom:8px">${rec.headline || '-'}</div>
      <div style="font-size:12.5px;color:var(--tx);line-height:1.6;margin-bottom:8px">${rec.tone || ''}</div>
      ${(rec.bullets && rec.bullets.length > 0) ? `<ul style="margin:6px 0 0 0;padding-left:18px;font-size:11.5px;color:var(--tx);line-height:1.7">${rec.bullets.map(b => `<li>${b}</li>`).join('')}</ul>` : ''}
    </div>
    <div style="font-size:10.5px;color:var(--tx2);line-height:1.5">데이터 기간 ${th.data_period} · 총 노출 ${total.impressions ? total.impressions.toLocaleString() : '-'} · 총 전환 ${total.conversions || 0}건</div>
  `;

  // 6.2 성별 노출 정합성 카드
  const total_impr = total.impressions || 0;
  const cards = [
    { lbl: '여성 노출 비중', val: (gs.female_impr_pct !== null && gs.female_impr_pct !== undefined) ? gs.female_impr_pct + '%' : '-', sub: '의도(여성 고정) 대비', color: gs.female_impr_pct > 95 ? 'var(--t1)' : 'var(--warn)' },
    { lbl: '남성 노출 비중', val: (gs.male_impr_pct !== null && gs.male_impr_pct !== undefined) ? gs.male_impr_pct + '%' : '-', sub: gs.male_impr_pct === 0 ? '누수 없음 ✓' : '누수 감지 ⚠', color: gs.male_impr_pct === 0 ? 'var(--t1)' : 'var(--red)' },
    { lbl: '미상 노출 비중', val: (gs.unknown_impr_pct !== null && gs.unknown_impr_pct !== undefined) ? gs.unknown_impr_pct + '%' : '-', sub: '미식별 분류', color: 'var(--tx2)' },
    { lbl: '미상 전환 비중', val: (gs.unknown_conv_pct !== null && gs.unknown_conv_pct !== undefined) ? gs.unknown_conv_pct + '%' : '-', sub: an ? '이상 신호 ⚠' : '정상 범위', color: an ? 'var(--warn)' : 'var(--tx2)' },
  ];
  document.getElementById('targeting-gender-cards').innerHTML = `<div class="g4" style="gap:10px">${cards.map(c => `
    <div style="background:var(--s1);border:1px solid var(--bd);border-left:4px solid ${c.color};border-radius:6px;padding:12px 14px">
      <div style="font-size:9.5px;font-weight:800;color:var(--tx2);letter-spacing:.06em;text-transform:uppercase;margin-bottom:5px">${c.lbl}</div>
      <div style="font-size:20px;font-weight:900;font-family:'DM Mono',monospace;color:${c.color}">${c.val}</div>
      <div style="font-size:10px;color:var(--tx2);margin-top:3px">${c.sub}</div>
    </div>`).join('')}</div>`;

  // NONE 분류 이상 신호 박스
  if (an) {
    document.getElementById('targeting-none-anomaly').innerHTML = `
      <div class="gap-caveat" style="border-left-color:var(--warn);background:rgba(248,191,79,.06);font-size:11.5px;line-height:1.6">
        <strong>${an.label}.</strong> ${an.rationale} · 미상 노출 ${an.unknown_impr_count.toLocaleString()} · 미상 전환 ${an.unknown_conv_count}건
      </div>
    `;
  } else {
    document.getElementById('targeting-none-anomaly').innerHTML = '';
  }

  // 6.3 여성 연령별 효율 표
  const byAge = th.by_age_female || {};
  const ageOrder = ['18-24', '25-34', '35-44', '45-54', '≥55', 'Unknown'];
  let ageRows = '';
  ageOrder.forEach(ag => {
    const k = byAge[ag];
    if (!k) return;
    const isTargetAge = ageSig && ageSig.age_group === ag;
    const highlight = isTargetAge ? `background:${ageSig.verdict === 'inefficient' ? 'rgba(248,113,113,.05)' : 'rgba(52,211,153,.05)'}` : '';
    ageRows += `<tr style="${highlight}">
      <td class="lbl">${ag}${isTargetAge ? ` <span style="font-size:8.5px;font-weight:800;background:${ageSig.verdict === 'inefficient' ? 'rgba(248,113,113,.18)' : 'rgba(52,211,153,.18)'};color:${ageColor};padding:2px 6px;border-radius:3px;margin-left:4px">${ageSig.verdict === 'inefficient' ? '비효율' : '확대 기회'}</span>` : ''}</td>
      <td>${k.impressions.toLocaleString()}</td>
      <td>${k.impr_share}%</td>
      <td>${k.clicks.toLocaleString()}</td>
      <td>${k.conversions}</td>
      <td>${k.ctr !== null ? k.ctr + '%' : '-'}</td>
      <td>${k.cvr !== null ? k.cvr + '%' : '-'}</td>
      <td>${k.cpa ? fmt(k.cpa) + '원' : '-'}</td>
    </tr>`;
  });
  document.getElementById('targeting-age-tbl').innerHTML = `<thead><tr><th>연령</th><th>노출</th><th>노출 비중</th><th>클릭</th><th>전환</th><th>CTR</th><th>CVR</th><th>CPA</th></tr></thead><tbody>${ageRows}</tbody>`;

  // 연령 신호 박스 + 운영 이력
  const ah = th.age_history || {};
  let ageBoxes = '';
  if (ageSig && ageSig.verdict !== 'noop') {
    ageBoxes += `
      <div class="gap-caveat" style="border-left-color:${ageColor};background:${ageSig.verdict === 'inefficient' ? 'rgba(248,113,113,.06)' : 'rgba(52,211,153,.06)'};font-size:11.5px;line-height:1.6;margin-bottom:10px">
        <strong>${ageSig.label}.</strong> ${ageSig.rationale}
      </div>
    `;
  }
  // 운영 이력 박스 — 의도적 배제 + 한정 재운영
  if (ah.available && (ah.excluded_ranges?.length > 0 || ah.is_limited_restart)) {
    const exclStr = (ah.excluded_ranges || []).map(r => `${r.start} ~ ${r.end}`).join(', ');
    const restartList = ah.restart_branches || [];
    const postBr = ah.post_exclusion_branches || {};
    let postRows = '';
    Object.entries(postBr).forEach(([b, k]) => {
      postRows += `<tr><td class="lbl">${b}</td><td>${k.impressions.toLocaleString()}</td><td>${k.clicks.toLocaleString()}</td><td>${k.conversions}</td><td>${k.cvr !== null ? k.cvr + '%' : '-'}</td><td>${k.cpa ? fmt(k.cpa) + '원' : '-'}</td></tr>`;
    });
    ageBoxes += `
      <div class="evidence-card" style="padding:12px 14px;background:rgba(167,139,250,.05);border-left:4px solid #a78bfa;border-radius:6px;font-size:11.5px;line-height:1.65">
        <div style="font-size:10px;font-weight:800;color:#a78bfa;letter-spacing:.06em;text-transform:uppercase;margin-bottom:6px">25-34 운영 이력 (의도적 배제 + 한정 재운영)</div>
        ${exclStr ? `<div style="margin-bottom:6px"><strong>의도적 배제 기간:</strong> ${exclStr} — 데이터에서 자동 감지된 노출 0 구간</div>` : ''}
        ${ah.is_limited_restart ? `<div style="margin-bottom:6px"><strong>배제 이후 한정 재운영:</strong> <strong style="color:#a78bfa">${restartList.join(', ')}</strong> 한정으로만 재운영 중 (다른 지점은 노출 0 유지)</div>` : ''}
        ${postRows ? `<div style="margin-top:8px"><div style="font-size:10px;color:var(--tx2);margin-bottom:4px">한정 재운영 결과:</div><div class="tw"><table><thead><tr><th>지점</th><th>노출</th><th>클릭</th><th>전환</th><th>CVR</th><th>CPA</th></tr></thead><tbody>${postRows}</tbody></table></div></div>` : ''}
        <div style="font-size:10.5px;color:var(--tx2);margin-top:8px">${ah.context_note || ''}</div>
      </div>
    `;
  }
  document.getElementById('targeting-age-signal').innerHTML = ageBoxes;

  // 6.4 지점별 노출 품질
  const branches = DATA.meta.branches || [];
  const by_b = th.by_branch || {};
  let bRows = '';
  const allBranches = [...branches, ...(by_b['부산'] ? ['부산'] : [])].filter((v, i, a) => a.indexOf(v) === i);
  allBranches.forEach(b => {
    const r = by_b[b];
    if (!r) return;
    const fpct = r.female_impr_pct;
    const ucpct = r.unknown_conv_pct;
    const fpctColor = fpct !== null && fpct < 95 ? 'var(--warn)' : 'var(--tx)';
    const ucColor = ucpct !== null && ucpct > 10 ? 'var(--warn)' : 'var(--tx)';
    bRows += `<tr><td class="lbl">${b}</td><td>${r.total_impr.toLocaleString()}</td><td style="color:${fpctColor}">${fpct !== null ? fpct + '%' : '-'}</td><td>${r.male_impr.toLocaleString()}</td><td>${r.unknown_impr.toLocaleString()}</td><td>${r.total_conv}</td><td style="color:${ucColor}">${ucpct !== null ? ucpct + '%' : '-'}</td></tr>`;
  });
  document.getElementById('targeting-branch-tbl').innerHTML = `<thead><tr><th>지점</th><th>총 노출</th><th>여성 비중</th><th>남성 노출</th><th>미상 노출</th><th>총 전환</th><th>미상 전환 비중</th></tr></thead><tbody>${bRows}</tbody>`;

  // 6.A 분석 기준 안내
  document.getElementById('targeting-note').innerHTML = `
    <div class="evidence-card" style="padding:12px 14px;font-size:11px;color:var(--tx);line-height:1.7">
      <div style="font-size:9.5px;font-weight:800;color:var(--tx2);letter-spacing:.06em;text-transform:uppercase;margin-bottom:6px">분석 방법 및 한계</div>
      <ul style="margin:0;padding-left:18px">
        <li>TikTok Audience report API (report_type=AUDIENCE)로 dimensions=[ad_id, stat_time_day, age, gender] 수집</li>
        <li>성별 정합성: 운영 의도(여성 고정) 대비 실제 노출 분포 비교. 남성 노출 0건 = 누수 없음</li>
        <li>미상(NONE) 분류: TikTok이 사용자 성별을 식별하지 못한 케이스. 노출 대비 전환 비중이 비대칭이면 어트리뷰션 비식별 정황 (cross-device 추정 포함 가능)</li>
        <li>연령 효율: 여성 한정 연령별 CVR 비교. 다른 연령대 평균 대비 50% 미만이면 비효율 구간, 100% 이상이면 확대 기회로 분류</li>
        <li>${th.note || ''}</li>
      </ul>
    </div>
  `;
})();

// ==================== 07 지역 도달 정합성 (Phase 1B) ====================
(function renderGeoLeakage() {
  const geo = DATA.geo_leakage || {};
  if (!geo.available) {
    const j = document.getElementById('geo-judgement');
    if (j) j.innerHTML = `<div class="muted">${geo.note || '지역 데이터 없음 — province 수집 필요'}</div>`;
    return;
  }
  const rec = geo.recommendation || {};
  const total = geo.total || {};
  const verdictColor = {
    clean: 'var(--t1)', minor_leak: 'var(--warn)', major_leak: 'var(--red)',
  };
  const recColor = verdictColor[rec.verdict] || 'var(--tx2)';
  const lo = geo.labels_overall || {};

  // 7.1 진단 결과
  document.getElementById('geo-judgement').innerHTML = `
    <div style="background:linear-gradient(135deg, var(--s2) 0%, var(--s1) 100%);border-left:5px solid ${recColor};border-radius:8px;padding:16px 20px;margin-bottom:14px">
      <div style="font-size:10px;font-weight:800;color:${recColor};letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px">진단 헤드라인</div>
      <div style="font-size:16px;font-weight:900;color:var(--tx);margin-bottom:8px">${rec.headline || '-'}</div>
      <div style="font-size:12.5px;color:var(--tx);line-height:1.6;margin-bottom:8px">${rec.tone || ''}</div>
      ${(rec.bullets && rec.bullets.length > 0) ? `<ul style="margin:6px 0 0 0;padding-left:18px;font-size:11.5px;color:var(--tx);line-height:1.7">${rec.bullets.filter(b => b).map(b => `<li>${b}</li>`).join('')}</ul>` : ''}
    </div>
    <div style="font-size:10.5px;color:var(--tx2);line-height:1.5">데이터 기간 ${geo.data_period} · 총 노출 ${total.impressions ? total.impressions.toLocaleString() : '-'} · 총 전환 ${total.conversions || 0}건</div>
  `;

  // 7.2 전체 정합/생활권/누수 카드
  const cards = [
    { lbl: '정합 (핵심 광역)', val: (lo['정합'] || {}).impr_pct, sub: ((lo['정합'] || {}).impr || 0).toLocaleString() + '회', color: 'var(--t1)' },
    { lbl: '생활권 (인접 광역)', val: (lo['생활권'] || {}).impr_pct, sub: ((lo['생활권'] || {}).impr || 0).toLocaleString() + '회', color: 'var(--blue, #60a5fa)' },
    { lbl: '누수 (매칭권 밖)', val: (lo['누수'] || {}).impr_pct, sub: ((lo['누수'] || {}).impr || 0).toLocaleString() + '회', color: (lo['누수'] || {}).impr_pct > 5 ? 'var(--warn)' : 'var(--tx2)' },
  ];
  document.getElementById('geo-overall-cards').innerHTML = `<div class="g3" style="gap:10px">${cards.map(c => `
    <div style="background:var(--s1);border:1px solid var(--bd);border-left:4px solid ${c.color};border-radius:7px;padding:14px 16px">
      <div style="font-size:9.5px;font-weight:800;color:var(--tx2);letter-spacing:.06em;text-transform:uppercase;margin-bottom:5px">${c.lbl}</div>
      <div style="font-size:24px;font-weight:900;font-family:'DM Mono',monospace;color:${c.color}">${c.val !== null && c.val !== undefined ? c.val + '%' : '-'}</div>
      <div style="font-size:10px;color:var(--tx2);margin-top:3px">${c.sub}</div>
    </div>`).join('')}</div>`;

  // 7.3 지점별 누수 진단 표
  const byBranch = geo.by_branch || {};
  let branchRows = '';
  const branchOrder = (DATA.meta.branches || []).concat(['부산']).filter((v, i, a) => a.indexOf(v) === i);
  branchOrder.forEach(b => {
    const r = byBranch[b];
    if (!r) return;
    const v = r.verdict || {};
    const vc = verdictColor[v.verdict] || 'var(--tx2)';
    const leak = r.labels['누수'].impr_pct;
    const topProvinces = (r.top_provinces || []).slice(0, 3).map(p => {
      const c = p.match_label === '정합' ? 'var(--t1)' : (p.match_label === '생활권' ? 'var(--blue, #60a5fa)' : 'var(--red)');
      return `<span style="color:${c}">${p.province} ${p.impr_pct}%</span>`;
    }).join(' · ');
    branchRows += `<tr>
      <td class="lbl">${b}</td>
      <td>${r.core_province}</td>
      <td>${r.total_impr.toLocaleString()}</td>
      <td style="color:var(--t1)">${r.labels['정합'].impr_pct}%</td>
      <td style="color:var(--blue, #60a5fa)">${r.labels['생활권'].impr_pct}%</td>
      <td style="color:${leak >= 15 ? 'var(--red)' : (leak >= 5 ? 'var(--warn)' : 'var(--tx2)')};font-weight:${leak >= 5 ? '800' : 'normal'}">${leak}%</td>
      <td><strong style="color:${vc}">${v.label || '-'}</strong></td>
      <td class="muted">${topProvinces}</td>
    </tr>`;
  });
  document.getElementById('geo-branch-tbl').innerHTML = `<thead><tr><th>지점</th><th>핵심 광역</th><th>총 노출</th><th>정합%</th><th>생활권%</th><th>누수%</th><th>판단</th><th>노출 상위 지역</th></tr></thead><tbody>${branchRows}</tbody>`;

  // 7.4 누수 노출 지역 TOP
  const oos = geo.out_of_scope_provinces || [];
  let leakRows = '';
  oos.forEach(p => {
    leakRows += `<tr><td class="lbl">${p.province}</td><td>${p.impr.toLocaleString()}</td><td>${p.impr_pct}%</td><td>${p.clicks.toLocaleString()}</td><td>${p.conv}</td></tr>`;
  });
  if (leakRows === '') leakRows = '<tr><td colspan="5" style="text-align:center;color:var(--tx2)">매칭권 밖 노출 없음</td></tr>';
  document.getElementById('geo-leakage-tbl').innerHTML = `<thead><tr><th>광역</th><th>노출</th><th>전체 대비%</th><th>클릭</th><th>전환</th></tr></thead><tbody>${leakRows}</tbody>`;

  // 7.A 매칭 룰 + 분석 기준
  const rules = geo.match_rules || {};
  const defs = rules.definition || {};
  const inclusive = rules.inclusive || {};
  let ruleRows = '';
  Object.entries(inclusive).forEach(([b, list]) => {
    ruleRows += `<tr><td class="lbl">${b}</td><td>${rules.core[b]}</td><td>${list.join(' · ')}</td></tr>`;
  });
  document.getElementById('geo-note').innerHTML = `
    <div class="evidence-card" style="padding:12px 14px;font-size:11px;color:var(--tx);line-height:1.7;margin-bottom:10px">
      <div style="font-size:9.5px;font-weight:800;color:var(--tx2);letter-spacing:.06em;text-transform:uppercase;margin-bottom:6px">분류 정의</div>
      ${Object.entries(defs).map(([k, v]) => `<div style="margin-bottom:3px"><strong style="color:${k === '정합' ? 'var(--t1)' : (k === '생활권' ? 'var(--blue, #60a5fa)' : 'var(--red)')}">${k}</strong> — ${v}</div>`).join('')}
    </div>
    <div class="evidence-card" style="padding:0;overflow:hidden;margin-bottom:10px"><div class="tw"><table><thead><tr><th>지점</th><th>핵심 광역</th><th>생활권 매칭</th></tr></thead><tbody>${ruleRows}</tbody></table></div></div>
    <div class="gap-caveat" style="border-left-color:var(--warn);background:rgba(248,191,79,.05);font-size:11px;line-height:1.6">
      <strong>해석 한계.</strong> ${geo.note || ''}
    </div>
  `;
})();
"""
