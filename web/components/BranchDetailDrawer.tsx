'use client';
import { useEffect } from 'react';
import { ActionProposal, BranchPace } from '@/lib/reports';
import { ActionCard } from './ActionCard';
import { fmtMan } from '@/lib/format';
import { DecisionRecord } from './ActionDetailModal';

const TIER_COLOR: Record<string, string> = {
  TIER1: 'bg-brand-success',
  TIER2: 'bg-sky-500',
  TIER3: 'bg-brand-warn',
  TIER4: 'bg-brand-danger',
  LOW_VOLUME: 'bg-slate-600',
  UNCLASSIFIED: 'bg-slate-500',
};

export function BranchDetailDrawer({
  branch,
  proposals,
  decisions,
  daysRemaining,
  onClose,
  onActionClick,
}: {
  branch: BranchPace;
  proposals: ActionProposal[];
  decisions: DecisionRecord[];
  daysRemaining: number;
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

  // 시뮬레이터: 남은 전환 / 남은 일수
  const convRemaining = Math.max(branch.conv_target - branch.conv_so_far, 0);
  const dailyNeeded = daysRemaining > 0 ? convRemaining / daysRemaining : 0;
  const costNeeded = branch.cpa != null ? dailyNeeded * branch.cpa : null;
  const budgetRemaining = Math.max(branch.budget - branch.cost_so_far, 0);
  const budgetCanSupport = branch.cpa && branch.cpa > 0 ? budgetRemaining / branch.cpa : Infinity;
  const simulationStatus: 'ok' | 'tight' | 'impossible' =
    convRemaining === 0
      ? 'ok'
      : budgetCanSupport >= convRemaining
      ? 'ok'
      : budgetCanSupport >= convRemaining * 0.8
      ? 'tight'
      : 'impossible';

  const tierDist = branch.tier_distribution || {};
  const tierTotal = Object.values(tierDist).reduce((a, b) => a + b, 0);
  const tierOrder = ['TIER1', 'TIER2', 'TIER3', 'TIER4', 'LOW_VOLUME', 'UNCLASSIFIED'];
  const tierEntries = tierOrder.filter((k) => tierDist[k] > 0).map((k) => [k, tierDist[k]] as const);

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

          {convRemaining > 0 && (
            <div className="border-t border-brand-border pt-3">
              <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                목표 달성 시뮬레이터
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                  simulationStatus === 'ok'
                    ? 'bg-emerald-900/50 text-brand-success'
                    : simulationStatus === 'tight'
                    ? 'bg-amber-900/50 text-brand-warn'
                    : 'bg-rose-900/50 text-brand-danger'
                }`}>
                  {simulationStatus === 'ok' ? '달성 가능' : simulationStatus === 'tight' ? '빠듯함' : '예산 부족'}
                </span>
              </h3>
              <div className="text-xs text-slate-300 space-y-1 bg-brand-bg/40 rounded p-3">
                <div>
                  남은 <span className="font-bold text-slate-100">{daysRemaining}일</span>간{' '}
                  <span className="font-bold text-slate-100">{convRemaining}건</span> 전환 필요
                </div>
                <div>
                  → 일평균 <span className="font-bold text-brand-primary">{dailyNeeded.toFixed(1)}건</span> 필요
                </div>
                {costNeeded != null && (
                  <div className="text-slate-400">
                    (현재 CPA 유지 시 일일 {fmtMan(costNeeded)}원 지출 예상)
                  </div>
                )}
                <div className="text-slate-400 pt-1 border-t border-brand-border/50 mt-1">
                  잔여 예산 <span className="font-mono">{fmtMan(budgetRemaining)}원</span>
                  {branch.cpa && ` · 현재 CPA로 최대 ${Math.floor(budgetCanSupport)}건 가능`}
                </div>
              </div>
            </div>
          )}

          {tierTotal > 0 && (
            <div className="border-t border-brand-border pt-3">
              <h3 className="text-sm font-semibold mb-2">소재 TIER 분포 <span className="text-xs text-slate-500 font-normal">({tierTotal}개)</span></h3>
              <div className="flex w-full h-2 rounded overflow-hidden mb-2">
                {tierEntries.map(([tier, cnt]) => (
                  <div
                    key={tier}
                    className={`${TIER_COLOR[tier] || 'bg-slate-500'}`}
                    style={{ width: `${(cnt / tierTotal) * 100}%` }}
                    title={`${tier}: ${cnt}개`}
                  />
                ))}
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                {tierEntries.map(([tier, cnt]) => (
                  <div key={tier} className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${TIER_COLOR[tier] || 'bg-slate-500'}`} />
                      <span className="text-slate-300">{tier}</span>
                    </span>
                    <span className="font-mono text-slate-400">{cnt}개 · {((cnt / tierTotal) * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

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
