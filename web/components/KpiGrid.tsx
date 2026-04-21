import { fmt, fmtMan, fmtPct, fmtDiff, diffColor } from '@/lib/format';

interface KPI { cost: number; conv: number; clicks: number; cpa: number; ctr: number; cvr: number }

export function KpiGrid({ now, prev }: { now: KPI; prev: KPI }) {
  const items = [
    { label: '광고비', value: fmtMan(now.cost), diff: now.cost - prev.cost, invert: true },
    { label: '전환수', value: fmt(now.conv, '건'), diff: now.conv - prev.conv, invert: false },
    { label: 'CPA', value: fmt(now.cpa, '원'), diff: now.cpa - prev.cpa, invert: true },
    { label: 'CTR', value: fmtPct(now.ctr), diff: (now.ctr - prev.ctr), invert: false, unit: 'p' },
    { label: 'CVR', value: fmtPct(now.cvr), diff: (now.cvr - prev.cvr), invert: false, unit: 'p' },
    { label: '클릭', value: fmt(now.clicks, '회'), diff: now.clicks - prev.clicks, invert: false },
  ];
  return (
    <section className="grid grid-cols-2 md:grid-cols-6 gap-3">
      {items.map((it) => (
        <div key={it.label} className="card">
          <div className="text-xs text-slate-400 mb-1">{it.label}</div>
          <div className="text-xl font-bold">{it.value}</div>
          <div className={`text-xs mt-1 ${diffColor(it.diff, it.invert)}`}>
            {fmtDiff(it.diff, it.unit ?? '원')}
          </div>
        </div>
      ))}
    </section>
  );
}
