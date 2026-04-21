import { loadLatestWeekly } from '@/lib/reports';
import { fmt, fmtMan, fmtPct, fmtDiff, diffColor } from '@/lib/format';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  const latest = await loadLatestWeekly();

  if (!latest) {
    return (
      <div className="card">
        <p className="text-slate-400">아직 생성된 리포트가 없습니다.</p>
      </div>
    );
  }

  const { date, data } = latest;
  const k = data.kpi_this;
  const p = data.kpi_prev;

  return (
    <div className="space-y-6">
      <section>
        <div className="flex items-baseline justify-between">
          <h1 className="text-2xl font-bold">최신 위클리 요약</h1>
          <span className="text-sm text-slate-400">{data.period_this_full}</span>
        </div>
      </section>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="광고비" value={fmtMan(k.cost)} sub={fmtDiff(k.cost - p.cost)} subClass={diffColor(k.cost - p.cost, true)} />
        <KpiCard label="전환수" value={fmt(k.conv, '건')} sub={fmtDiff(k.conv - p.conv, '건')} subClass={diffColor(k.conv - p.conv)} />
        <KpiCard label="CPA" value={fmt(k.cpa, '원')} sub={fmtDiff(k.cpa - p.cpa)} subClass={diffColor(k.cpa - p.cpa, true)} />
        <KpiCard label="CVR" value={fmtPct(k.cvr)} sub={fmtDiff((k.cvr - p.cvr) * 100, 'p') .replace('원', '')} subClass={diffColor(k.cvr - p.cvr)} />
      </section>

      <section className="card">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">월 전환 목표</h2>
          <span className="text-xs text-slate-400">잔여 예상 {data.proj_pct}%</span>
        </div>
        <div className="h-2 bg-brand-bg rounded overflow-hidden mb-1">
          <div
            className="h-full bg-brand-primary"
            style={{ width: `${Math.min(data.conv_pct, 100)}%` }}
          />
        </div>
        <p className="text-sm text-slate-400">
          {data.conv_so_far.toLocaleString()} / {data.monthly_target_conv.toLocaleString()}건 ({data.conv_pct}%)
        </p>
      </section>

      <section className="card">
        <h2 className="font-semibold mb-3">인사이트</h2>
        <ul className="space-y-3">
          {data.insights.map((ins: any, i: number) => (
            <li key={i} className="border-l-2 pl-3" style={{ borderColor: ins.color }}>
              <div className="text-sm font-medium" style={{ color: ins.color }}>
                [{ins.type}] {ins.title}
              </div>
              <ul className="mt-1 ml-4 text-sm text-slate-300 list-disc">
                {ins.points.map((p: string, j: number) => (
                  <li key={j}>{p}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </section>

      <div className="text-right">
        <Link
          href={`/weekly/${date}`}
          className="inline-block text-sm text-brand-primary hover:underline"
        >
          상세 보기 →
        </Link>
      </div>
    </div>
  );
}

function KpiCard({ label, value, sub, subClass }: { label: string; value: string; sub: string; subClass: string }) {
  return (
    <div className="card">
      <div className="text-xs text-slate-400 mb-1">{label}</div>
      <div className="text-xl font-bold">{value}</div>
      <div className={`text-xs mt-1 ${subClass}`}>{sub}</div>
    </div>
  );
}
