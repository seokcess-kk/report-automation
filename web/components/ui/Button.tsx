import { cn } from './cn';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline';
type Size = 'sm' | 'md' | 'lg';

const base =
  'inline-flex items-center justify-center gap-1.5 font-medium rounded-md ' +
  'transition-colors duration-150 ease-swift whitespace-nowrap ' +
  'disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98] ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg';

const variants: Record<Variant, string> = {
  primary: 'bg-accent text-bg hover:bg-accent-strong',
  secondary: 'bg-elevated text-fg hover:bg-border-strong',
  ghost: 'text-muted hover:text-fg hover:bg-elevated',
  danger: 'bg-danger text-white hover:opacity-90',
  outline: 'border border-border-strong text-fg hover:bg-elevated',
};

const sizes: Record<Size, string> = {
  sm: 'h-7 px-2.5 text-xs',
  md: 'h-9 px-3.5 text-sm',
  lg: 'h-11 px-5 text-sm',
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

export function Button({
  variant = 'secondary',
  size = 'md',
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button className={cn(base, variants[variant], sizes[size], className)} {...rest}>
      {children}
    </button>
  );
}
