import { BranchPaceData } from '@/lib/reports';
import { fmtMan } from '@/lib/format';
import { InfoTip } from './InfoTip';
import { Badge, Card, StatusDot } from './ui';
import { cn } from './ui/cn';

const STATUS_META: Record<string, { label: string; tone: 'success' | 'warn' | 'danger' }> = {
  ok: { label: '정상', tone: 'success' },
  warn: { label: '주의', tone: 'warn' },
  danger: { label: '경고', tone: 'danger' },
};

const STATUS_EXPLAIN = `신호등 기준
정상: 전환 페이스 ≥ 일자 진행률, 예산 여유
주의: 전환 5%p 지연 또는 예산 10%p 초과
경고: 전환 15%p+ 지연 또는 예산 20%p+ 초과`;

export function PaceHeader({ pace }: { pace: BranchPaceData }) {
  const { overall, date_progress, days_elapsed, days_total, month, updated } = pace;
  const meta = STATUS_META[overall.status];

  return (
    <Card variant="raised" className="p-6 animate-fade-in">
      <div className="flex items-start justify-between mb-6 gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 text-2xs text-subtle uppercase tracking-wider mb-1">
            <span>{month} 월간 진행</span>
            <span className="text-border-strong">·</span>
            <span>업데이트 {updated}</span>
          </div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-fg tracking-tight">목표 달성 트래커</h1>
            <Badge tone={meta.tone} className="text-xs">
              <StatusDot status={overall.status as any} size="sm" />
              {meta.label}
            </Badge>
            <InfoTip text={STATUS_EXPLAIN} />
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xs text-subtle uppercase tracking-wider">경과</div>
          <div className="text-2xl font-semibold text-fg tabular-nums">{date_progress}%</div>
          <div className="text-xs text-muted tabular-nums">{days_elapsed} / {days_total}일</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <PaceBar
          label="예산 소진"
          pct={overall.budget_pct}
          target={date_progress}
          sub={`${fmtMan(overall.cost_so_far)} / ${fmtMan(overall.budget_total)}원`}
          invert
        />
        <PaceBar
          label="전환 달성"
          pct={overall.conv_pct}
          target={date_progress}
          sub={`${overall.conv_so_far} / ${overall.conv_target}건`}
        />
        <PaceBar
          label="월말 예상 전환"
          pct={overall.proj_pct}
          target={100}
          sub={`${overall.proj_conv}건 예상 (목표 ${overall.proj_pct}%)`}
          tip="현재 일평균을 남은 일수에 곱한 단순 외삽 예측. 월초엔 노이즈 크므로 참고용."
        />
      </div>
    </Card>
  );
}

function PaceBar({
  label, pct, target, sub, invert = false, tip,
}: {
  label: string; pct: number; target: number; sub: string; invert?: boolean; tip?: string;
}) {
  const gap = pct - target;
  const good = invert ? gap <= 5 : gap >= -5;
  const mid = invert ? gap <= 15 : gap >= -15;
  const barClass = good ? 'bg-success' : mid ? 'bg-warn' : 'bg-danger';
  const width = Math.min(Math.max(pct, 0), 100);

  return (
    <div className="min-w-0">
      <div className="flex items-baseline justify-between mb-2">
        <span className="text-xs text-muted flex items-center gap-1">
          {label}
          {tip && <InfoTip text={tip} />}
        </span>
        <span className="text-lg font-semibold text-fg tabular-nums">{pct.toFixed(1)}%</span>
      </div>
      <div className="relative h-1.5 bg-elevated rounded-full overflow-hidden">
        <div
          className={cn('absolute inset-y-0 left-0 rounded-full transition-all duration-300 ease-swift', barClass)}
          style={{ width: `${width}%` }}
        />
        <div
          className="absolute top-0 h-full w-px bg-fg/40"
          style={{ left: `${Math.min(target, 100)}%` }}
          title={`일자 진행률 ${target}%`}
        />
      </div>
      <div className="text-2xs text-subtle mt-1.5 tabular-nums">{sub}</div>
    </div>
  );
}
