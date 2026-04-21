'use client';
import { useEffect, useState } from 'react';
import { cn } from './ui/cn';

export interface SectionDef {
  id: string;
  label: string;
  count?: number;
}

export function SectionNav({ sections }: { sections: SectionDef[] }) {
  const [active, setActive] = useState<string>(sections[0]?.id || '');

  useEffect(() => {
    const els = sections.map((s) => document.getElementById(s.id)).filter((e): e is HTMLElement => !!e);
    if (els.length === 0) return;
    const obs = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible.length > 0) setActive(visible[0].target.id);
      },
      { rootMargin: '-96px 0px -60% 0px', threshold: 0.01 }
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, [sections]);

  function go(id: string) {
    const el = document.getElementById(id);
    if (!el) return;
    const y = el.getBoundingClientRect().top + window.scrollY - 72;
    window.scrollTo({ top: y, behavior: 'smooth' });
  }

  return (
    <nav className="sticky top-12 z-20 -mx-4 px-4 bg-bg/85 backdrop-blur-md border-b border-border">
      <div className="max-w-7xl mx-auto flex gap-0.5 py-2 overflow-x-auto">
        {sections.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => go(s.id)}
            className={cn(
              'shrink-0 px-3 py-1.5 text-xs rounded-md transition-all duration-150 ease-swift',
              'font-medium',
              active === s.id
                ? 'bg-elevated text-fg'
                : 'text-muted hover:text-fg hover:bg-elevated/60'
            )}
          >
            {s.label}
            {s.count != null && s.count > 0 && (
              <span
                className={cn(
                  'ml-1.5 inline-flex items-center justify-center px-1 min-w-[16px] h-4 rounded text-[10px] tabular-nums',
                  active === s.id ? 'bg-accent/20 text-accent-strong' : 'bg-elevated text-muted'
                )}
              >
                {s.count}
              </span>
            )}
          </button>
        ))}
      </div>
    </nav>
  );
}
