'use client';
import { useState } from 'react';
import { fmt, fmtMan, fmtPct, fmtDiff, diffColor } from '@/lib/format';
import type { BranchRow } from '@/lib/reports';

type SortKey = 'branch' | '총비용' | '총전환' | 'CPA' | 'CTR' | 'CVR' | 'CPA_diff' | '효율점수';

export function BranchTable({ rows }: { rows: BranchRow[] }) {
  const [sort, setSort] = useState<SortKey>('총비용');
  const [desc, setDesc] = useState(true);

  const sorted = [...rows].sort((a, b) => {
    const av = a[sort] as number | string;
    const bv = b[sort] as number | string;
    if (typeof av === 'number' && typeof bv === 'number') return desc ? bv - av : av - bv;
    return desc ? String(bv).localeCompare(String(av)) : String(av).localeCompare(String(bv));
  });

  function header(label: string, key: SortKey, rightAlign = true) {
    const active = sort === key;
    return (
      <th
        onClick={() => {
          if (active) setDesc(!desc);
          else { setSort(key); setDesc(true); }
        }}
        className={`px-3 py-2 cursor-pointer select-none whitespace-nowrap ${rightAlign ? 'text-right' : 'text-left'} ${active ? 'text-brand-primary' : 'text-slate-400'}`}
      >
        {label} {active ? (desc ? '↓' : '↑') : ''}
      </th>
    );
  }

  return (
    <div className="card overflow-x-auto">
      <h2 className="font-semibold mb-3">지점별 성과</h2>
      <table className="w-full text-sm">
        <thead className="border-b border-brand-border">
          <tr>
            {header('지점', 'branch', false)}
            {header('비용', '총비용')}
            {header('전환', '총전환')}
            {header('CPA', 'CPA')}
            {header('CTR', 'CTR')}
            {header('CVR', 'CVR')}
            {header('CPA 전주 대비', 'CPA_diff')}
            {header('효율점수', '효율점수')}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={r.branch} className="border-b border-brand-border/50 hover:bg-brand-bg/30">
              <td className="px-3 py-2 font-medium">{r.branch}</td>
              <td className="px-3 py-2 text-right">{fmtMan(r.총비용)}</td>
              <td className="px-3 py-2 text-right">{fmt(r.총전환, '건')}</td>
              <td className="px-3 py-2 text-right">{fmt(r.CPA, '원')}</td>
              <td className="px-3 py-2 text-right">{fmtPct(r.CTR)}</td>
              <td className="px-3 py-2 text-right">{fmtPct(r.CVR)}</td>
              <td className={`px-3 py-2 text-right ${diffColor(r.CPA_diff, true)}`}>{fmtDiff(r.CPA_diff)}</td>
              <td className="px-3 py-2 text-right font-semibold">{typeof r.효율점수 === 'number' ? r.효율점수.toFixed(2) : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
