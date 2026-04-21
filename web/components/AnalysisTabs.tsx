'use client';
import { useState } from 'react';
import { SegmentAnalysis, SegmentRow } from '@/lib/reports';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer, CartesianGrid } from 'recharts';
import { fmtMan } from '@/lib/format';
import { InfoTip } from './InfoTip';
import { cn } from './ui/cn';

const EFF_SCORE_EXPLAIN = `효율점수 = 전환비중 / 비용비중
1.0 = 비용만큼 전환 (비례)
1.1+ = 고효율
0.7 미만 = 비효율`;

type TabKey = 'weekday' | 'hour' | 'creative_type';

const TABS: { key: TabKey; label: string; keyField: string }[] = [
  { key: 'weekday', label: '요일', keyField: 'weekday' },
  { key: 'hour', label: '시간대', keyField: 'hour' },
  { key: 'creative_type', label: '소재 유형', keyField: '소재유형' },
];

function scoreColor(score: number | null | undefined): string {
  if (score == null || !isFinite(score)) return 'rgb(113 113 122)';
  if (score >= 1.1) return 'rgb(52 211 153)';   // success
  if (score >= 0.9) return 'rgb(129 140 248)';  // accent
  if (score >= 0.7) return 'rgb(251 191 36)';   // warn
  return 'rgb(248 113 113)';                      // danger
}

export function AnalysisTabs({ segments }: { segments: SegmentAnalysis }) {
  const [tab, setTab] = useState<TabKey>('weekday');
  const active = TABS.find((t) => t.key === tab)!;
  const rows = segments[tab] || [];
  const keyField = active.keyField;

  return (
    <div className="bg-surface border border-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-5 gap-2 flex-wrap">
        <h2 className="text-lg font-semibold text-fg tracking-tight flex items-center gap-2">
          세그먼트 분석
          <InfoTip text={EFF_SCORE_EXPLAIN} />
        </h2>
        <div className="flex gap-0.5 p-0.5 bg-elevated rounded-lg">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={cn(
                'px-3 py-1 text-xs font-medium rounded transition-all duration-150 ease-swift',
                tab === t.key ? 'bg-surface text-fg shadow-subtle' : 'text-muted hover:text-fg'
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="py-10 text-center text-sm text-muted">
          {tab === 'hour'
            ? '시간대 데이터가 없습니다. 수집: python run_analysis.py --collect --include-hour'
            : '데이터가 없습니다.'}
        </div>
      ) : (
        <>
          <div className="h-64 mb-5 -mx-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rows} margin={{ top: 10, right: 10, bottom: 20, left: 0 }}>
                <CartesianGrid stroke="rgb(39 39 42)" strokeDasharray="3 3" />
                <XAxis
                  dataKey={keyField}
                  stroke="rgb(161 161 170)"
                  tick={{ fontSize: 11, fill: 'rgb(161 161 170)' }}
                  tickFormatter={(v) => tab === 'hour' ? `${v}시` : String(v)}
                />
                <YAxis
                  stroke="rgb(161 161 170)"
                  tick={{ fontSize: 11, fill: 'rgb(161 161 170)' }}
                />
                <Tooltip
                  cursor={{ fill: 'rgb(39 39 42 / 0.5)' }}
                  contentStyle={{ background: 'rgb(24 24 27)', border: '1px solid rgb(63 63 70)', fontSize: 12, borderRadius: 8 }}
                  labelStyle={{ color: 'rgb(244 244 245)', fontWeight: 600 }}
                  formatter={(v: any, name: string) => {
                    if (name === '예산효율점수') return [Number(v).toFixed(2), name];
                    return [v, name];
                  }}
                  labelFormatter={(v) => tab === 'hour' ? `${v}시` : String(v)}
                />
                <Bar dataKey="예산효율점수" radius={[4, 4, 0, 0]}>
                  {rows.map((r, i) => <Cell key={i} fill={scoreColor(r.예산효율점수)} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="overflow-x-auto -mx-2">
            <table className="w-full text-sm">
              <thead className="text-2xs text-subtle uppercase tracking-wider border-b border-border">
                <tr>
                  <th className="text-left py-2.5 px-3 font-medium">{active.label}</th>
                  <th className="text-right px-3 font-medium">비용</th>
                  <th className="text-right px-3 font-medium">전환</th>
                  <th className="text-right px-3 font-medium hidden sm:table-cell">CPA</th>
                  <th className="text-right px-3 font-medium hidden md:table-cell">비용비중</th>
                  <th className="text-right px-3 font-medium hidden md:table-cell">전환비중</th>
                  <th className="text-right px-3 font-medium">효율점수</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-elevated/50 transition-colors">
                    <td className="py-2 px-3 font-medium text-fg">
                      {tab === 'hour' ? `${r[keyField]}시` : r[keyField]}
                    </td>
                    <td className="text-right px-3 tabular-nums text-muted">{fmtMan(r.총비용)}</td>
                    <td className="text-right px-3 tabular-nums">{r.총전환}건</td>
                    <td className="text-right px-3 tabular-nums text-muted hidden sm:table-cell">
                      {r.CPA != null ? Number(r.CPA).toLocaleString() : '-'}
                    </td>
                    <td className="text-right px-3 tabular-nums text-subtle hidden md:table-cell">{r.비용비중}%</td>
                    <td className="text-right px-3 tabular-nums text-subtle hidden md:table-cell">{r.전환비중}%</td>
                    <td
                      className="text-right px-3 font-semibold tabular-nums"
                      style={{ color: scoreColor(r.예산효율점수) }}
                    >
                      {r.예산효율점수 != null ? Number(r.예산효율점수).toFixed(2) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
