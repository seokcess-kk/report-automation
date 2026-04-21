'use client';
import { ActionProposal } from '@/lib/reports';
import { Badge } from './ui';
import { cn } from './ui/cn';

const PRIORITY_META: Record<string, { label: string; tone: 'danger' | 'warn' | 'neutral'; accent: string }> = {
  high: { label: '긴급', tone: 'danger', accent: 'before:bg-danger' },
  medium: { label: '권장', tone: 'warn', accent: 'before:bg-warn' },
  low: { label: '참고', tone: 'neutral', accent: 'before:bg-subtle' },
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

const STATUS_BADGE: Record<string, { label: string; tone: 'success' | 'warn' | 'info' | 'neutral' }> = {
  approved: { label: '승인', tone: 'success' },
  queued: { label: '대기', tone: 'warn' },
  executed: { label: '실행완료', tone: 'info' },
  rejected: { label: '거절', tone: 'neutral' },
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
  const status = decisionStatus ? STATUS_BADGE[decisionStatus] : null;

  return (
    <li
      onClick={onClick}
      title={`#${p.id}`}
      className={cn(
        'group relative cursor-pointer transition-all duration-150 ease-swift',
        'bg-surface border border-border hover:border-border-strong rounded-xl p-4',
        'pl-5 before:absolute before:left-0 before:top-3 before:bottom-3 before:w-1 before:rounded-full',
        meta.accent
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1.5 flex-wrap">
            <Badge tone={meta.tone}>{meta.label}</Badge>
            <span className="text-2xs text-subtle uppercase tracking-wider">{actionLabel}</span>
            {status && <Badge tone={status.tone}>{status.label}</Badge>}
          </div>
          <div className="text-sm font-semibold text-fg leading-snug">{p.title}</div>
          <div className="text-xs text-muted mt-1 leading-relaxed">{p.reason}</div>
        </div>
        {hasDelta && (
          <div className="shrink-0 text-right">
            <div className="text-2xs text-subtle uppercase tracking-wider mb-0.5">현재 → 제안</div>
            <div className="text-xs font-mono text-subtle line-through tabular-nums">
              {formatValue(rec.current, rec.unit)}
            </div>
            <div className="text-sm font-mono text-accent-strong font-semibold tabular-nums">
              {formatValue(rec.proposed, rec.unit)}
            </div>
          </div>
        )}
      </div>
      <div className="flex items-center justify-end mt-3 text-2xs text-subtle group-hover:text-accent-strong transition-colors">
        <span>상세 →</span>
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
