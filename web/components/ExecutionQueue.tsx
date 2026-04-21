'use client';
import { useState } from 'react';
import { DecisionRecord } from './ActionDetailModal';
import { ExecutePasswordModal } from './ExecutePasswordModal';

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
      <section className="card">
        <h2 className="text-lg font-semibold mb-3">실행 관리</h2>

        <div>
          <h3 className="text-sm text-slate-300 font-semibold mb-2">
            실행 대기 <span className="text-slate-500">({queued.length})</span>
          </h3>
          {queued.length === 0 ? (
            <p className="text-xs text-slate-500 mb-4">대기 중인 항목이 없습니다.</p>
          ) : (
            <ul className="space-y-2 mb-4">
              {queued.map((d) => (
                <li key={d.id} className="flex items-center justify-between bg-brand-bg/40 rounded p-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-[10px] text-slate-500">#{d.proposal_id}</span>
                      <span className="text-[10px] bg-amber-900/50 text-brand-warn px-1.5 py-0.5 rounded">⏳ 대기</span>
                    </div>
                    <div className="text-sm font-medium truncate">{d.proposal_snapshot?.title || '(제목 없음)'}</div>
                    {d.note && <div className="text-[10px] text-slate-500 truncate">메모: {d.note}</div>}
                  </div>
                  <button
                    type="button"
                    onClick={() => setPending(d)}
                    className="shrink-0 text-xs px-3 py-1.5 rounded bg-brand-danger/80 hover:bg-brand-danger text-white font-semibold"
                  >
                    실행
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {executed.length > 0 && (
          <details>
            <summary className="text-sm text-slate-400 cursor-pointer hover:text-slate-200">
              실행 이력 ({executed.length})
            </summary>
            <ul className="space-y-1 mt-2">
              {executed.slice().reverse().map((d) => (
                <li key={d.id} className="flex items-center gap-2 text-xs bg-brand-bg/40 rounded px-3 py-2">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                    d.execution_result?.status === 'success'
                      ? 'bg-sky-900/50 text-sky-300'
                      : 'bg-rose-900/50 text-brand-danger'
                  }`}>
                    {d.execution_result?.status === 'success' ? '✅' : '❌'}
                    {d.execution_result?.dry_run && ' DRY'}
                  </span>
                  <span className="text-slate-500">{new Date(d.executed_at || '').toLocaleString('ko-KR')}</span>
                  <span className="truncate">{d.proposal_snapshot?.title || d.proposal_id}</span>
                </li>
              ))}
            </ul>
          </details>
        )}
      </section>

      {pending && (
        <ExecutePasswordModal
          decision={pending}
          onClose={() => setPending(null)}
          onExecuted={(updated) => {
            onExecuted(updated);
            setPending(null);
          }}
        />
      )}
    </>
  );
}
