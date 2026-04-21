import { BranchPaceData } from '@/lib/reports';
import { fmtMan } from '@/lib/format';
import { InfoTip } from './InfoTip';

const STATUS_EXPLAIN = `신호등 기준
🟢 정상: 전환 페이스 ≥ 일자 진행률, 예산 여유
🟡 주의: 전환 5%p 지연 또는 예산 10%p 초과
🔴 경고: 전환 15%p+ 지연 또는 예산 20%p+ 초과`;

const STATUS_META: Record<string, { label: string; color: string; bg: string }> = {
  ok: { label: '정상', color: 'text-brand-success', bg: 'bg-emerald-900/30' },
  warn: { label: '주의', color: 'text-brand-warn', bg: 'bg-amber-900/30' },
  danger: { label: '경고', color: 'text-brand-danger', bg: 'bg-rose-900/30' },
};

export function PaceHeader({ pace }: { pace: BranchPaceData }) {
  const { overall, date_progress, days_elapsed, days_total, month, updated } = pace;
  const meta = STATUS_META[overall.status];

  return (
    <section className={`card ${meta.bg} border-l-4 ${meta.color.replace('text-', 'border-')}`}>
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="text-xs text-slate-400 mb-1">{month} 월간 진행 현황 · 업데이트 {updated}</div>
          <h1 className="text-2xl font-bold">
            목표 달성 트래커
            <span className={`ml-3 text-sm font-medium px-2 py-0.5 rounded ${meta.color} ${meta.bg}`}>
              {meta.label}
            </span>
            <span className="ml-2 align-middle">
              <InfoTip text={STATUS_EXPLAIN} />
            </span>
          </h1>
        </div>
        <div className="text-right text-sm text-slate-400">
          <div>{days_elapsed} / {days_total}일 경과</div>
          <div className="font-bold text-slate-200">{date_progress}%</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
          sub={`${overall.proj_conv}건 예상 (목표 대비 ${overall.proj_pct}%)`}
          tip="현재 일평균을 남은 일수에 곱한 단순 외삽 예측. 월초엔 노이즈 크므로 참고용."
        />
      </div>
    </section>
  );
}

function PaceBar({
  label,
  pct,
  target,
  sub,
  invert = false,
  tip,
}: {
  label: string;
  pct: number;
  target: number;
  sub: string;
  invert?: boolean;
  tip?: string;
}) {
  const gap = pct - target;
  const good = invert ? gap <= 5 : gap >= -5;
  const barColor = good ? 'bg-brand-success' : gap >= (invert ? 15 : -15) && gap <= (invert ? -15 : 15) ? 'bg-brand-warn' : 'bg-brand-danger';
  const width = Math.min(Math.max(pct, 0), 100);

  return (
    <div>
      <div className="flex items-baseline justify-between text-sm mb-1">
        <span className="text-slate-300 flex items-center gap-1">
          {label}
          {tip && <InfoTip text={tip} />}
        </span>
        <span className="font-bold text-slate-100">{pct.toFixed(1)}%</span>
      </div>
      <div className="h-2 bg-brand-bg rounded overflow-hidden relative">
        <div className={`h-full ${barColor}`} style={{ width: `${width}%` }} />
        <div
          className="absolute top-0 h-full w-0.5 bg-slate-400"
          style={{ left: `${Math.min(target, 100)}%` }}
          title={`일자 진행률 ${target}%`}
        />
      </div>
      <div className="text-xs text-slate-400 mt-1">{sub}</div>
    </div>
  );
}
