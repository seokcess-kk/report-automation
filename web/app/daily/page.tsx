import { listDailyDates, loadDaily } from '@/lib/reports';
import Link from 'next/link';
import { fmtMan, fmtPct } from '@/lib/format';

export const dynamic = 'force-dynamic';

export default async function DailyListPage() {
  const dates = await listDailyDates();
  const items = await Promise.all(dates.slice(0, 30).map(async (d) => ({ date: d, data: await loadDaily(d) })));
  const valid = items.filter((x) => x.data);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">데일리 리포트 목록</h1>
      <div className="space-y-2">
        {valid.map(({ date, data }) => (
          <Link
            key={date}
            href={`/daily/${date}`}
            className="card hover:border-brand-primary transition-colors flex items-center justify-between"
          >
            <div>
              <div className="font-medium">{data!.date_label} ({data!.date})</div>
              <div className="text-xs text-slate-400">
                잔여 {data!.goal.remaining_days}일 · 전환 {data!.goal.conv_current}/{data!.goal.conv_target} ({data!.goal.conv_pct}%)
              </div>
            </div>
            <div className="text-sm text-slate-300 flex gap-4">
              <span>어제 비용 {fmtMan(data!.kpi_daily.cost)}</span>
              <span>전환 {data!.kpi_daily.conv}건</span>
              <span>CPA {fmtMan(data!.kpi_daily.cpa)}</span>
              <span>CVR {fmtPct(data!.kpi_daily.cvr)}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
