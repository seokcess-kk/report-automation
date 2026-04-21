'use client';
import { useEffect } from 'react';
import { ActionProposal, BranchPace } from '@/lib/reports';
import { ActionCard } from './ActionCard';
import { fmtMan } from '@/lib/format';
import { DecisionRecord } from './ActionDetailModal';
import { Badge, Stat, StatusDot } from './ui';
import { cn } from './ui/cn';
import { useFocusTrap } from './ui/useFocusTrap';

const TIER_COLOR: Record<string, string> = {
  TIER1: 'bg-success',
  TIER2: 'bg-info',
  TIER3: 'bg-warn',
  TIER4: 'bg-danger',
  LOW_VOLUME: 'bg-border-strong',
  UNCLASSIFIED: 'bg-muted',
};

const STATUS_META: Record<string, { label: string; tone: 'success' | 'warn' | 'danger' }> = {
  ok: { label: '정상', tone: 'success' },
  warn: { label: '주의', tone: 'warn' },
  danger: { label: '경고', tone: 'danger' },
};

export function BranchDetailDrawer({
  branch, proposals, decisions, daysRemaining, onClose, onActionClick,
}: {
  branch: BranchPace;
  proposals: ActionProposal[];
  decisions: DecisionRecord[];
  daysRemaining: number;
  onClose: () => void;
  onActionClick: (p: ActionProposal) => void;
}) {
  const trapRef = useFocusTrap<HTMLElement>(true);
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
  const meta = STATUS_META[branch.status];

  // 시뮬레이터
  const convRemaining = Math.max(branch.conv_target - branch.conv_so_far, 0);
  const dailyNeeded = daysRemaining > 0 ? convRemaining / daysRemaining : 0;
  const costNeeded = branch.cpa != null ? dailyNeeded * branch.cpa : null;
  const budgetRemaining = Math.max(branch.budget - branch.cost_so_far, 0);
  const budgetCanSupport = branch.cpa && branch.cpa > 0 ? budgetRemaining / branch.cpa : Infinity;
  const simStatus: 'ok' | 'tight' | 'impossible' =
    convRemaining === 0 ? 'ok'
      : budgetCanSupport >= convRemaining ? 'ok'
      : budgetCanSupport >= convRemaining * 0.8 ? 'tight'
      : 'impossible';
  const simTone: 'success' | 'warn' | 'danger' =
    simStatus === 'ok' ? 'success' : simStatus === 'tight' ? 'warn' : 'danger';
  const simLabel = simStatus === 'ok' ? '달성 가능' : simStatus === 'tight' ? '빠듯함' : '예산 부족';

  const tierDist = branch.tier_distribution || {};
  const tierTotal = Object.values(tierDist).reduce((a, b) => a + b, 0);
  const tierOrder = ['TIER1', 'TIER2', 'TIER3', 'TIER4', 'LOW_VOLUME', 'UNCLASSIFIED'];
  const tierEntries = tierOrder.filter((k) => tierDist[k] > 0).map((k) => [k, tierDist[k]] as const);

  return (
    <div className="fixed inset-0 z-40 animate-fade-in" onClick={onClose} role="dialog" aria-modal="true" aria-label={`${branch.branch} 상세`}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <aside
        ref={trapRef as React.RefObject<HTMLElement>}
        className="absolute right-0 top-0 bottom-0 w-full sm:w-[480px] bg-surface border-l border-border shadow-drawer overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-surface/95 backdrop-blur border-b border-border px-5 py-3 flex items-center justify-between z-10">
          <div className="flex items-center gap-2.5">
            <StatusDot status={branch.status as any} size="lg" />
            <h2 className="text-lg font-semibold text-fg tracking-tight">{branch.branch}</h2>
            <Badge tone={meta.tone}>{meta.label}</Badge>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-md text-muted hover:text-fg hover:bg-elevated transition-colors"
            aria-label="닫기"
          >
            ✕
          </button>
        </div>

        <div className="p-5 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <Stat
              label="누적 비용"
              value={fmtMan(branch.cost_so_far) + '원'}
              sub={`예산 ${fmtMan(branch.budget)}원 (${branch.budget_pct}%)`}
            />
            <Stat
              label="누적 전환"
              value={`${branch.conv_so_far}건`}
              sub={`목표 ${branch.conv_target}건 (${branch.conv_pct}%)`}
            />
            <Stat
              label="CPA"
              value={branch.cpa != null ? branch.cpa.toLocaleString() + '원' : '-'}
              sub={`목표 ${branch.target_cpa.toLocaleString()}원`}
            />
            <Stat
              label="월말 예상"
              value={`${branch.proj_conv}건`}
              sub={`달성 ${branch.proj_pct}%`}
            />
          </div>

          <div className="grid grid-cols-3 gap-2 text-xs">
            <InfoBox label="노출" value={branch.impressions.toLocaleString()} />
            <InfoBox label="클릭" value={branch.clicks.toLocaleString()} />
            <InfoBox label="CTR" value={ctr} />
          </div>

          {convRemaining > 0 && (
            <section className="border-t border-border pt-4">
              <div className="flex items-center gap-2 mb-3">
                <h3 className="text-sm font-semibold text-fg">목표 달성 시뮬레이터</h3>
                <Badge tone={simTone}>{simLabel}</Badge>
              </div>
              <div className="bg-elevated/50 border border-border rounded-lg p-4 space-y-2 text-sm">
                <div className="text-muted">
                  남은 <span className="font-semibold text-fg tabular-nums">{daysRemaining}일</span>간{' '}
                  <span className="font-semibold text-fg tabular-nums">{convRemaining}건</span> 전환 필요
                </div>
                <div className="text-fg">
                  → 일평균 <span className="text-accent-strong font-semibold tabular-nums">{dailyNeeded.toFixed(1)}건</span> 필요
                </div>
                {costNeeded != null && (
                  <div className="text-xs text-muted">
                    (현재 CPA 유지 시 일일 {fmtMan(costNeeded)}원 지출 예상)
                  </div>
                )}
                <div className="pt-2 mt-1 border-t border-border text-xs text-muted">
                  잔여 예산 <span className="font-mono tabular-nums">{fmtMan(budgetRemaining)}원</span>
                  {branch.cpa && ` · 현재 CPA로 최대 ${Math.floor(budgetCanSupport)}건 가능`}
                </div>
              </div>
            </section>
          )}

          {tierTotal > 0 && (
            <section className="border-t border-border pt-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-fg">소재 TIER 분포</h3>
                <span className="text-2xs text-subtle tabular-nums">{tierTotal}개</span>
              </div>
              <div className="flex w-full h-1.5 rounded-full overflow-hidden mb-3">
                {tierEntries.map(([tier, cnt]) => (
                  <div
                    key={tier}
                    className={cn('transition-all', TIER_COLOR[tier] || 'bg-muted')}
                    style={{ width: `${(cnt / tierTotal) * 100}%` }}
                    title={`${tier}: ${cnt}개`}
                  />
                ))}
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
                {tierEntries.map(([tier, cnt]) => (
                  <div key={tier} className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <span className={cn('w-2 h-2 rounded-full', TIER_COLOR[tier] || 'bg-muted')} />
                      <span className="text-fg">{tier}</span>
                    </span>
                    <span className="tabular-nums text-muted">{cnt}개 · {((cnt / tierTotal) * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className="border-t border-border pt-4">
            <div className="flex items-center gap-2 mb-3">
              <h3 className="text-sm font-semibold text-fg">관련 액션</h3>
              <Badge tone="neutral">{proposals.length}</Badge>
            </div>
            {proposals.length > 0 ? (
              <ul className="space-y-2">
                {proposals.map((p) => (
                  <ActionCard key={p.id} p={p} decisionStatus={statusOf(p)} onClick={() => onActionClick(p)} />
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">이 지점에 대한 제안이 없습니다.</p>
            )}
          </section>
        </div>
      </aside>
    </div>
  );
}

function InfoBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between bg-elevated/40 border border-border rounded px-3 py-2">
      <span className="text-subtle">{label}</span>
      <span className="font-mono text-fg tabular-nums">{value}</span>
    </div>
  );
}
