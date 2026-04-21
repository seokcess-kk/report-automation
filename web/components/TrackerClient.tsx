'use client';
import { useEffect, useState } from 'react';
import { ActionProposal, BranchPaceData, ProposalsData } from '@/lib/reports';
import { BranchPaceCard } from './BranchPaceCard';
import { ActionCard } from './ActionCard';
import { ActionDetailModal, DecisionRecord } from './ActionDetailModal';
import { ExecutionQueue } from './ExecutionQueue';
import { fmtMan } from '@/lib/format';

type Decision = DecisionRecord;

export function TrackerClient({ pace, proposals }: { pace: BranchPaceData; proposals: ProposalsData }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [modalProposal, setModalProposal] = useState<ActionProposal | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);

  useEffect(() => {
    fetch('/api/actions/decisions')
      .then((r) => r.json())
      .then((j) => setDecisions(j.decisions || []))
      .catch(() => setDecisions([]));
  }, []);

  const decisionMap = new Map<string, Decision>();
  for (const d of decisions) {
    decisionMap.set(d.proposal_id, d);
  }

  function statusOf(p: ActionProposal): 'approved' | 'queued' | 'executed' | 'rejected' | null {
    const d = decisionMap.get(p.id);
    if (!d) return null;
    if (d.decision === 'reject') return 'rejected';
    if (d.executed) return 'executed';
    if (d.queued) return 'queued';
    return 'approved';
  }

  function handleDecided(newDecision: Decision) {
    setDecisions((prev) => {
      const filtered = prev.filter((d) => d.proposal_id !== newDecision.proposal_id);
      return [...filtered, newDecision];
    });
    setModalProposal(null);
  }

  function handleExecuted(updated: Decision) {
    setDecisions((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
  }

  const focused = selected ? pace.branches.find((b) => b.branch === selected) : null;
  const focusedProposals = selected
    ? proposals.proposals.filter((p) => p.target === selected || p.target.startsWith(`${selected}→`))
    : [];

  const top5 = proposals.proposals.slice(0, 5);

  return (
    <>
      <section>
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
          지점 페이스
          <span className="text-xs text-slate-500 font-normal">카드 클릭 시 상세 보기</span>
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

      <section>
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

      {focused && (
        <section className="card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">{focused.branch} 상세</h2>
            <button
              type="button"
              onClick={() => setSelected(null)}
              className="text-xs text-slate-400 hover:text-white"
            >
              닫기 ✕
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <DetailStat label="누적 비용" value={fmtMan(focused.cost_so_far) + '원'} sub={`예산 ${fmtMan(focused.budget)}원`} />
            <DetailStat label="누적 전환" value={`${focused.conv_so_far}건`} sub={`목표 ${focused.conv_target}건`} />
            <DetailStat label="CPA" value={focused.cpa != null ? focused.cpa.toLocaleString() + '원' : '-'} sub={`목표 ${focused.target_cpa.toLocaleString()}원`} />
            <DetailStat label="월말 예상" value={`${focused.proj_conv}건`} sub={`달성 ${focused.proj_pct}%`} />
          </div>
          <div className="grid grid-cols-3 gap-3 text-sm mb-4">
            <InfoBox label="노출" value={focused.impressions.toLocaleString()} />
            <InfoBox label="클릭" value={focused.clicks.toLocaleString()} />
            <InfoBox label="CTR" value={focused.impressions > 0 ? ((focused.clicks / focused.impressions) * 100).toFixed(2) + '%' : '-'} />
          </div>

          <div className="border-t border-brand-border pt-3">
            <h3 className="text-sm font-semibold mb-2">
              {focused.branch} 관련 액션 ({focusedProposals.length})
            </h3>
            {focusedProposals.length > 0 ? (
              <ul className="space-y-2">
                {focusedProposals.map((p) => (
                  <ActionCard
                    key={p.id}
                    p={p}
                    decisionStatus={statusOf(p)}
                    onClick={() => setModalProposal(p)}
                  />
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">현재 이 지점에 대한 제안이 없습니다.</p>
            )}
          </div>
        </section>
      )}

      <ExecutionQueue decisions={decisions} onExecuted={handleExecuted} />

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

function DetailStat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-brand-bg/60 rounded p-3">
      <div className="text-xs text-slate-400 mb-1">{label}</div>
      <div className="text-lg font-bold">{value}</div>
      {sub && <div className="text-[10px] text-slate-500 mt-1">{sub}</div>}
    </div>
  );
}

function InfoBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between bg-brand-bg/40 rounded px-3 py-2">
      <span className="text-xs text-slate-400">{label}</span>
      <span className="font-mono text-sm text-slate-200">{value}</span>
    </div>
  );
}
