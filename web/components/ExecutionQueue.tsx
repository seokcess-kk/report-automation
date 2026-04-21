'use client';
import { useState } from 'react';
import { DecisionRecord } from './ActionDetailModal';
import { ExecutePasswordModal } from './ExecutePasswordModal';
import { Badge, Button } from './ui';

export function ExecutionQueue({
  decisions,
  onExecuted,
}: {
  decisions: DecisionRecord[];
  onExecuted: (d: DecisionRecord) => void;
}) {
  const [pending, setPending] = useState<DecisionRecord | null>(null);

  const queued = decisions.filter((d) => d.queued && !d.executed);
  const executed = decisions.filter((d) => d.executed);

  if (queued.length === 0 && executed.length === 0) return null;

  return (
    <>
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-lg font-semibold text-fg tracking-tight mb-4">실행 관리</h2>

        <section>
          <div className="flex items-center gap-2 mb-3">
            <h3 className="text-sm font-semibold text-fg">실행 대기</h3>
            <Badge tone={queued.length > 0 ? 'warn' : 'neutral'}>{queued.length}</Badge>
          </div>
          {queued.length === 0 ? (
            <p className="text-xs text-muted mb-6">대기 중인 항목이 없습니다.</p>
          ) : (
            <ul className="space-y-2 mb-6">
              {queued.map((d) => (
                <li key={d.id} className="flex items-center justify-between gap-3 bg-elevated/50 border border-border rounded-lg p-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                      <Badge tone="warn">⏳ 대기</Badge>
                      <span className="text-2xs text-subtle">#{d.proposal_id}</span>
                    </div>
                    <div className="text-sm font-medium text-fg truncate">{d.proposal_snapshot?.title || '(제목 없음)'}</div>
                    {d.note && <div className="text-2xs text-subtle truncate mt-0.5">메모: {d.note}</div>}
                  </div>
                  <Button variant="danger" size="sm" onClick={() => setPending(d)}>
                    실행
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {executed.length > 0 && (
          <details className="mt-3 group">
            <summary className="text-sm text-muted cursor-pointer hover:text-fg flex items-center gap-2 list-none">
              <span className="transition-transform group-open:rotate-90">▸</span>
              실행 이력 <Badge tone="info">{executed.length}</Badge>
            </summary>
            <ul className="space-y-1 mt-3">
              {executed.slice().reverse().map((d) => (
                <li key={d.id} className="flex items-center gap-2 text-xs bg-elevated/40 border border-border/60 rounded px-3 py-2">
                  <Badge tone={d.execution_result?.status === 'success' ? 'info' : 'danger'}>
                    {d.execution_result?.status === 'success' ? '✓' : '✗'}
                  </Badge>
                  <span className="text-subtle tabular-nums">
                    {new Date(d.executed_at || '').toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                  </span>
                  <span className="truncate text-muted">{d.proposal_snapshot?.title || d.proposal_id}</span>
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>

      {pending && (
        <ExecutePasswordModal
          decision={pending}
          onClose={() => setPending(null)}
          onExecuted={(updated) => { onExecuted(updated); setPending(null); }}
        />
      )}
    </>
  );
}
