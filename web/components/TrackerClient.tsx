'use client';
import { useEffect, useMemo, useState } from 'react';
import { ActionProposal, BranchPaceData, ProposalsData, SegmentAnalysis } from '@/lib/reports';
import { BranchPaceCard } from './BranchPaceCard';
import { BranchTableView } from './BranchTableView';
import { ActionList } from './ActionList';
import { ActionDetailModal, DecisionRecord } from './ActionDetailModal';
import { ExecutionQueue } from './ExecutionQueue';
import { BranchDetailDrawer } from './BranchDetailDrawer';
import { AnalysisTabs } from './AnalysisTabs';
import { SectionNav, SectionDef } from './SectionNav';

type PaceView = 'cards' | 'table';

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
  const [paceView, setPaceView] = useState<PaceView>('cards');

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

  const queuedCount = decisions.filter((d) => d.queued && !d.executed).length;
  const daysRemaining = pace.days_total - pace.days_elapsed;

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
        <div className="flex items-baseline justify-between mb-4 flex-wrap gap-2">
          <h2 className="text-lg font-semibold text-fg tracking-tight flex items-center gap-2">
            지점 페이스
            <span className="text-2xs text-subtle font-normal">
              {paceView === 'cards' ? '카드 클릭 시 상세' : '행 클릭 시 상세'}
            </span>
          </h2>
          <div className="flex gap-0.5 p-0.5 bg-elevated rounded-lg">
            <button
              type="button"
              onClick={() => setPaceView('cards')}
              className={`px-2.5 py-1 text-xs font-medium rounded transition-all duration-150 ease-swift ${
                paceView === 'cards' ? 'bg-surface text-fg shadow-subtle' : 'text-muted hover:text-fg'
              }`}
            >
              카드
            </button>
            <button
              type="button"
              onClick={() => setPaceView('table')}
              className={`px-2.5 py-1 text-xs font-medium rounded transition-all duration-150 ease-swift ${
                paceView === 'table' ? 'bg-surface text-fg shadow-subtle' : 'text-muted hover:text-fg'
              }`}
            >
              테이블
            </button>
          </div>
        </div>
        {paceView === 'cards' ? (
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
        ) : (
          <BranchTableView
            branches={pace.branches}
            dateProgress={pace.date_progress}
            onSelect={(b) => setSelected(b)}
            selected={selected}
          />
        )}
      </section>

      <section id="sec-actions">
        <ActionList
          proposals={proposals.proposals}
          decisionMap={decisionMap}
          onClick={(p) => setModalProposal(p)}
        />
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
          daysRemaining={daysRemaining}
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
