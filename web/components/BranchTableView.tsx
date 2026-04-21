'use client';
import { useState } from 'react';
import { BranchPace } from '@/lib/reports';
import { fmtMan } from '@/lib/format';
import { StatusDot } from './ui';
import { cn } from './ui/cn';

type SortKey = 'branch' | 'budget_pct' | 'conv_pct' | 'cpa' | 'proj_pct' | 'status';
type SortDir = 'asc' | 'desc';

const STATUS_ORDER: Record<string, number> = { danger: 0, warn: 1, ok: 2 };

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
    if (sort.key === 'status') { av = STATUS_ORDER[a.status]; bv = STATUS_ORDER[b.status]; }
    else if (sort.key === 'branch') { av = a.branch; bv = b.branch; }
    else { av = a[sort.key] ?? -1; bv = b[sort.key] ?? -1; }
    if (av === bv) return 0;
    const cmp = av > bv ? 1 : -1;
    return sort.dir === 'asc' ? cmp : -cmp;
  });

  function toggleSort(key: SortKey) {
    setSort((prev) => prev.key === key ? { key, dir: prev.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' });
  }

  function arrow(key: SortKey) {
    if (sort.key !== key) return <span className="text-subtle/50">↕</span>;
    return <span className="text-accent">{sort.dir === 'asc' ? '↑' : '↓'}</span>;
  }

  return (
    <div className="bg-surface border border-border rounded-xl overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-2xs text-subtle uppercase tracking-wider border-b border-border">
          <tr>
            <Th onClick={() => toggleSort('status')}>상태 {arrow('status')}</Th>
            <Th onClick={() => toggleSort('branch')}>지점 {arrow('branch')}</Th>
            <Th onClick={() => toggleSort('budget_pct')} align="right">예산% {arrow('budget_pct')}</Th>
            <Th onClick={() => toggleSort('conv_pct')} align="right">전환% {arrow('conv_pct')}</Th>
            <Th onClick={() => toggleSort('cpa')} align="right" hideOnMobile>CPA {arrow('cpa')}</Th>
            <Th onClick={() => toggleSort('proj_pct')} align="right" hideOnMobile>월말예상 {arrow('proj_pct')}</Th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((b) => {
            const active = selected === b.branch;
            const convGap = b.conv_pct - dateProgress;
            const cpaTone = b.cpa_vs_target_pct == null ? ''
              : b.cpa_vs_target_pct > 120 ? 'text-danger'
              : b.cpa_vs_target_pct > 100 ? 'text-warn'
              : 'text-success';
            const convTone = convGap < -15 ? 'text-danger' : convGap < -5 ? 'text-warn' : 'text-success';

            return (
              <tr
                key={b.branch}
                onClick={() => onSelect(b.branch)}
                className={cn(
                  'cursor-pointer border-b border-border/50 transition-colors',
                  active ? 'bg-elevated' : 'hover:bg-elevated/50'
                )}
              >
                <td className="py-2.5 px-4"><StatusDot status={b.status as any} size="md" /></td>
                <td className="py-2.5 px-4 font-semibold text-fg">{b.branch}</td>
                <td className="py-2.5 px-4 text-right tabular-nums">
                  <div className="text-fg">{b.budget_pct}%</div>
                  <div className="text-2xs text-subtle">{fmtMan(b.cost_so_far)} / {fmtMan(b.budget)}</div>
                </td>
                <td className="py-2.5 px-4 text-right tabular-nums">
                  <div className={convTone}>{b.conv_pct}%</div>
                  <div className="text-2xs text-subtle">{b.conv_so_far} / {b.conv_target}건</div>
                </td>
                <td className="py-2.5 px-4 text-right tabular-nums hidden sm:table-cell">
                  <div className={cpaTone || 'text-fg'}>{b.cpa != null ? b.cpa.toLocaleString() : '-'}</div>
                  {b.cpa_vs_target_pct != null && <div className="text-2xs text-subtle">목표 {b.cpa_vs_target_pct}%</div>}
                </td>
                <td className="py-2.5 px-4 text-right tabular-nums hidden sm:table-cell">
                  <div className="text-fg">{b.proj_conv}건</div>
                  <div className="text-2xs text-subtle">{b.proj_pct}%</div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Th({
  children, onClick, align, hideOnMobile,
}: { children: React.ReactNode; onClick: () => void; align?: 'right'; hideOnMobile?: boolean }) {
  return (
    <th
      onClick={onClick}
      className={cn(
        'py-2.5 px-4 cursor-pointer select-none hover:text-fg font-medium',
        align === 'right' ? 'text-right' : 'text-left',
        hideOnMobile && 'hidden sm:table-cell'
      )}
    >
      {children}
    </th>
  );
}
