import { loadDaily } from '@/lib/reports';
import { notFound } from 'next/navigation';
import { fmt, fmtMan, fmtPct, fmtDiff, diffColor } from '@/lib/format';
import { DailyBranchGrid } from '@/components/DailyBranchGrid';

export const dynamic = 'force-dynamic';

export default async function DailyDetailPage({ params }: { params: { date: string } }) {
  const data = await loadDaily(params.date);
  if (!data) notFound();

  const d = data.kpi_daily;
  const p = data.kpi_prev || {};

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold">데일리 리포트 · {data.date_label}</h1>
        <p className="text-sm text-slate-400">{data.date}</p>
      </header>

      {/* 월 목표 */}
      <section className="card">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">📅 월 목표 현황</h2>
          <span className="text-xs text-slate-400">잔여 {data.goal.remaining_days}일</span>
        </div>
        <div className="grid grid-cols-3 gap-4 mb-3 text-sm">
          <div>
            <div className="text-slate-400 text-xs mb-1">전환 진행률</div>
            <div className="text-lg font-bold">
              {data.goal.conv_current.toLocaleString()} / {data.goal.conv_target.toLocaleString()}건
            </div>
            <div className="text-xs text-brand-primary">{data.goal.conv_pct}%</div>
          </div>
          <div>
            <div className="text-slate-400 text-xs mb-1">예산 소진율</div>
            <div className="text-lg font-bold">{data.goal.budget_pct}%</div>
            <div className="text-xs text-slate-400">총예산 {fmtMan(data.goal.budget_total)}</div>
          </div>
          <div>
            <div className="text-slate-400 text-xs mb-1">누적 CPA</div>
            <div className="text-lg font-bold">{fmt(data.kpi_cum.cpa, '원')}</div>
            <div className="text-xs text-slate-400">CVR {fmtPct(data.kpi_cum.cvr)}</div>
          </div>
        </div>
        <div className="h-2 bg-brand-bg rounded overflow-hidden">
          <div className="h-full bg-brand-primary" style={{ width: `${Math.min(data.goal.conv_pct, 100)}%` }} />
        </div>
      </section>

      {/* 어제 KPI */}
      <section>
        <h2 className="font-semibold mb-3">💰 어제 성과 (전일비)</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <KpiCard label="광고비" value={fmtMan(d.cost)} diff={d.cost - (p.cost ?? 0)} invert />
          <KpiCard label="전환수" value={fmt(d.conv, '건')} diff={d.conv - (p.conv ?? 0)} />
          <KpiCard label="CPA" value={fmtMan(d.cpa)} diff={(d.cpa ?? 0) - (p.cpa ?? 0)} invert />
          <KpiCard label="CTR" value={fmtPct(d.ctr)} diff={(d.ctr ?? 0) - (p.ctr ?? 0)} unit="p" />
          <KpiCard label="CVR" value={fmtPct(d.cvr)} diff={(d.cvr ?? 0) - (p.cvr ?? 0)} unit="p" />
        </div>
      </section>

      {/* 지점 Best/Focus */}
      <section>
        <h2 className="font-semibold mb-3">📍 지점별 현황</h2>
        <DailyBranchGrid branches={data.branches} />
      </section>

      {/* 특이사항 */}
      {(data.notable_lines?.length || data.anomaly_lines?.length || data.zero_conv_lines?.length) > 0 && (
        <section className="card">
          <h2 className="font-semibold mb-3">📋 특이사항</h2>
          <div className="space-y-1 text-sm font-mono whitespace-pre-wrap">
            {data.zero_conv_lines?.map((ln, i) => <div key={`z${i}`} className="text-slate-300">{ln}</div>)}
            {data.anomaly_lines?.map((ln, i) => <div key={`a${i}`} className="text-slate-300">{ln}</div>)}
            {data.notable_lines?.map((ln, i) => <div key={`n${i}`} className="text-slate-300">{ln}</div>)}
          </div>
        </section>
      )}

      {/* 체크포인트 */}
      {data.checkpoints?.length > 0 && (
        <section className="card">
          <h2 className="font-semibold mb-3">🛠 오늘의 체크포인트</h2>
          <ul className="space-y-2 text-sm">
            {data.checkpoints.map((cp, i) => (
              <li key={i} className="border-l-2 border-brand-primary pl-3 text-slate-300">{cp}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function KpiCard({
  label,
  value,
  diff,
  invert,
  unit = '원',
}: {
  label: string;
  value: string;
  diff: number;
  invert?: boolean;
  unit?: string;
}) {
  return (
    <div className="card">
      <div className="text-xs text-slate-400 mb-1">{label}</div>
      <div className="text-xl font-bold">{value}</div>
      <div className={`text-xs mt-1 ${diffColor(diff, invert)}`}>{fmtDiff(diff, unit)}</div>
    </div>
  );
}
