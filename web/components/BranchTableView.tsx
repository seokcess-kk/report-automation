'use client';
import { useState } from 'react';
import { BranchPace } from '@/lib/reports';
import { fmtMan } from '@/lib/format';

type SortKey = 'branch' | 'budget_pct' | 'conv_pct' | 'cpa' | 'proj_pct' | 'status';
type SortDir = 'asc' | 'desc';

const STATUS_ORDER: Record<string, number> = { danger: 0, warn: 1, ok: 2 };
const STATUS_META: Record<string, { dot: string; label: string }> = {
  ok: { dot: 'bg-brand-success', label: '정상' },
  warn: { dot: 'bg-brand-warn', label: '주의' },
  danger: { dot: 'bg-brand-danger', label: '경고' },
};

export function BranchTableView({
  branches,
  dateProgress,
  onSelect,
  selected,
}: {
  branches: BranchPace[];
  dateProgress: number;
  onSelect: (branch: string) => void;
  selected: string | null;
}) {
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({ key: 'status', dir: 'asc' });

  const sorted = [...branches].sort((a, b) => {
    let av: any, bv: any;
    if (sort.key === 'status') {
      av = STATUS_ORDER[a.status];
      bv = STATUS_ORDER[b.status];
    } else if (sort.key === 'branch') {
      av = a.branch;
      bv = b.branch;
    } else {
      av = a[sort.key] ?? -1;
      bv = b[sort.key] ?? -1;
    }
    if (av === bv) return 0;
    const cmp = av > bv ? 1 : -1;
    return sort.dir === 'asc' ? cmp : -cmp;
  });

  function toggleSort(key: SortKey) {
    setSort((prev) =>
      prev.key === key
        ? { key, dir: prev.dir === 'asc' ? 'desc' : 'asc' }
        : { key, dir: 'asc' }
    );
  }

  function arrow(key: SortKey) {
    if (sort.key !== key) return <span className="text-slate-600">↕</span>;
    return <span className="text-brand-primary">{sort.dir === 'asc' ? '↑' : '↓'}</span>;
  }

  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-xs text-slate-400 border-b border-brand-border">
          <tr>
            <Th onClick={() => toggleSort('status')}>상태 {arrow('status')}</Th>
            <Th onClick={() => toggleSort('branch')}>지점 {arrow('branch')}</Th>
            <Th onClick={() => toggleSort('budget_pct')} align="right">예산% {arrow('budget_pct')}</Th>
            <Th onClick={() => toggleSort('conv_pct')} align="right">전환% {arrow('conv_pct')}</Th>
            <Th onClick={() => toggleSort('cpa')} align="right">CPA {arrow('cpa')}</Th>
            <Th onClick={() => toggleSort('proj_pct')} align="right">월말예상 {arrow('proj_pct')}</Th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((b) => {
            const meta = STATUS_META[b.status];
            const active = selected === b.branch;
            const convGap = b.conv_pct - dateProgress;
            const cpaColor =
              b.cpa_vs_target_pct == null
                ? ''
                : b.cpa_vs_target_pct > 120
                ? 'text-brand-danger'
                : b.cpa_vs_target_pct > 100
                ? 'text-brand-warn'
                : 'text-brand-success';

            return (
              <tr
                key={b.branch}
                onClick={() => onSelect(b.branch)}
                className={`cursor-pointer border-b border-brand-border/50 hover:bg-brand-bg/60 ${
                  active ? 'bg-brand-bg/80' : ''
                }`}
              >
                <td className="py-2 px-3">
                  <span className={`inline-block w-2 h-2 rounded-full ${meta.dot}`} title={meta.label} />
                </td>
                <td className="py-2 px-3 font-medium">{b.branch}</td>
                <td className="py-2 px-3 text-right font-mono">
                  {b.budget_pct}%
                  <div className="text-[10px] text-slate-500">{fmtMan(b.cost_so_far)} / {fmtMan(b.budget)}</div>
                </td>
                <td className="py-2 px-3 text-right font-mono">
                  <span className={convGap < -15 ? 'text-brand-danger' : convGap < -5 ? 'text-brand-warn' : 'text-brand-success'}>
                    {b.conv_pct}%
                  </span>
                  <div className="text-[10px] text-slate-500">{b.conv_so_far} / {b.conv_target}건</div>
                </td>
                <td className="py-2 px-3 text-right font-mono">
                  <span className={cpaColor}>
                    {b.cpa != null ? b.cpa.toLocaleString() : '-'}
                  </span>
                  {b.cpa_vs_target_pct != null && (
                    <div className="text-[10px] text-slate-500">목표 {b.cpa_vs_target_pct}%</div>
                  )}
                </td>
                <td className="py-2 px-3 text-right font-mono">
                  {b.proj_conv}건
                  <div className="text-[10px] text-slate-500">{b.proj_pct}%</div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Th({ children, onClick, align }: { children: React.ReactNode; onClick: () => void; align?: 'right' }) {
  return (
    <th
      onClick={onClick}
      className={`py-2 px-3 cursor-pointer select-none hover:text-white ${align === 'right' ? 'text-right' : 'text-left'}`}
    >
      {children}
    </th>
  );
}
