import { loadMonthly } from '@/lib/reports';
import { notFound } from 'next/navigation';
import { fmt, fmtMan, fmtPct } from '@/lib/format';
import { MonthlyDailyChart } from '@/components/MonthlyDailyChart';
import { BudgetProgress } from '@/components/BudgetProgress';
import { CreativeLeaderboard } from '@/components/CreativeLeaderboard';

export const dynamic = 'force-dynamic';

export default async function MonthlyDetailPage({ params }: { params: { month: string } }) {
  const data = await loadMonthly(params.month);
  if (!data) notFound();

  const k = data.kpi;
  const label = `${params.month.slice(0, 4)}년 ${parseInt(params.month.slice(4), 10)}월`;
  const totalBudget = Object.values(data.budget).reduce((a, b) => a + b, 0);
  const budgetPct = totalBudget > 0 ? (k.cost / totalBudget) * 100 : 0;
  const convPct = data.monthly_target_conv > 0 ? (k.conv / data.monthly_target_conv) * 100 : 0;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold">먼슬리 리포트 · {label}</h1>
        <p className="text-sm text-slate-400">
          목표 CPA {fmt(data.target_cpa, '원')} · 목표 전환 {data.monthly_target_conv.toLocaleString()}건
        </p>
      </header>

      {/* 전체 KPI */}
      <section className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Kpi label="총 광고비" value={fmtMan(k.cost)} sub={`예산 ${budgetPct.toFixed(1)}%`} />
        <Kpi label="총 전환" value={`${k.conv.toLocaleString()}건`} sub={`목표 ${convPct.toFixed(1)}%`} />
        <Kpi label="CPA" value={fmt(k.cpa, '원')} sub={k.cpa <= data.target_cpa ? '✓ 목표 내' : '⚠ 목표 초과'} />
        <Kpi label="CTR" value={fmtPct(k.ctr)} />
        <Kpi label="CVR" value={fmtPct(k.cvr)} />
      </section>

      {/* 일별 추이 */}
      <MonthlyDailyChart data={data.daily} />

      {/* 지점별 예산 소진 */}
      <BudgetProgress branches={data.branch as any} budget={data.budget} />

      {/* 소재 리더보드 */}
      <CreativeLeaderboard items={data.creative as any} />

      {/* 확장 기회 + OFF 누적 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.expansion?.length > 0 && (
          <div className="card">
            <h2 className="font-semibold mb-3">TIER1 확장 기회</h2>
            <ul className="space-y-2 text-sm">
              {data.expansion.slice(0, 5).map((e: any, i: number) => (
                <li key={i} className="border-l-2 border-brand-primary pl-3">
                  <div className="font-medium">{e.creative_name}</div>
                  <div className="text-xs text-slate-400">
                    CPA {fmt(e.CPA, '원')} · 미집행 {(e.missing ?? []).join(', ')}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
        {data.off_cumul?.length > 0 && (
          <div className="card">
            <h2 className="font-semibold mb-3">OFF 누적 리포트</h2>
            <ul className="space-y-2 text-sm">
              {data.off_cumul.slice(0, 5).map((o: any, i: number) => (
                <li key={i} className="border-l-2 border-brand-danger pl-3">
                  <div className="font-medium">{o.creative_name}</div>
                  <div className="text-xs text-slate-400">
                    [{o.branch}] CPA {fmt(o.CPA, '원')} · 평균 대비 {o.ratio}배
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* 다음 달 예산 제안 */}
      {data.next_budget?.length > 0 && (
        <div className="card overflow-x-auto">
          <h2 className="font-semibold mb-3">다음 달 예산 조정 제안</h2>
          <table className="w-full text-sm">
            <thead className="border-b border-brand-border text-slate-400">
              <tr>
                <th className="px-3 py-2 text-left">지점</th>
                <th className="px-3 py-2 text-right">현 예산</th>
                <th className="px-3 py-2 text-right">효율점수</th>
                <th className="px-3 py-2 text-right">제안 예산</th>
                <th className="px-3 py-2 text-center">방향</th>
                <th className="px-3 py-2 text-left">근거</th>
              </tr>
            </thead>
            <tbody>
              {data.next_budget.map((n: any, i: number) => (
                <tr key={i} className="border-b border-brand-border/50">
                  <td className="px-3 py-2 font-medium">{n.branch}</td>
                  <td className="px-3 py-2 text-right">{fmtMan(n.cur_budget)}</td>
                  <td className="px-3 py-2 text-right">{typeof n.효율점수 === 'number' ? n.효율점수.toFixed(2) : '-'}</td>
                  <td className="px-3 py-2 text-right font-semibold">{fmtMan(n.suggested)}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`text-xs ${n.direction === '증액' ? 'text-brand-success' : n.direction === '감액' ? 'text-brand-danger' : 'text-slate-400'}`}>
                      {n.direction}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-400">{n.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Kpi({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="card">
      <div className="text-xs text-slate-400 mb-1">{label}</div>
      <div className="text-xl font-bold">{value}</div>
      {sub && <div className="text-xs text-slate-400 mt-1">{sub}</div>}
    </div>
  );
}
