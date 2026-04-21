import { loadWeekly, listWeeklyDates } from '@/lib/reports';
import { notFound } from 'next/navigation';
import { KpiGrid } from '@/components/KpiGrid';
import { BranchTable } from '@/components/BranchTable';
import { DailyTrendChart } from '@/components/DailyTrendChart';
import { TierDetail } from '@/components/TierDetail';
import { InsightsBlock } from '@/components/InsightsBlock';

export const dynamic = 'force-dynamic';

export async function generateStaticParams() {
  return (await listWeeklyDates()).map((date) => ({ date }));
}

export default async function WeeklyDetailPage({ params }: { params: { date: string } }) {
  const data = await loadWeekly(params.date);
  if (!data) notFound();

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold">위클리 리포트</h1>
        <p className="text-sm text-slate-400">{data.period_this_full} · 발행 {data.issue_date}</p>
      </header>

      <KpiGrid now={data.kpi_this} prev={data.kpi_prev} />

      <InsightsBlock items={data.insights} />

      <section className="card">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">월 전환 목표</h2>
          <span className="text-xs text-slate-400">연말 예상 {data.proj_pct}%</span>
        </div>
        <div className="h-2 bg-brand-bg rounded overflow-hidden mb-1">
          <div className="h-full bg-brand-primary" style={{ width: `${Math.min(data.conv_pct, 100)}%` }} />
        </div>
        <p className="text-sm text-slate-400">
          {data.conv_so_far.toLocaleString()} / {data.monthly_target_conv.toLocaleString()}건 ({data.conv_pct}%)
        </p>
      </section>

      <DailyTrendChart data={data.daily} />

      <BranchTable rows={data.branch} />

      <TierDetail items={data.tier_this} />
    </div>
  );
}
