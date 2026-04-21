'use client';
import { useEffect, useState } from 'react';

export interface SectionDef {
  id: string;
  label: string;
  count?: number;
}

export function SectionNav({ sections }: { sections: SectionDef[] }) {
  const [active, setActive] = useState<string>(sections[0]?.id || '');

  useEffect(() => {
    const els = sections
      .map((s) => document.getElementById(s.id))
      .filter((e): e is HTMLElement => !!e);
    if (els.length === 0) return;

    const obs = new IntersectionObserver(
      (entries) => {
        // 현재 뷰포트 상단 근처에 있는 섹션을 활성화
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible.length > 0) {
          setActive(visible[0].target.id);
        }
      },
      { rootMargin: '-80px 0px -60% 0px', threshold: 0.01 }
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, [sections]);

  function go(id: string) {
    const el = document.getElementById(id);
    if (!el) return;
    const y = el.getBoundingClientRect().top + window.scrollY - 64;
    window.scrollTo({ top: y, behavior: 'smooth' });
  }

  return (
    <nav className="sticky top-[52px] z-20 -mx-4 px-4 bg-brand-bg/90 backdrop-blur border-b border-brand-border">
      <div className="max-w-6xl mx-auto flex gap-1 py-2 overflow-x-auto">
        {sections.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => go(s.id)}
            className={`shrink-0 px-3 py-1 text-xs rounded transition-colors ${
              active === s.id
                ? 'bg-brand-primary text-brand-bg font-semibold'
                : 'text-slate-300 hover:text-white hover:bg-brand-card'
            }`}
          >
            {s.label}
            {s.count != null && s.count > 0 && (
              <span className="ml-1 opacity-70">{s.count}</span>
            )}
          </button>
        ))}
      </div>
    </nav>
  );
}
