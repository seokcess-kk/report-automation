'use client';
import { useState } from 'react';
import { SegmentAnalysis, SegmentRow } from '@/lib/reports';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer, CartesianGrid } from 'recharts';
import { fmtMan } from '@/lib/format';
import { InfoTip } from './InfoTip';

const EFF_SCORE_EXPLAIN = `효율점수 = 전환비중 / 비용비중
1.0 = 비용만큼 전환 (비례)
1.1+ = 고효율 (비중 대비 전환 높음)
0.7 미만 = 비효율`;

type TabKey = 'weekday' | 'hour' | 'creative_type';

const TABS: { key: TabKey; label: string; keyField: string }[] = [
  { key: 'weekday', label: '요일', keyField: 'weekday' },
  { key: 'hour', label: '시간대', keyField: 'hour' },
  { key: 'creative_type', label: '소재 유형', keyField: '소재유형' },
];

function scoreColor(score: number | null | undefined): string {
  if (score == null || !isFinite(score)) return '#64748b';
  if (score >= 1.1) return '#4ade80';   // success
  if (score >= 0.9) return '#60a5fa';   // primary
  if (score >= 0.7) return '#f59e0b';   // warn
  return '#f87171';                      // danger
}

export function AnalysisTabs({ segments }: { segments: SegmentAnalysis }) {
  const [tab, setTab] = useState<TabKey>('weekday');
  const active = TABS.find((t) => t.key === tab)!;
  const rows = segments[tab] || [];
  const keyField = active.keyField;

  return (
    <section className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          세그먼트 분석
          <InfoTip text={EFF_SCORE_EXPLAIN} />
        </h2>
        <div className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`px-3 py-1 text-xs rounded ${
                tab === t.key
                  ? 'bg-brand-primary text-brand-bg font-semibold'
                  : 'bg-brand-bg text-slate-300 hover:bg-slate-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="text-sm text-slate-400 py-6 text-center">
          {tab === 'hour'
            ? '시간대 데이터가 없습니다. 수집: python run_analysis.py --collect --include-hour'
            : '데이터가 없습니다.'}
        </div>
      ) : (
        <>
          <div className="h-64 mb-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rows} margin={{ top: 10, right: 10, bottom: 20, left: 0 }}>
                <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                <XAxis
                  dataKey={keyField}
                  stroke="#94a3b8"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v) => tab === 'hour' ? `${v}시` : String(v)}
                />
                <YAxis
                  stroke="#94a3b8"
                  tick={{ fontSize: 11 }}
                  label={{ value: '효율점수', angle: -90, position: 'insideLeft', fill: '#94a3b8', fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', fontSize: 12 }}
                  labelStyle={{ color: '#cbd5e1' }}
                  formatter={(v: any, name: string) => {
                    if (name === '예산효율점수') return [Number(v).toFixed(2), name];
                    return [v, name];
                  }}
                  labelFormatter={(v) => tab === 'hour' ? `${v}시` : String(v)}
                />
                <Bar dataKey="예산효율점수" radius={[4, 4, 0, 0]}>
                  {rows.map((r, i) => (
                    <Cell key={i} fill={scoreColor(r.예산효율점수)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-slate-400 border-b border-brand-border">
                <tr>
                  <th className="text-left py-2 px-2">{active.label}</th>
                  <th className="text-right px-2">비용</th>
                  <th className="text-right px-2">전환</th>
                  <th className="text-right px-2 hidden sm:table-cell">CPA</th>
                  <th className="text-right px-2 hidden md:table-cell">비용비중</th>
                  <th className="text-right px-2 hidden md:table-cell">전환비중</th>
                  <th className="text-right px-2">효율점수</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i} className="border-b border-brand-border/50 hover:bg-brand-bg/40">
                    <td className="py-1.5 px-2 font-medium">
                      {tab === 'hour' ? `${r[keyField]}시` : r[keyField]}
                    </td>
                    <td className="text-right px-2 text-slate-300">{fmtMan(r.총비용)}</td>
                    <td className="text-right px-2">{r.총전환}건</td>
                    <td className="text-right px-2 text-slate-300 hidden sm:table-cell">
                      {r.CPA != null ? Number(r.CPA).toLocaleString() : '-'}
                    </td>
                    <td className="text-right px-2 text-slate-400 hidden md:table-cell">{r.비용비중}%</td>
                    <td className="text-right px-2 text-slate-400 hidden md:table-cell">{r.전환비중}%</td>
                    <td className="text-right px-2 font-bold" style={{ color: scoreColor(r.예산효율점수) }}>
                      {r.예산효율점수 != null ? Number(r.예산효율점수).toFixed(2) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
