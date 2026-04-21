'use client';
import { BranchPace } from '@/lib/reports';
import { fmtMan } from '@/lib/format';
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts';
import { StatusDot } from './ui';
import { cn } from './ui/cn';

export function BranchPaceCard({
  b, dateProgress, selected, onClick,
}: {
  b: BranchPace;
  dateProgress: number;
  selected: boolean;
  onClick: () => void;
}) {
  const convGap = b.conv_pct - dateProgress;
  const budgetGap = b.budget_pct - dateProgress;
  const cpaTone =
    b.cpa_vs_target_pct == null ? 'text-muted'
      : b.cpa_vs_target_pct > 120 ? 'text-danger'
      : b.cpa_vs_target_pct > 100 ? 'text-warn'
      : 'text-success';

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'group text-left w-full rounded-xl transition-all duration-150 ease-swift',
        'bg-surface border p-4',
        'hover:border-border-strong hover:shadow-card',
        selected ? 'border-accent shadow-card' : 'border-border'
      )}
    >
      <div className="flex items-center gap-2 mb-3">
        <StatusDot status={b.status as any} size="md" />
        <span className="text-base font-semibold text-fg">{b.branch}</span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <MiniStat label="예산" value={`${b.budget_pct}%`} sub={`${fmtMan(b.cost_so_far)} / ${fmtMan(b.budget)}`} gap={budgetGap} invert />
        <MiniStat label="전환" value={`${b.conv_pct}%`} sub={`${b.conv_so_far} / ${b.conv_target}건`} gap={convGap} />
      </div>

      <div className="flex items-baseline justify-between text-2xs mb-2">
        <span className="text-subtle">CPA</span>
        <span className="tabular-nums">
          <span className="text-fg font-medium">{b.cpa != null ? b.cpa.toLocaleString() + '원' : '-'}</span>
          {b.cpa_vs_target_pct != null && (
            <span className={cn('ml-1.5', cpaTone)}>·{b.cpa_vs_target_pct}%</span>
          )}
        </span>
      </div>

      <div className="flex items-baseline justify-between text-2xs mb-2">
        <span className="text-subtle">월말 예상</span>
        <span className="tabular-nums text-fg">{b.proj_conv}건</span>
      </div>

      <div className="h-10 -mx-1 mt-2">
        {b.sparkline.length > 1 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={b.sparkline}>
              <Line type="monotone" dataKey="conv" stroke="rgb(129 140 248)" strokeWidth={1.5} dot={false} />
              <Tooltip
                contentStyle={{ background: 'rgb(24 24 27)', border: '1px solid rgb(39 39 42)', fontSize: 11, borderRadius: 6 }}
                labelStyle={{ color: 'rgb(161 161 170)' }}
                formatter={(v: number, k: string) => [k === 'conv' ? `${v}건` : v.toLocaleString(), k === 'conv' ? '전환' : k]}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-2xs text-subtle italic">데이터 부족</div>
        )}
      </div>
    </button>
  );
}

function MiniStat({
  label, value, sub, gap, invert = false,
}: {
  label: string; value: string; sub: string; gap: number; invert?: boolean;
}) {
  const good = invert ? gap <= 5 : gap >= -5;
  const mid = invert ? gap <= 15 : gap >= -15;
  const tone = good ? 'text-success' : mid ? 'text-warn' : 'text-danger';
  const sign = gap > 0 ? '+' : '';

  return (
    <div>
      <div className="text-2xs text-subtle uppercase tracking-wide">{label}</div>
      <div className="flex items-baseline gap-1.5 mt-0.5">
        <span className="text-base font-semibold text-fg tabular-nums">{value}</span>
        <span className={cn('text-2xs tabular-nums', tone)}>{sign}{gap.toFixed(1)}%p</span>
      </div>
      <div className="text-2xs text-subtle mt-0.5 tabular-nums">{sub}</div>
    </div>
  );
}
