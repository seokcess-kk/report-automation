'use client';
import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';

interface Pt {
  date_str: string;
  cost: number;
  conv: number;
  cpa?: number | null;
}

export function MonthlyDailyChart({ data }: { data: Pt[] }) {
  if (!data?.length) return null;
  const chartData = data.map((d) => ({
    day: d.date_str,
    비용: d.cost,
    전환: d.conv,
  }));
  return (
    <div className="card">
      <h2 className="font-semibold mb-3">월간 일별 추이</h2>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="day" stroke="#94a3b8" fontSize={11} />
          <YAxis yAxisId="left" stroke="#60a5fa" fontSize={11} />
          <YAxis yAxisId="right" orientation="right" stroke="#4ade80" fontSize={11} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', fontSize: 12 }}
            formatter={(v: number) => v.toLocaleString()}
          />
          <Legend />
          <Bar yAxisId="left" dataKey="비용" fill="#60a5fa" opacity={0.6} />
          <Line yAxisId="right" type="monotone" dataKey="전환" stroke="#4ade80" strokeWidth={2} dot={{ r: 3 }} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
