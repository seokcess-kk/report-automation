'use client';
import { useState } from 'react';
import { fmt, fmtMan, fmtPct } from '@/lib/format';

interface Item {
  creative_name: string;
  TIER?: string;
  총비용: number;
  총전환: number;
  총클릭: number;
  집행일수: number;
  지점목록?: string[];
  소재유형?: string;
  CPA: number | null;
  CTR: number | null;
  CVR: number | null;
}

type SortKey = '총비용' | '총전환' | 'CPA' | 'CTR' | 'CVR';

export function CreativeLeaderboard({ items, title = '월간 소재 리더보드' }: { items: Item[]; title?: string }) {
  const [sort, setSort] = useState<SortKey>('총비용');
  const [desc, setDesc] = useState(true);

  const sorted = [...items].sort((a, b) => {
    const av = a[sort] ?? (sort === 'CPA' ? Infinity : 0);
    const bv = b[sort] ?? (sort === 'CPA' ? Infinity : 0);
    return desc ? (bv as number) - (av as number) : (av as number) - (bv as number);
  });

  function H(label: string, key: SortKey) {
    const active = sort === key;
    return (
      <th
        onClick={() => {
          if (active) setDesc(!desc);
          else { setSort(key); setDesc(true); }
        }}
        className={`px-3 py-2 cursor-pointer select-none text-right whitespace-nowrap ${active ? 'text-brand-primary' : 'text-slate-400'}`}
      >
        {label} {active ? (desc ? '↓' : '↑') : ''}
      </th>
    );
  }

  return (
    <div className="card overflow-x-auto">
      <h2 className="font-semibold mb-3">{title}</h2>
      <table className="w-full text-sm">
        <thead className="border-b border-brand-border">
          <tr>
            <th className="px-3 py-2 text-left text-slate-400">소재명</th>
            <th className="px-3 py-2 text-slate-400 text-center">TIER</th>
            {H('비용', '총비용')}
            {H('전환', '총전환')}
            {H('CPA', 'CPA')}
            {H('CTR', 'CTR')}
            {H('CVR', 'CVR')}
          </tr>
        </thead>
        <tbody>
          {sorted.slice(0, 20).map((it, i) => (
            <tr key={i} className="border-b border-brand-border/50 hover:bg-brand-bg/30">
              <td className="px-3 py-2">
                <div className="font-medium">{it.creative_name}</div>
                <div className="text-xs text-slate-500">
                  {it.소재유형} · 지점 {it.지점목록?.length ?? 0}개 · {it.집행일수}일
                </div>
              </td>
              <td className="px-3 py-2 text-center">
                <span className={`text-xs px-2 py-0.5 rounded border ${tierClass(it.TIER)}`}>
                  {it.TIER ?? '-'}
                </span>
              </td>
              <td className="px-3 py-2 text-right">{fmtMan(it.총비용)}</td>
              <td className="px-3 py-2 text-right">{it.총전환}</td>
              <td className="px-3 py-2 text-right">{fmt(it.CPA, '원')}</td>
              <td className="px-3 py-2 text-right">{fmtPct(it.CTR)}</td>
              <td className="px-3 py-2 text-right">{fmtPct(it.CVR)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function tierClass(tier?: string) {
  switch (tier) {
    case 'TIER1': return 'border-brand-success text-brand-success';
    case 'TIER2': return 'border-brand-primary text-brand-primary';
    case 'TIER3': return 'border-brand-warn text-brand-warn';
    case 'TIER4': return 'border-brand-danger text-brand-danger';
    default: return 'border-slate-600 text-slate-400';
  }
}
