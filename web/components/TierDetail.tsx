'use client';
import { useState } from 'react';
import { fmt, fmtPct } from '@/lib/format';

interface TierItem {
  creative_name: string;
  TIER: string;
  총비용: number;
  총전환: number;
  집행일수: number;
  지점목록: string[];
  CPA: number | null;
  CTR: number | null;
  CVR: number | null;
  소재유형: string;
}

const TIER_COLORS: Record<string, string> = {
  TIER1: 'border-brand-success',
  TIER2: 'border-brand-primary',
  TIER3: 'border-brand-warn',
  TIER4: 'border-brand-danger',
  LOW_VOLUME: 'border-slate-600',
};

export function TierDetail({ items }: { items: TierItem[] }) {
  const tiers = ['TIER1', 'TIER2', 'TIER3', 'TIER4', 'LOW_VOLUME'];
  const [filter, setFilter] = useState<string>('ALL');
  const shown = filter === 'ALL' ? items : items.filter((i) => i.TIER === filter);
  const counts: Record<string, number> = {};
  items.forEach((i) => { counts[i.TIER] = (counts[i.TIER] || 0) + 1; });

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h2 className="font-semibold">소재 TIER 분류</h2>
        <div className="flex gap-1 flex-wrap">
          <FilterBtn label={`전체 ${items.length}`} active={filter === 'ALL'} onClick={() => setFilter('ALL')} />
          {tiers.map((t) => (
            <FilterBtn
              key={t}
              label={`${t} ${counts[t] ?? 0}`}
              active={filter === t}
              onClick={() => setFilter(t)}
            />
          ))}
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {shown.map((it, i) => (
          <div key={i} className={`border-l-4 bg-brand-bg/40 rounded p-3 ${TIER_COLORS[it.TIER] ?? 'border-slate-600'}`}>
            <div className="flex items-start justify-between mb-1 gap-2">
              <span className="font-medium text-sm">{it.creative_name}</span>
              <span className="text-xs text-slate-400 whitespace-nowrap">{it.TIER}</span>
            </div>
            <div className="text-xs text-slate-400 mb-2">{it.소재유형} · 집행 {it.집행일수}일 · 지점 {it.지점목록.length}개</div>
            <div className="grid grid-cols-4 gap-2 text-xs">
              <Metric label="비용" value={`${(it.총비용 / 10000).toFixed(1)}만`} />
              <Metric label="전환" value={`${it.총전환}`} />
              <Metric label="CPA" value={fmt(it.CPA, '원')} />
              <Metric label="CVR" value={fmtPct(it.CVR)} />
            </div>
          </div>
        ))}
        {shown.length === 0 && <div className="text-sm text-slate-400 col-span-2">해당 TIER 소재가 없습니다.</div>}
      </div>
    </div>
  );
}

function FilterBtn({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`text-xs px-2 py-1 rounded border ${active ? 'bg-brand-primary text-brand-bg border-brand-primary' : 'border-brand-border text-slate-300 hover:border-brand-primary'}`}
    >
      {label}
    </button>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-slate-500">{label}</div>
      <div className="font-medium">{value}</div>
    </div>
  );
}
