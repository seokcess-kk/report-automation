import { loadLatestTracker } from '@/lib/reports';
import { fmtMan } from '@/lib/format';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

const STATUS_DOT: Record<string, string> = {
  ok: 'bg-brand-success',
  warn: 'bg-brand-warn',
  danger: 'bg-brand-danger',
};

const PRIORITY_META: Record<string, { label: string; cls: string }> = {
  high: { label: '긴급', cls: 'bg-rose-900/50 text-brand-danger' },
  medium: { label: '권장', cls: 'bg-amber-900/50 text-brand-warn' },
  low: { label: '참고', cls: 'bg-slate-700 text-slate-400' },
};

export default async function MobilePage() {
  const tracker = await loadLatestTracker();

  if (!tracker) {
    return (
      <div className="card">
        <p className="text-slate-400 text-sm">데이터가 아직 생성되지 않았습니다.</p>
      </div>
    );
  }

  const { pace, proposals } = tracker;
  const { overall, date_progress } = pace;
  const top3 = proposals.proposals.slice(0, 3);

  return (
    <div className="space-y-4">
      <section className="card">
        <div className="flex items-baseline justify-between mb-2">
          <h1 className="text-lg font-bold">{pace.month} 현황</h1>
          <span className="text-xs text-slate-400">
            {pace.days_elapsed}/{pace.days_total}일 · {date_progress}%
          </span>
        </div>

        <div className="space-y-2">
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
      </section>

      <section className="card">
        <h2 className="text-sm font-semibold mb-3">지점 상태</h2>
        <ul className="space-y-1.5">
          {pace.branches.map((b) => (
            <li key={b.branch} className="flex items-center gap-2 text-sm">
              <span className={`w-2 h-2 rounded-full shrink-0 ${STATUS_DOT[b.status]}`} />
              <span className="font-medium w-8 shrink-0">{b.branch}</span>
              <span className="text-xs text-slate-400 flex-1">
                예산 {b.budget_pct}% · 전환 {b.conv_pct}%
              </span>
              <span className="text-xs text-slate-500 shrink-0">
                {b.cpa != null ? `${(b.cpa / 1000).toFixed(0)}k` : '-'}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-sm font-semibold">오늘의 액션 Top 3</h2>
          <span className="text-xs text-slate-500">전체 {proposals.summary.total}건</span>
        </div>
        {top3.length === 0 ? (
          <p className="text-xs text-slate-500">제안 없음</p>
        ) : (
          <ul className="space-y-2">
            {top3.map((p) => {
              const meta = PRIORITY_META[p.priority];
              return (
                <li key={p.id} className="text-xs">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${meta.cls}`}>
                      {meta.label}
                    </span>
                    <span className="font-semibold">{p.title}</span>
                  </div>
                  <p className="text-slate-400 text-[11px] leading-snug line-clamp-2">{p.reason}</p>
                </li>
              );
            })}
          </ul>
        )}
        <Link
          href="/tracker"
          className="block mt-3 text-center text-xs text-brand-primary hover:underline"
        >
          전체 보기 →
        </Link>
      </section>
    </div>
  );
}

function MiniBar({
  label,
  pct,
  target,
  sub,
  invert,
}: {
  label: string;
  pct: number;
  target: number;
  sub: string;
  invert?: boolean;
}) {
  const gap = pct - target;
  const good = invert ? gap <= 5 : gap >= -5;
  const mid = invert ? gap <= 15 : gap >= -15;
  const barColor = good ? 'bg-brand-success' : mid ? 'bg-brand-warn' : 'bg-brand-danger';

  return (
    <div>
      <div className="flex items-baseline justify-between text-xs">
        <span className="text-slate-300">{label}</span>
        <span className="font-bold text-slate-100">{pct.toFixed(1)}%</span>
      </div>
      <div className="h-1.5 bg-brand-bg rounded overflow-hidden relative my-0.5">
        <div className={`h-full ${barColor}`} style={{ width: `${Math.min(pct, 100)}%` }} />
        <div
          className="absolute top-0 h-full w-0.5 bg-slate-400"
          style={{ left: `${Math.min(target, 100)}%` }}
        />
      </div>
      <div className="text-[10px] text-slate-500">{sub}</div>
    </div>
  );
}
