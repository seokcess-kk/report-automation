'use client';
import { useEffect } from 'react';
import { ActionProposal, BranchPace } from '@/lib/reports';
import { ActionCard } from './ActionCard';
import { fmtMan } from '@/lib/format';
import { DecisionRecord } from './ActionDetailModal';

export function BranchDetailDrawer({
  branch,
  proposals,
  decisions,
  onClose,
  onActionClick,
}: {
  branch: BranchPace;
  proposals: ActionProposal[];
  decisions: DecisionRecord[];
  onClose: () => void;
  onActionClick: (p: ActionProposal) => void;
}) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [onClose]);

  function statusOf(p: ActionProposal): 'approved' | 'queued' | 'executed' | 'rejected' | null {
    const d = decisions.find((x) => x.proposal_id === p.id);
    if (!d) return null;
    if (d.decision === 'reject') return 'rejected';
    if (d.executed) return 'executed';
    if (d.queued) return 'queued';
    return 'approved';
  }

  const ctr = branch.impressions > 0 ? ((branch.clicks / branch.impressions) * 100).toFixed(2) + '%' : '-';

  return (
    <div className="fixed inset-0 z-40" onClick={onClose}>
      <div className="absolute inset-0 bg-black/50" />
      <aside
        className="absolute right-0 top-0 bottom-0 w-full sm:w-[480px] bg-brand-card border-l border-brand-border shadow-2xl overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-brand-card border-b border-brand-border p-4 flex items-center justify-between z-10">
          <h2 className="text-lg font-semibold">{branch.branch} 상세</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-white text-lg leading-none"
          >
            ✕
          </button>
        </div>

        <div className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-2">
            <DetailStat label="누적 비용" value={fmtMan(branch.cost_so_far) + '원'} sub={`예산 ${fmtMan(branch.budget)}원 (${branch.budget_pct}%)`} />
            <DetailStat label="누적 전환" value={`${branch.conv_so_far}건`} sub={`목표 ${branch.conv_target}건 (${branch.conv_pct}%)`} />
            <DetailStat
              label="CPA"
              value={branch.cpa != null ? branch.cpa.toLocaleString() + '원' : '-'}
              sub={`목표 ${branch.target_cpa.toLocaleString()}원`}
            />
            <DetailStat label="월말 예상" value={`${branch.proj_conv}건`} sub={`달성 ${branch.proj_pct}%`} />
          </div>

          <div className="grid grid-cols-3 gap-2 text-xs">
            <InfoBox label="노출" value={branch.impressions.toLocaleString()} />
            <InfoBox label="클릭" value={branch.clicks.toLocaleString()} />
            <InfoBox label="CTR" value={ctr} />
          </div>

          <div className="border-t border-brand-border pt-3">
            <h3 className="text-sm font-semibold mb-2">
              관련 액션 ({proposals.length})
            </h3>
            {proposals.length > 0 ? (
              <ul className="space-y-2">
                {proposals.map((p) => (
                  <ActionCard
                    key={p.id}
                    p={p}
                    decisionStatus={statusOf(p)}
                    onClick={() => onActionClick(p)}
                  />
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">이 지점에 대한 제안이 없습니다.</p>
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}

function DetailStat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-brand-bg/60 rounded p-3">
      <div className="text-xs text-slate-400 mb-1">{label}</div>
      <div className="text-base font-bold">{value}</div>
      {sub && <div className="text-[10px] text-slate-500 mt-1">{sub}</div>}
    </div>
  );
}

function InfoBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between bg-brand-bg/40 rounded px-2 py-1.5">
      <span className="text-slate-400">{label}</span>
      <span className="font-mono text-slate-200">{value}</span>
    </div>
  );
}
