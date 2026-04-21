import { listWeeklyDates, loadWeekly } from '@/lib/reports';
import Link from 'next/link';
import { fmtMan, fmtPct } from '@/lib/format';

export const dynamic = 'force-dynamic';

export default async function WeeklyListPage() {
  const dates = await listWeeklyDates();
  const items = await Promise.all(
    dates.slice(0, 20).map(async (d) => {
      const data = await loadWeekly(d);
      return { date: d, data };
    })
  );
  const valid = items.filter((x) => x.data);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">위클리 리포트 목록</h1>
      <div className="space-y-2">
        {valid.map(({ date, data }) => (
          <Link
            key={date}
            href={`/weekly/${date}`}
            className="card hover:border-brand-primary transition-colors flex items-center justify-between"
          >
            <div>
              <div className="font-medium">{data!.period_this_full}</div>
              <div className="text-xs text-slate-400">발행: {data!.issue_date}</div>
            </div>
            <div className="text-sm text-slate-300 flex gap-4">
              <span>비용 {fmtMan(data!.kpi_this.cost)}</span>
              <span>전환 {data!.kpi_this.conv}건</span>
              <span>CVR {fmtPct(data!.kpi_this.cvr)}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
