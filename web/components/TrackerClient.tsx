'use client';
import { useEffect, useMemo, useState } from 'react';
import { ActionProposal, BranchPaceData, ProposalsData, SegmentAnalysis } from '@/lib/reports';
import { BranchPaceCard } from './BranchPaceCard';
import { ActionCard } from './ActionCard';
import { ActionDetailModal, DecisionRecord } from './ActionDetailModal';
import { ExecutionQueue } from './ExecutionQueue';
import { BranchDetailDrawer } from './BranchDetailDrawer';
import { AnalysisTabs } from './AnalysisTabs';
import { SectionNav, SectionDef } from './SectionNav';

export function TrackerClient({
  pace,
  proposals,
  segments,
}: {
  pace: BranchPaceData;
  proposals: ProposalsData;
  segments: SegmentAnalysis | null;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const [modalProposal, setModalProposal] = useState<ActionProposal | null>(null);
  const [decisions, setDecisions] = useState<DecisionRecord[]>([]);

  useEffect(() => {
    fetch('/api/actions/decisions')
      .then((r) => r.json())
      .then((j) => setDecisions(j.decisions || []))
      .catch(() => setDecisions([]));
  }, []);

  const decisionMap = useMemo(() => {
    const m = new Map<string, DecisionRecord>();
    for (const d of decisions) m.set(d.proposal_id, d);
    return m;
  }, [decisions]);

  function statusOf(p: ActionProposal): 'approved' | 'queued' | 'executed' | 'rejected' | null {
    const d = decisionMap.get(p.id);
    if (!d) return null;
    if (d.decision === 'reject') return 'rejected';
    if (d.executed) return 'executed';
    if (d.queued) return 'queued';
    return 'approved';
  }

  function handleDecided(newDecision: DecisionRecord) {
    setDecisions((prev) => {
      const filtered = prev.filter((d) => d.proposal_id !== newDecision.proposal_id);
      return [...filtered, newDecision];
    });
    setModalProposal(null);
  }

  function handleExecuted(updated: DecisionRecord) {
    setDecisions((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
  }

  const focused = selected ? pace.branches.find((b) => b.branch === selected) : null;
  const focusedProposals = selected
    ? proposals.proposals.filter((p) => p.target === selected || p.target.startsWith(`${selected}→`))
    : [];

  const top5 = proposals.proposals.slice(0, 5);
  const queuedCount = decisions.filter((d) => d.queued && !d.executed).length;

  const sections: SectionDef[] = [
    { id: 'sec-pace', label: '페이스' },
    { id: 'sec-actions', label: '액션', count: proposals.summary.total },
    { id: 'sec-queue', label: '실행', count: queuedCount },
  ];
  if (segments) sections.push({ id: 'sec-analysis', label: '분석' });

  return (
    <>
      <SectionNav sections={sections} />

      <section id="sec-pace">
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
          지점 페이스
          <span className="text-xs text-slate-500 font-normal">카드 클릭 시 상세</span>
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {pace.branches.map((b) => (
            <BranchPaceCard
              key={b.branch}
              b={b}
              dateProgress={pace.date_progress}
              selected={selected === b.branch}
              onClick={() => setSelected(selected === b.branch ? null : b.branch)}
            />
          ))}
        </div>
      </section>

      <section id="sec-actions">
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-lg font-semibold">오늘의 액션 Top 5</h2>
          <span className="text-xs text-slate-500">
            총 {proposals.summary.total}건 · 긴급 {proposals.summary.high} · 권장 {proposals.summary.medium}
            {decisions.length > 0 && ` · 결정 ${decisions.length}건`}
          </span>
        </div>
        {top5.length > 0 ? (
          <ul className="space-y-2">
            {top5.map((p) => (
              <ActionCard
                key={p.id}
                p={p}
                decisionStatus={statusOf(p)}
                onClick={() => setModalProposal(p)}
              />
            ))}
          </ul>
        ) : (
          <div className="card text-sm text-slate-400 text-center py-6">
            현재 규칙 기준으로 제안 가능한 액션이 없습니다.
          </div>
        )}
      </section>

      <section id="sec-queue">
        <ExecutionQueue decisions={decisions} onExecuted={handleExecuted} />
      </section>

      {segments && (
        <section id="sec-analysis">
          <AnalysisTabs segments={segments} />
        </section>
      )}

      {focused && (
        <BranchDetailDrawer
          branch={focused}
          proposals={focusedProposals}
          decisions={decisions}
          onClose={() => setSelected(null)}
          onActionClick={(p) => setModalProposal(p)}
        />
      )}

      {modalProposal && (
        <ActionDetailModal
          proposal={modalProposal}
          existingDecision={decisionMap.get(modalProposal.id) || null}
          onClose={() => setModalProposal(null)}
          onDecided={handleDecided}
        />
      )}
    </>
  );
}
