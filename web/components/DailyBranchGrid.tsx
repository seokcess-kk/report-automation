import { fmt, fmtMan, fmtPct } from '@/lib/format';
import type { DailyBranch } from '@/lib/reports';

export function DailyBranchGrid({ branches }: { branches: DailyBranch[] }) {
  const best = branches.filter((b) => b.tag === 'best');
  const focus = branches.filter((b) => b.tag === 'focus');
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Section
        title="✅ Best (효율 우수)"
        color="text-brand-success"
        rows={best}
        accentClass="border-brand-success/40"
      />
      <Section
        title="⚠️ Focus (관측 필요)"
        color="text-brand-warn"
        rows={focus}
        accentClass="border-brand-warn/40"
      />
    </div>
  );
}

function Section({
  title,
  color,
  rows,
  accentClass,
}: {
  title: string;
  color: string;
  rows: DailyBranch[];
  accentClass: string;
}) {
  return (
    <div className="card">
      <h3 className={`font-semibold mb-3 ${color}`}>{title}</h3>
      {rows.length === 0 && <div className="text-sm text-slate-500">해당 없음</div>}
      <div className="space-y-2">
        {rows.map((b) => (
          <div key={b.branch} className={`flex items-center justify-between border-l-2 pl-3 py-1 ${accentClass}`}>
            <div>
              <div className="font-medium text-sm">{b.branch}</div>
              <div className="text-xs text-slate-400">
                어제 전환 {b.daily_conv}건 · 목표 {fmt(b.target, '원')}
                {b.tag === 'focus' && b.ratio ? ` (목표 ${b.ratio}배)` : ''}
              </div>
            </div>
            <div className="text-right text-sm">
              <div>{fmtMan(b.cum_cpa)}</div>
              <div className="text-xs text-slate-400">CVR {fmtPct(b.cum_cvr, 1)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
