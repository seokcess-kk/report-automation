import { loadLatestTracker } from '@/lib/reports';
import { fmtMan } from '@/lib/format';
import { Badge, Card, StatusDot } from '@/components/ui';
import { cn } from '@/components/ui/cn';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

const PRIORITY_META: Record<string, { label: string; tone: 'danger' | 'warn' | 'neutral' }> = {
  high: { label: '긴급', tone: 'danger' },
  medium: { label: '권장', tone: 'warn' },
  low: { label: '참고', tone: 'neutral' },
};

export default async function MobilePage() {
  const tracker = await loadLatestTracker();

  if (!tracker) {
    return <Card><p className="text-muted text-sm">데이터가 아직 생성되지 않았습니다.</p></Card>;
  }

  const { pace, proposals } = tracker;
  const { overall, date_progress } = pace;
  const top3 = proposals.proposals.slice(0, 3);

  return (
    <div className="space-y-3 animate-fade-in">
      <Card variant="default" className="p-4">
        <div className="flex items-baseline justify-between mb-3">
          <h1 className="text-base font-semibold text-fg tracking-tight">{pace.month} 현황</h1>
          <span className="text-2xs text-subtle tabular-nums">
            {pace.days_elapsed}/{pace.days_total}일 · {date_progress}%
          </span>
        </div>

        <div className="space-y-3">
          <MiniBar
            label="예산 소진"
            pct={overall.budget_pct}
            target={date_progress}
            sub={`${fmtMan(overall.cost_so_far)} / ${fmtMan(overall.budget_total)}원`}
            invert
          />
          <MiniBar
            label="전환 달성"
            pct={overall.conv_pct}
            target={date_progress}
            sub={`${overall.conv_so_far} / ${overall.conv_target}건`}
          />
          <MiniBar
            label="월말 예상"
            pct={overall.proj_pct}
            target={100}
            sub={`${overall.proj_conv}건 (${overall.proj_pct}%)`}
          />
        </div>
      </Card>

      <Card variant="default" className="p-4">
        <h2 className="text-sm font-semibold text-fg mb-3">지점 상태</h2>
        <ul className="space-y-2">
          {pace.branches.map((b) => (
            <li key={b.branch} className="flex items-center gap-2.5 text-sm">
              <StatusDot status={b.status as any} size="md" />
              <span className="font-semibold text-fg w-10 shrink-0">{b.branch}</span>
              <span className="text-2xs text-muted flex-1 tabular-nums">
                예산 {b.budget_pct}% · 전환 {b.conv_pct}%
              </span>
              <span className="text-2xs text-subtle shrink-0 tabular-nums">
                {b.cpa != null ? `${(b.cpa / 1000).toFixed(0)}k` : '-'}
              </span>
            </li>
          ))}
        </ul>
      </Card>

      <Card variant="default" className="p-4">
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-sm font-semibold text-fg">오늘의 액션 Top 3</h2>
          <span className="text-2xs text-subtle">전체 {proposals.summary.total}건</span>
        </div>
        {top3.length === 0 ? (
          <p className="text-2xs text-muted">제안 없음</p>
        ) : (
          <ul className="space-y-3">
            {top3.map((p) => {
              const meta = PRIORITY_META[p.priority];
              return (
                <li key={p.id} className="text-xs">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Badge tone={meta.tone}>{meta.label}</Badge>
                    <span className="text-sm font-semibold text-fg leading-snug">{p.title}</span>
                  </div>
                  <p className="text-muted text-xs leading-relaxed line-clamp-2">{p.reason}</p>
                </li>
              );
            })}
          </ul>
        )}
        <Link
          href="/tracker"
          className="block mt-4 text-center text-xs text-accent hover:text-accent-strong font-medium"
        >
          전체 보기 →
        </Link>
      </Card>
    </div>
  );
}

function MiniBar({
  label, pct, target, sub, invert,
}: {
  label: string; pct: number; target: number; sub: string; invert?: boolean;
}) {
  const gap = pct - target;
  const good = invert ? gap <= 5 : gap >= -5;
  const mid = invert ? gap <= 15 : gap >= -15;
  const barColor = good ? 'bg-success' : mid ? 'bg-warn' : 'bg-danger';

  return (
    <div>
      <div className="flex items-baseline justify-between text-xs mb-1">
        <span className="text-muted">{label}</span>
        <span className="font-semibold text-fg tabular-nums">{pct.toFixed(1)}%</span>
      </div>
      <div className="h-1 bg-elevated rounded-full overflow-hidden relative">
        <div
          className={cn('absolute inset-y-0 left-0 rounded-full', barColor)}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
        <div
          className="absolute top-0 h-full w-px bg-fg/40"
          style={{ left: `${Math.min(target, 100)}%` }}
        />
      </div>
      <div className="text-2xs text-subtle mt-1 tabular-nums">{sub}</div>
    </div>
  );
}
