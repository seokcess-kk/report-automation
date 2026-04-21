'use client';
import { useEffect, useState } from 'react';
import { ActionProposal } from '@/lib/reports';

const ACTION_LABEL: Record<string, string> = {
  budget_decrease: '예산 감액',
  budget_increase: '예산 증액',
  budget_reallocate: '예산 재분배',
  pause_creative: '소재 중단',
  scale_creative: '소재 확대',
  reactivate_creative: '소재 재활성화',
  creative_review: '소재 전면 재검토',
  exclude_age: '나이대 타겟 축소',
  expand_age: '나이대 타겟 확대',
  dayparting: '시간대 송출 축소',
  weekday_boost: '요일 예산 가중',
  type_scale: '소재 유형 확대',
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
  proposal,
  existingDecision,
  onClose,
  onDecided,
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
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch('/api/actions/decisions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proposal, decision, note, queued }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error || `HTTP ${res.status}`);
      }
      const j = await res.json();
      onDecided(j.decision);
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {
      setSubmitting(false);
    }
  }

  const preview = previewText(proposal);
  const actionLabel = ACTION_LABEL[proposal.action_type] || proposal.action_type;
  const disabled = submitting || existingDecision?.executed;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="card w-full max-w-xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-700 text-slate-300">
                {actionLabel}
              </span>
              <span className="text-[10px] text-slate-500">#{proposal.id}</span>
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                proposal.priority === 'high' ? 'bg-rose-900/50 text-brand-danger' :
                proposal.priority === 'medium' ? 'bg-amber-900/50 text-brand-warn' :
                'bg-slate-700 text-slate-400'
              }`}>
                {proposal.priority === 'high' ? '긴급' : proposal.priority === 'medium' ? '권장' : '참고'}
              </span>
            </div>
            <h3 className="font-bold text-lg">{proposal.title}</h3>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-white">✕</button>
        </div>

        <div className="text-sm text-slate-300 mb-4 border-l-2 border-brand-primary pl-3">
          {proposal.reason}
        </div>

        <div className="bg-brand-bg/60 rounded p-3 mb-4">
          <div className="text-xs text-slate-400 mb-2 font-semibold">변경 미리보기 (Dry-run)</div>
          <pre className="text-xs whitespace-pre-wrap font-mono text-slate-200">{preview}</pre>
          <p className="text-[10px] text-slate-500 mt-2">
            ⓘ 실제 API 호출은 Phase 3에서 연결됩니다. 지금은 결정·대기열 기록까지 가능.
          </p>
        </div>

        {Object.keys(proposal.evidence || {}).length > 0 && (
          <details className="mb-4">
            <summary className="text-xs text-slate-400 cursor-pointer hover:text-slate-200">
              근거 데이터 보기
            </summary>
            <pre className="text-[10px] bg-brand-bg/60 rounded p-2 mt-2 overflow-x-auto text-slate-300">
              {JSON.stringify(proposal.evidence, null, 2)}
            </pre>
          </details>
        )}

        {existingDecision && (
          <div className={`text-xs rounded p-2 mb-3 ${
            existingDecision.executed
              ? 'bg-sky-900/30 text-sky-300'
              : existingDecision.queued
              ? 'bg-amber-900/30 text-brand-warn'
              : existingDecision.decision === 'approve'
              ? 'bg-emerald-900/30 text-brand-success'
              : 'bg-rose-900/30 text-brand-danger'
          }`}>
            상태:{' '}
            <strong>
              {existingDecision.executed ? '실행 완료' :
               existingDecision.queued ? '실행 대기' :
               existingDecision.decision === 'approve' ? '승인됨' : '거절됨'}
            </strong>
            {' · '}{new Date(existingDecision.decided_at).toLocaleString('ko-KR')}
            {existingDecision.note && ` · "${existingDecision.note}"`}
            {existingDecision.execution_result && (
              <div className="mt-1 text-slate-300">
                {existingDecision.execution_result.message}
              </div>
            )}
          </div>
        )}

        <label className="block mb-3">
          <span className="text-xs text-slate-400">메모 (선택)</span>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            className="w-full mt-1 bg-brand-bg border border-brand-border rounded p-2 text-sm"
            placeholder="근거·제약·검토 의견"
            disabled={!!existingDecision?.executed}
          />
        </label>

        {error && <div className="text-xs text-brand-danger mb-2">⚠️ {error}</div>}

        <div className="flex items-center justify-end gap-2 flex-wrap">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="px-3 py-1.5 text-sm rounded border border-brand-border text-slate-300 hover:bg-brand-bg"
          >
            취소
          </button>
          <button
            type="button"
            onClick={() => submit('reject', false)}
            disabled={disabled}
            className="px-3 py-1.5 text-sm rounded border border-brand-danger text-brand-danger hover:bg-rose-900/30 disabled:opacity-50"
          >
            거절
          </button>
          <button
            type="button"
            onClick={() => submit('approve', false)}
            disabled={disabled}
            className="px-3 py-1.5 text-sm rounded border border-brand-success text-brand-success hover:bg-emerald-900/30 disabled:opacity-50"
          >
            승인만
          </button>
          <button
            type="button"
            onClick={() => submit('approve', true)}
            disabled={disabled}
            className="px-3 py-1.5 text-sm rounded bg-brand-primary text-brand-bg font-semibold hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? '저장 중…' : '승인 + 대기열 추가'}
          </button>
        </div>
        {existingDecision?.executed && (
          <p className="text-[10px] text-slate-500 text-right mt-2">
            이미 실행된 결정은 변경할 수 없습니다.
          </p>
        )}
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
      return (
        `지점: ${p.target}\n` +
        `현재 월 예산: ${cur.toLocaleString()}원\n` +
        `제안 월 예산: ${prop.toLocaleString()}원 (${sign}${delta.toLocaleString()}원)\n` +
        `API 호출: adgroup/update/ (해당 지점의 모든 광고그룹 대상)\n`
      );
    }
    case 'budget_reallocate': {
      const amount = Number(rec.amount || 0);
      return (
        `출처 (여유): ${rec.from}\n` +
        `대상 (부족): ${rec.to}\n` +
        `이관액: ${amount.toLocaleString()}원/월\n` +
        `API 호출: ${rec.from} adgroup 예산 -${amount.toLocaleString()} + ${rec.to} adgroup 예산 +${amount.toLocaleString()}\n`
      );
    }
    case 'pause_creative':
      return `소재: ${p.target}\n액션: 상태 DISABLE (중단)\nAPI 호출: ad/status/update/ (ad_name=${rec.ad_name})\n`;
    case 'scale_creative':
      return `소재: ${p.target}\n액션: 노출 비중 확대 (예산 증액 또는 타 adgroup 복제)\nAPI 호출: adgroup/update/ (budget) 또는 ad/create/ (복제)\n`;
    case 'reactivate_creative':
      return `소재: ${p.target}\n액션: 상태 ENABLE (재활성화)\nAPI 호출: ad/status/update/ (ad_name=${rec.ad_name})\n`;
    case 'creative_review':
      return `지점: ${rec.branch || p.target}\n액션: 해당 지점 전 소재 성과 리뷰 회의 필요\nAPI 호출 없음 (운영 의사결정 차원)\n`;
    case 'exclude_age':
    case 'expand_age':
      return `나이대: ${rec.age}\n액션: adgroup 타겟팅의 age 가중치 조정\nAPI 호출: adgroup/update/ (age 필드)\n`;
    case 'dayparting':
      return `시간대: ${rec.hour}시\n액션: 해당 시간대 송출 축소 (dayparting schedule)\nAPI 호출: adgroup/update/ (schedule_infos)\n`;
    case 'weekday_boost':
      return `요일: ${rec.weekday}\n액션: 해당 요일 송출 가중 (dayparting schedule)\nAPI 호출: adgroup/update/ (schedule_infos)\n`;
    case 'type_scale':
      return `소재 유형: ${rec.type}\n액션: 해당 유형 신규 소재 제작·확대\nAPI 호출 없음 (크리에이티브 기획)\n`;
    default:
      return JSON.stringify(rec, null, 2);
  }
}
