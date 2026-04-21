import { loadLatestWeekly } from '@/lib/reports';
import { fmt, fmtMan, fmtPct, fmtDiff, diffColor } from '@/lib/format';
import { Card, Stat } from '@/components/ui';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  const latest = await loadLatestWeekly();

  if (!latest) {
    return (
      <div className="bg-surface border border-border rounded-xl p-8 text-center">
        <p className="text-muted text-sm">아직 생성된 리포트가 없습니다.</p>
      </div>
    );
  }

  const { date, data } = latest;
  const k = data.kpi_this;
  const p = data.kpi_prev;

  return (
    <div className="space-y-8 animate-fade-in">
      <section>
        <div className="flex items-baseline justify-between flex-wrap gap-2">
          <h1 className="text-2xl font-bold text-fg tracking-tight">최신 위클리 요약</h1>
          <span className="text-xs text-subtle tabular-nums">{data.period_this_full}</span>
        </div>
      </section>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card variant="default">
          <Stat
            label="광고비"
            value={fmtMan(k.cost)}
            delta={fmtDiff(k.cost - p.cost)}
            deltaTone={k.cost - p.cost < 0 ? 'positive' : k.cost - p.cost > 0 ? 'negative' : 'neutral'}
          />
        </Card>
        <Card variant="default">
          <Stat
            label="전환수"
            value={fmt(k.conv, '건')}
            delta={fmtDiff(k.conv - p.conv, '건')}
            deltaTone={k.conv - p.conv > 0 ? 'positive' : k.conv - p.conv < 0 ? 'negative' : 'neutral'}
          />
        </Card>
        <Card variant="default">
          <Stat
            label="CPA"
            value={fmt(k.cpa, '원')}
            delta={fmtDiff(k.cpa - p.cpa)}
            deltaTone={k.cpa - p.cpa < 0 ? 'positive' : k.cpa - p.cpa > 0 ? 'negative' : 'neutral'}
          />
        </Card>
        <Card variant="default">
          <Stat
            label="CVR"
            value={fmtPct(k.cvr)}
            delta={fmtDiff((k.cvr - p.cvr) * 100, 'p').replace('원', '')}
            deltaTone={k.cvr - p.cvr > 0 ? 'positive' : k.cvr - p.cvr < 0 ? 'negative' : 'neutral'}
          />
        </Card>
      </section>

      <Card variant="default" className="p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-fg">월 전환 목표</h2>
          <span className="text-2xs text-subtle uppercase tracking-wider">월말 예상 {data.proj_pct}%</span>
        </div>
        <div className="h-2 bg-elevated rounded-full overflow-hidden mb-2">
          <div
            className="h-full bg-accent transition-all duration-300 ease-swift"
            style={{ width: `${Math.min(data.conv_pct, 100)}%` }}
          />
        </div>
        <p className="text-sm text-muted tabular-nums">
          <span className="text-fg font-semibold">{data.conv_so_far.toLocaleString()}</span>
          {' '}/ {data.monthly_target_conv.toLocaleString()}건{' '}
          <span className="text-subtle">({data.conv_pct}%)</span>
        </p>
      </Card>

      <Card variant="default" className="p-5">
        <h2 className="text-base font-semibold text-fg mb-4">인사이트</h2>
        <ul className="space-y-4">
          {data.insights.map((ins: any, i: number) => (
            <li key={i} className="border-l-2 pl-3" style={{ borderColor: ins.color }}>
              <div className="text-sm font-medium mb-1" style={{ color: ins.color }}>
                [{ins.type}] {ins.title}
              </div>
              <ul className="ml-4 text-sm text-muted list-disc space-y-0.5">
                {ins.points.map((p: string, j: number) => (
                  <li key={j} className="leading-relaxed">{p}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </Card>

      <div className="text-right">
        <Link
          href={`/weekly/${date}`}
          className="inline-flex items-center gap-1 text-sm text-accent hover:text-accent-strong font-medium"
        >
          상세 보기 <span>→</span>
        </Link>
      </div>
    </div>
  );
}
