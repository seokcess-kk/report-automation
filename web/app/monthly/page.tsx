import { listMonthlyDates, loadMonthly } from '@/lib/reports';
import Link from 'next/link';
import { fmtMan, fmtPct } from '@/lib/format';

export const dynamic = 'force-dynamic';

export default async function MonthlyListPage() {
  const months = await listMonthlyDates();
  const items = await Promise.all(months.map(async (m) => ({ month: m, data: await loadMonthly(m) })));
  const valid = items.filter((x) => x.data);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">먼슬리 리포트</h1>
      <div className="space-y-2">
        {valid.map(({ month, data }) => {
          const label = `${month.slice(0, 4)}년 ${parseInt(month.slice(4), 10)}월`;
          return (
            <Link
              key={month}
              href={`/monthly/${month}`}
              className="card hover:border-brand-primary transition-colors flex items-center justify-between"
            >
              <div>
                <div className="font-medium">{label}</div>
                <div className="text-xs text-slate-400">{data!.period?.start ?? ''} ~ {data!.period?.end ?? ''}</div>
              </div>
              <div className="text-sm text-slate-300 flex gap-4">
                <span>비용 {fmtMan(data!.kpi.cost)}</span>
                <span>전환 {data!.kpi.conv}건</span>
                <span>CPA {fmtMan(data!.kpi.cpa)}</span>
                <span>CVR {fmtPct(data!.kpi.cvr)}</span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
