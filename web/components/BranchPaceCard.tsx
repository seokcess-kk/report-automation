'use client';
import { BranchPace } from '@/lib/reports';
import { fmtMan } from '@/lib/format';
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts';

const STATUS_META: Record<string, { dot: string; ring: string; label: string }> = {
  ok: { dot: 'bg-brand-success', ring: 'ring-emerald-500/30', label: '정상' },
  warn: { dot: 'bg-brand-warn', ring: 'ring-amber-500/30', label: '주의' },
  danger: { dot: 'bg-brand-danger', ring: 'ring-rose-500/30', label: '경고' },
};

export function BranchPaceCard({
  b,
  dateProgress,
  selected,
  onClick,
}: {
  b: BranchPace;
  dateProgress: number;
  selected: boolean;
  onClick: () => void;
}) {
  const meta = STATUS_META[b.status];
  const convGap = b.conv_pct - dateProgress;
  const budgetGap = b.budget_pct - dateProgress;

  return (
    <button
      type="button"
      onClick={onClick}
      className={`card text-left w-full transition-all ring-2 ${selected ? 'ring-brand-primary' : meta.ring} hover:ring-brand-primary`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${meta.dot}`} />
          <span className="font-bold text-lg">{b.branch}</span>
          <span className="text-xs text-slate-500">{meta.label}</span>
        </div>
        <span className="text-xs text-slate-500">{b.sparkline.length}일</span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm mb-3">
        <MiniStat
          label="예산"
          value={`${b.budget_pct}%`}
          sub={fmtMan(b.cost_so_far) + ' / ' + fmtMan(b.budget)}
          gap={budgetGap}
          invert
        />
        <MiniStat
          label="전환"
          value={`${b.conv_pct}%`}
          sub={`${b.conv_so_far} / ${b.conv_target}건`}
          gap={convGap}
        />
      </div>

      <div className="text-xs text-slate-400 mb-2">
        CPA {b.cpa != null ? `${b.cpa.toLocaleString()}원` : '-'}
        {b.cpa_vs_target_pct != null && (
          <span className={`ml-1 ${b.cpa_vs_target_pct > 120 ? 'text-brand-danger' : b.cpa_vs_target_pct > 100 ? 'text-brand-warn' : 'text-brand-success'}`}>
            (목표 대비 {b.cpa_vs_target_pct}%)
          </span>
        )}
        {' · '}월말 예상 {b.proj_conv}건
      </div>

      <div className="h-10">
        {b.sparkline.length > 1 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={b.sparkline}>
              <Line type="monotone" dataKey="conv" stroke="#60a5fa" strokeWidth={1.5} dot={false} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', fontSize: 11 }}
                labelStyle={{ color: '#cbd5e1' }}
                formatter={(v: number, k: string) => [k === 'conv' ? `${v}건` : v.toLocaleString(), k === 'conv' ? '전환' : k]}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-xs text-slate-500 italic">데이터 부족</div>
        )}
      </div>
    </button>
  );
}

function MiniStat({
  label,
  value,
  sub,
  gap,
  invert = false,
}: {
  label: string;
  value: string;
  sub: string;
  gap: number;
  invert?: boolean;
}) {
  const good = invert ? gap <= 5 : gap >= -5;
  const mid = invert ? gap <= 15 : gap >= -15;
  const cls = good ? 'text-brand-success' : mid ? 'text-brand-warn' : 'text-brand-danger';
  const sign = gap > 0 ? '+' : '';

  return (
    <div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="flex items-baseline gap-1">
        <span className="text-base font-bold">{value}</span>
        <span className={`text-[10px] ${cls}`}>{sign}{gap.toFixed(1)}%p</span>
      </div>
      <div className="text-[10px] text-slate-500 mt-0.5">{sub}</div>
    </div>
  );
}
