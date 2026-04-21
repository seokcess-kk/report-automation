import { cn } from './cn';

type Status = 'ok' | 'warn' | 'danger' | 'neutral';
type Size = 'sm' | 'md' | 'lg';

const colors: Record<Status, string> = {
  ok: 'bg-success',
  warn: 'bg-warn',
  danger: 'bg-danger',
  neutral: 'bg-muted',
};

const sizes: Record<Size, string> = {
  sm: 'w-1.5 h-1.5',
  md: 'w-2 h-2',
  lg: 'w-2.5 h-2.5',
};

export function StatusDot({
  status,
  size = 'md',
  pulse,
  className,
}: {
  status: Status;
  size?: Size;
  pulse?: boolean;
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-block rounded-full shrink-0',
        colors[status],
        sizes[size],
        pulse && 'animate-pulse',
        className
      )}
    />
  );
}
