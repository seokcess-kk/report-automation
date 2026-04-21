import { cn } from './cn';

type Variant = 'flat' | 'default' | 'raised';

const variants: Record<Variant, string> = {
  flat: 'bg-transparent border border-border rounded-xl',
  default: 'bg-surface border border-border rounded-xl shadow-subtle',
  raised: 'bg-surface border border-border-strong rounded-xl shadow-card',
};

export function Card({
  variant = 'default',
  className,
  children,
  ...rest
}: React.HTMLAttributes<HTMLDivElement> & { variant?: Variant }) {
  return (
    <div className={cn(variants[variant], 'p-4', className)} {...rest}>
      {children}
    </div>
  );
}

export function CardHeader({ className, children }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('mb-3 flex items-start justify-between gap-3', className)}>{children}</div>;
}

export function CardTitle({ className, children }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn('text-base font-semibold text-fg', className)}>{children}</h3>;
}

export function CardDescription({ className, children }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-xs text-muted', className)}>{children}</p>;
}
