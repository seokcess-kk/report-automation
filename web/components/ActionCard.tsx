'use client';
import { ActionProposal } from '@/lib/reports';

const PRIORITY_META: Record<string, { label: string; badge: string; border: string }> = {
  high: { label: '긴급', badge: 'bg-rose-900/50 text-brand-danger', border: 'border-brand-danger' },
  medium: { label: '권장', badge: 'bg-amber-900/50 text-brand-warn', border: 'border-brand-warn' },
  low: { label: '참고', badge: 'bg-slate-700 text-slate-300', border: 'border-slate-500' },
};

const ACTION_LABEL: Record<string, string> = {
  budget_decrease: '예산 감액',
  budget_increase: '예산 증액',
  budget_reallocate: '예산 재분배',
  pause_creative: '소재 중단',
  scale_creative: '소재 확대',
  reactivate_creative: '소재 재활성화',
  creative_review: '소재 재검토',
  exclude_age: '나이대 축소',
  expand_age: '나이대 확대',
  dayparting: '시간대 축소',
  weekday_boost: '요일 가중',
  type_scale: '유형 확대',
};

type DecisionStatus = 'approved' | 'queued' | 'executed' | 'rejected' | null;

export function ActionCard({
  p,
  onClick,
  decisionStatus,
}: {
  p: ActionProposal;
  onClick: () => void;
  decisionStatus: DecisionStatus;
}) {
  const meta = PRIORITY_META[p.priority] || PRIORITY_META.low;
  const actionLabel = ACTION_LABEL[p.action_type] || p.action_type;
  const rec = p.recommended_value;
  const hasDelta = rec?.current != null && rec?.proposed != null;

  return (
    <li className={`card border-l-4 ${meta.border}`}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${meta.badge}`}>
              {meta.label}
            </span>
            <span className="text-[10px] text-slate-500 uppercase tracking-wide">{actionLabel}</span>
            <span className="text-[10px] text-slate-500">#{p.id}</span>
            {decisionStatus === 'approved' && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-900/50 text-brand-success">
                ✓ 승인
              </span>
            )}
            {decisionStatus === 'queued' && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-900/50 text-brand-warn">
                ⏳ 대기
              </span>
            )}
            {decisionStatus === 'executed' && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-sky-900/50 text-sky-300">
                ✅ 실행 완료
              </span>
            )}
            {decisionStatus === 'rejected' && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-700 text-slate-400">
                ✕ 거절
              </span>
            )}
          </div>
          <div className="font-semibold">{p.title}</div>
          <div className="text-sm text-slate-400 mt-1">{p.reason}</div>
        </div>
        {hasDelta && (
          <div className="shrink-0 text-right">
            <div className="text-[10px] text-slate-500">현재 → 제안</div>
            <div className="text-sm font-mono text-slate-300">
              {formatValue(rec.current, rec.unit)}
            </div>
            <div className="text-sm font-mono text-brand-primary">
              {formatValue(rec.proposed, rec.unit)}
            </div>
          </div>
        )}
      </div>
      <div className="flex items-center justify-end gap-2 mt-2">
        <button
          type="button"
          onClick={onClick}
          className="text-xs px-3 py-1 rounded bg-brand-primary/20 text-brand-primary hover:bg-brand-primary/30 border border-brand-primary/40"
        >
          상세 보기
        </button>
      </div>
    </li>
  );
}

function formatValue(v: any, unit?: string): string {
  if (typeof v === 'number') {
    return `${v.toLocaleString()}${unit ? ' ' + unit : ''}`;
  }
  return String(v);
}
