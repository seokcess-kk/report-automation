'use client';
import { useEffect, useState } from 'react';
import { ActionProposal } from '@/lib/reports';
import { Badge, Button } from './ui';
import { cn } from './ui/cn';

const ACTION_LABEL: Record<string, string> = {
  budget_decrease: '예산 감액', budget_increase: '예산 증액', budget_reallocate: '예산 재분배',
  pause_creative: '소재 중단', scale_creative: '소재 확대', reactivate_creative: '소재 재활성화',
  creative_review: '소재 전면 재검토', exclude_age: '나이대 타겟 축소', expand_age: '나이대 타겟 확대',
  dayparting: '시간대 송출 축소', weekday_boost: '요일 예산 가중', type_scale: '소재 유형 확대',
};

export type DecisionRecord = {
  id: string;
  proposal_id: string;
  proposal_snapshot: any;
  decision: 'approve' | 'reject';
  queued: boolean;
  decided_at: string;
  note: string;
  executed: boolean;
  executed_at: string | null;
  execution_result: { status: string; message: string; dry_run: boolean } | null;
};

export function ActionDetailModal({
  proposal, existingDecision, onClose, onDecided,
}: {
  proposal: ActionProposal;
  existingDecision: DecisionRecord | null;
  onClose: () => void;
  onDecided: (decision: DecisionRecord) => void;
}) {
  const [note, setNote] = useState(existingDecision?.note || '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [onClose]);

  async function submit(decision: 'approve' | 'reject', queued: boolean) {
    setSubmitting(true); setError(null);
    try {
      const res = await fetch('/api/actions/decisions', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proposal, decision, note, queued }),
      });
      if (!res.ok) { const j = await res.json().catch(() => ({})); throw new Error(j.error || `HTTP ${res.status}`); }
      const j = await res.json();
      onDecided(j.decision);
    } catch (e: any) { setError(String(e.message || e)); }
    finally { setSubmitting(false); }
  }

  const preview = previewText(proposal);
  const actionLabel = ACTION_LABEL[proposal.action_type] || proposal.action_type;
  const disabled = submitting || existingDecision?.executed;
  const priorityTone = proposal.priority === 'high' ? 'danger' : proposal.priority === 'medium' ? 'warn' : 'neutral';
  const priorityLabel = proposal.priority === 'high' ? '긴급' : proposal.priority === 'medium' ? '권장' : '참고';

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in" onClick={onClose}>
      <div
        className="bg-surface border border-border-strong rounded-xl shadow-raised w-full max-w-xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-surface/95 backdrop-blur border-b border-border px-5 py-4 flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 mb-1.5 flex-wrap">
              <Badge tone="neutral">{actionLabel}</Badge>
              <Badge tone={priorityTone}>{priorityLabel}</Badge>
              <span className="text-2xs text-subtle">#{proposal.id}</span>
            </div>
            <h3 className="text-base font-semibold text-fg leading-snug">{proposal.title}</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-md text-muted hover:text-fg hover:bg-elevated shrink-0"
          >✕</button>
        </div>

        <div className="p-5 space-y-4">
          <div className="text-sm text-muted leading-relaxed border-l-2 border-accent pl-3">
            {proposal.reason}
          </div>

          <div className="bg-elevated/50 border border-border rounded-lg p-4">
            <div className="text-2xs text-subtle uppercase tracking-wider mb-2 font-semibold">변경 미리보기 (Dry-run)</div>
            <pre className="text-xs whitespace-pre-wrap font-mono text-fg leading-relaxed">{preview}</pre>
            <p className="text-2xs text-subtle mt-3">
              ℹ️ 실행은 다음 단계에서 관리 비밀번호 확인 후 진행됩니다.
            </p>
          </div>

          {Object.keys(proposal.evidence || {}).length > 0 && (
            <details className="group">
              <summary className="text-xs text-muted cursor-pointer hover:text-fg flex items-center gap-1.5 list-none">
                <span className="transition-transform group-open:rotate-90">▸</span>
                근거 데이터
              </summary>
              <pre className="text-2xs bg-elevated/40 border border-border/50 rounded-md p-3 mt-2 overflow-x-auto text-muted tabular-nums">
                {JSON.stringify(proposal.evidence, null, 2)}
              </pre>
            </details>
          )}

          {existingDecision && (
            <div className={cn(
              'text-xs rounded-md px-3 py-2',
              existingDecision.executed
                ? 'bg-info-soft text-info'
                : existingDecision.queued
                  ? 'bg-warn-soft text-warn'
                  : existingDecision.decision === 'approve'
                    ? 'bg-success-soft text-success'
                    : 'bg-danger-soft text-danger'
            )}>
              상태: <strong>
                {existingDecision.executed ? '실행 완료'
                  : existingDecision.queued ? '실행 대기'
                  : existingDecision.decision === 'approve' ? '승인됨' : '거절됨'}
              </strong>
              {' · '}{new Date(existingDecision.decided_at).toLocaleString('ko-KR')}
              {existingDecision.note && ` · "${existingDecision.note}"`}
              {existingDecision.execution_result && (
                <div className="mt-1.5 text-fg">{existingDecision.execution_result.message}</div>
              )}
            </div>
          )}

          <label className="block">
            <span className="text-2xs text-subtle uppercase tracking-wider font-semibold">메모 (선택)</span>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              className="w-full mt-1.5 bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-fg placeholder:text-subtle focus:border-accent"
              placeholder="근거·제약·검토 의견"
              disabled={!!existingDecision?.executed}
            />
          </label>

          {error && <div className="text-xs text-danger bg-danger-soft/30 border border-danger-soft rounded px-3 py-2">⚠️ {error}</div>}

          <div className="flex items-center justify-end gap-2 flex-wrap pt-2">
            <Button variant="ghost" onClick={onClose} disabled={submitting}>취소</Button>
            <Button variant="outline" onClick={() => submit('reject', false)} disabled={disabled} className="text-danger border-danger/40 hover:bg-danger-soft/30">거절</Button>
            <Button variant="primary" onClick={() => submit('approve', true)} disabled={disabled}>
              {submitting ? '저장 중…' : '실행 예정'}
            </Button>
          </div>
          {existingDecision?.executed && (
            <p className="text-2xs text-subtle text-right">이미 실행된 결정은 변경할 수 없습니다.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function previewText(p: ActionProposal): string {
  const rec = p.recommended_value || {};
  switch (p.action_type) {
    case 'budget_decrease':
    case 'budget_increase': {
      const cur = Number(rec.current || 0);
      const prop = Number(rec.proposed || 0);
      const delta = prop - cur;
      const sign = delta >= 0 ? '+' : '';
      return `지점: ${p.target}\n현재 월 예산: ${cur.toLocaleString()}원\n제안 월 예산: ${prop.toLocaleString()}원 (${sign}${delta.toLocaleString()}원)\nAPI: adgroup/update/ (해당 지점 전 adgroup)`;
    }
    case 'budget_reallocate': {
      const amount = Number(rec.amount || 0);
      return `출처 (여유): ${rec.from}\n대상 (부족): ${rec.to}\n이관액: ${amount.toLocaleString()}원/월`;
    }
    case 'pause_creative':
      return `소재: ${p.target}\n액션: 상태 DISABLE (중단)\nAPI: ad/status/update/`;
    case 'scale_creative':
      return `소재: ${p.target}\n액션: 노출 비중 확대 (예산 증액 또는 타 adgroup 복제)`;
    case 'reactivate_creative':
      return `소재: ${p.target}\n액션: 상태 ENABLE (재활성화)\nAPI: ad/status/update/`;
    case 'creative_review':
      return `지점: ${rec.branch || p.target}\n액션: 해당 지점 전 소재 성과 리뷰 회의`;
    case 'exclude_age':
    case 'expand_age':
      return `나이대: ${rec.age}\n액션: adgroup 타겟팅의 age 가중치 조정`;
    case 'dayparting':
      return `시간대: ${rec.hour}시\n액션: 해당 시간대 송출 축소 (dayparting schedule)`;
    case 'weekday_boost':
      return `요일: ${rec.weekday}\n액션: 해당 요일 송출 가중 (dayparting schedule)`;
    case 'type_scale':
      return `소재 유형: ${rec.type}\n액션: 해당 유형 신규 소재 제작·확대`;
    default:
      return JSON.stringify(rec, null, 2);
  }
}
