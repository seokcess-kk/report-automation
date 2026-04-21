import { cn } from './cn';

export function Stat({
  label,
  value,
  sub,
  delta,
  deltaTone,
  className,
}: {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  delta?: React.ReactNode;
  deltaTone?: 'positive' | 'negative' | 'neutral';
  className?: string;
}) {
  const deltaClass =
    deltaTone === 'positive'
      ? 'text-success'
      : deltaTone === 'negative'
      ? 'text-danger'
      : 'text-muted';

  return (
    <div className={cn('flex flex-col', className)}>
      <div className="text-2xs text-subtle uppercase tracking-wide mb-1">{label}</div>
      <div className="text-xl font-semibold text-fg tabular-nums">{value}</div>
      {(sub || delta) && (
        <div className="mt-1 flex items-baseline gap-2 text-2xs">
          {sub && <span className="text-muted">{sub}</span>}
          {delta && <span className={cn('tabular-nums', deltaClass)}>{delta}</span>}
        </div>
      )}
    </div>
  );
}
