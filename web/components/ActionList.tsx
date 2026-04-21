'use client';
import { useMemo, useState } from 'react';
import { ActionProposal } from '@/lib/reports';
import { ActionCard } from './ActionCard';
import { DecisionRecord } from './ActionDetailModal';
import { cn } from './ui/cn';

const PRIORITY_LABEL: Record<string, string> = { high: '긴급', medium: '권장', low: '참고' };
const ACTION_LABEL: Record<string, string> = {
  budget_decrease: '예산 감액', budget_increase: '예산 증액', budget_reallocate: '예산 재분배',
  pause_creative: '소재 중단', scale_creative: '소재 확대', reactivate_creative: '소재 재활성화',
  creative_review: '소재 재검토', exclude_age: '나이대 축소', expand_age: '나이대 확대',
  dayparting: '시간대 축소', weekday_boost: '요일 가중', type_scale: '유형 확대',
};
const STATUS_LABEL: Record<string, string> = {
  undecided: '미결정', approved: '승인', queued: '대기', executed: '실행완료', rejected: '거절',
};

type Status = 'undecided' | 'approved' | 'queued' | 'executed' | 'rejected';

export function ActionList({
  proposals, decisionMap, onClick,
}: {
  proposals: ActionProposal[];
  decisionMap: Map<string, DecisionRecord>;
  onClick: (p: ActionProposal) => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const [filters, setFilters] = useState<{
    priority: string[]; type: string[]; status: string[]; target: string[];
  }>({ priority: [], type: [], status: [], target: [] });

  function statusOf(p: ActionProposal): Status {
    const d = decisionMap.get(p.id);
    if (!d) return 'undecided';
    if (d.decision === 'reject') return 'rejected';
    if (d.executed) return 'executed';
    if (d.queued) return 'queued';
    return 'approved';
  }

  const types = useMemo(() => Array.from(new Set(proposals.map((p) => p.action_type))), [proposals]);
  const targets = useMemo(() => Array.from(new Set(proposals.map((p) => p.target))), [proposals]);

  const filtered = useMemo(() => proposals.filter((p) => {
    if (filters.priority.length && !filters.priority.includes(p.priority)) return false;
    if (filters.type.length && !filters.type.includes(p.action_type)) return false;
    if (filters.target.length && !filters.target.includes(p.target)) return false;
    if (filters.status.length && !filters.status.includes(statusOf(p))) return false;
    return true;
  }), [proposals, filters, decisionMap]);

  const anyFilter = filters.priority.length + filters.type.length + filters.status.length + filters.target.length > 0;
  const visible = showAll || anyFilter ? filtered : filtered.slice(0, 5);

  function toggle(key: keyof typeof filters, value: string) {
    setFilters((prev) => {
      const set = prev[key];
      return { ...prev, [key]: set.includes(value) ? set.filter((v) => v !== value) : [...set, value] };
    });
  }
  function clearAll() {
    setFilters({ priority: [], type: [], status: [], target: [] });
    setShowAll(false);
  }

  return (
    <div>
      <div className="flex items-baseline justify-between mb-4 flex-wrap gap-2">
        <h2 className="text-lg font-semibold text-fg tracking-tight">
          {showAll || anyFilter ? '액션 목록' : '오늘의 액션 Top 5'}
        </h2>
        <div className="text-2xs text-subtle tabular-nums">
          {visible.length} / {anyFilter ? filtered.length : proposals.length}건 표시
          {anyFilter && <span className="text-accent ml-1">· 필터 적용</span>}
        </div>
      </div>

      <div className="bg-surface border border-border rounded-xl p-4 mb-4">
        <FilterGroup label="우선순위" options={['high', 'medium', 'low']} labels={PRIORITY_LABEL} selected={filters.priority} onToggle={(v) => toggle('priority', v)} />
        <FilterGroup label="상태" options={['undecided', 'approved', 'queued', 'executed', 'rejected']} labels={STATUS_LABEL} selected={filters.status} onToggle={(v) => toggle('status', v)} />
        <FilterGroup label="타입" options={types} labels={ACTION_LABEL} selected={filters.type} onToggle={(v) => toggle('type', v)} />
        <FilterGroup label="대상" options={targets} labels={{}} selected={filters.target} onToggle={(v) => toggle('target', v)} collapsed />
        <div className="flex items-center justify-between pt-3 mt-1 border-t border-border">
          <button
            type="button"
            onClick={() => setShowAll((v) => !v)}
            className="text-xs text-accent hover:text-accent-strong font-medium"
          >
            {showAll || anyFilter ? 'Top 5만 보기' : `전체 ${proposals.length}건 보기 →`}
          </button>
          {anyFilter && (
            <button
              type="button"
              onClick={clearAll}
              className="text-2xs text-muted hover:text-fg"
            >
              필터 초기화
            </button>
          )}
        </div>
      </div>

      {visible.length > 0 ? (
        <ul className="space-y-2">
          {visible.map((p) => {
            const s = statusOf(p);
            return (
              <ActionCard
                key={p.id}
                p={p}
                decisionStatus={s === 'undecided' ? null : s}
                onClick={() => onClick(p)}
              />
            );
          })}
        </ul>
      ) : (
        <div className="bg-surface border border-border rounded-xl py-8 text-center text-sm text-muted">
          {anyFilter ? '필터 조건에 매칭되는 액션이 없습니다.' : '현재 규칙 기준 제안이 없습니다.'}
        </div>
      )}
    </div>
  );
}

function FilterGroup({
  label, options, labels, selected, onToggle, collapsed,
}: {
  label: string; options: string[]; labels: Record<string, string>;
  selected: string[]; onToggle: (v: string) => void; collapsed?: boolean;
}) {
  const [open, setOpen] = useState(!collapsed);
  if (options.length === 0) return null;

  return (
    <div className="mb-3 last:mb-0">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-2xs text-subtle uppercase tracking-wider font-semibold">{label}</span>
        {collapsed && (
          <button type="button" onClick={() => setOpen(!open)} className="text-2xs text-muted hover:text-fg">
            {open ? '접기' : `펼치기 (${options.length})`}
          </button>
        )}
        {selected.length > 0 && (
          <span className="text-2xs text-accent-strong">{selected.length}개 선택</span>
        )}
      </div>
      {open && (
        <div className="flex flex-wrap gap-1.5">
          {options.map((opt) => {
            const active = selected.includes(opt);
            return (
              <button
                key={opt}
                type="button"
                onClick={() => onToggle(opt)}
                className={cn(
                  'text-xs px-2 py-1 rounded-md border transition-colors duration-150',
                  active
                    ? 'bg-accent text-bg border-accent font-semibold'
                    : 'bg-transparent border-border-strong text-muted hover:text-fg hover:border-muted'
                )}
              >
                {labels[opt] || opt}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
