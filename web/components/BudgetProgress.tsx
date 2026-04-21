import { fmtMan } from '@/lib/format';

interface BranchKpi { branch: string; 총비용: number; 총전환: number; CPA: number }

export function BudgetProgress({
  branches,
  budget,
}: {
  branches: BranchKpi[];
  budget: Record<string, number>;
}) {
  const rows = branches
    .map((b) => {
      const bud = budget[b.branch] ?? 0;
      const ratio = bud > 0 ? (b.총비용 / bud) * 100 : 0;
      return { ...b, budget: bud, ratio };
    })
    .sort((a, b) => b.ratio - a.ratio);

  const barColor = (r: number) => {
    if (r >= 100) return 'bg-brand-danger';
    if (r >= 85) return 'bg-brand-warn';
    return 'bg-brand-primary';
  };

  return (
    <div className="card">
      <h2 className="font-semibold mb-3">지점별 예산 소진율</h2>
      <div className="space-y-3">
        {rows.map((r) => (
          <div key={r.branch}>
            <div className="flex items-baseline justify-between text-sm mb-1">
              <span className="font-medium">{r.branch}</span>
              <span className="text-slate-400 text-xs">
                {fmtMan(r.총비용)} / {fmtMan(r.budget)} ({r.ratio.toFixed(1)}%) · 전환 {r.총전환}건
              </span>
            </div>
            <div className="h-2 bg-brand-bg rounded overflow-hidden">
              <div
                className={`h-full ${barColor(r.ratio)}`}
                style={{ width: `${Math.min(r.ratio, 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
