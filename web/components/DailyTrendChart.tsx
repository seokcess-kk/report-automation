'use client';
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts';

interface DailyPoint {
  date: string;
  cost: number;
  conv: number;
  cpa: number | null;
}

export function DailyTrendChart({ data }: { data: DailyPoint[] }) {
  const chartData = data.map((d) => ({
    date: d.date.slice(5), // MM-DD
    비용: d.cost,
    전환: d.conv,
    CPA: d.cpa ?? 0,
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
