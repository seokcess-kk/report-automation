export function InsightsBlock({ items }: { items: any[] }) {
  if (!items?.length) return null;
  return (
    <div className="card">
      <h2 className="font-semibold mb-3">종합 인사이트</h2>
      <ul className="space-y-3">
        {items.map((ins, i) => (
          <li key={i} className="border-l-2 pl-3" style={{ borderColor: ins.color }}>
            <div className="text-sm font-medium" style={{ color: ins.color }}>
              [{ins.type}] {ins.title}
            </div>
            <ul className="mt-1 ml-4 text-sm text-slate-300 list-disc">
              {ins.points.map((p: string, j: number) => (
                <li key={j}>{p}</li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </div>
  );
}
