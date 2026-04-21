import { cn } from './ui/cn';

export function InfoTip({
  text,
  children,
  className,
}: {
  text: string;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <span className={cn('relative inline-flex group items-center gap-1 align-middle', className)}>
      {children}
      <span
        className="inline-flex w-3.5 h-3.5 text-[9px] items-center justify-center rounded-full bg-elevated border border-border-strong text-muted cursor-help hover:text-fg hover:border-muted"
        aria-label="정보"
      >
        ⓘ
      </span>
      <span
        role="tooltip"
        className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 z-40
                   hidden group-hover:block
                   bg-elevated border border-border-strong rounded-md
                   text-2xs text-fg font-normal leading-relaxed
                   px-2.5 py-1.5 whitespace-pre-line max-w-xs text-left
                   shadow-card pointer-events-none"
      >
        {text}
      </span>
    </span>
  );
}
