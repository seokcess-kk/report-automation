'use client';
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts';

interface DailyPoint {
  date_str?: string;
  date?: string;
  cost: number;
  conv: number;
  cpa?: number | null;
  ctr?: number | null;
}

export function DailyTrendChart({ data }: { data: DailyPoint[] }) {
  if (!data?.length) return null;
  const chartData = data.map((d) => ({
    date: d.date_str ?? (d.date ? d.date.slice(5) : ''),
    비용: d.cost ?? 0,
    전환: d.conv ?? 0,
  }));
  return (
    <div className="card">
      <h2 className="font-semibold mb-3">일별 추이</h2>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} />
          <YAxis yAxisId="left" stroke="#60a5fa" fontSize={11} />
          <YAxis yAxisId="right" orientation="right" stroke="#4ade80" fontSize={11} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', fontSize: 12 }}
            formatter={(v: number, name: string) => [v.toLocaleString(), name]}
          />
          <Legend />
          <Line yAxisId="left" type="monotone" dataKey="비용" stroke="#60a5fa" strokeWidth={2} dot={{ r: 3 }} />
          <Line yAxisId="right" type="monotone" dataKey="전환" stroke="#4ade80" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
