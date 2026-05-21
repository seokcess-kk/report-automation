import Link from 'next/link';
import { loadJuneStatus } from '@/lib/june-status';
import { Card, Badge, Stat } from '@/components/ui';
import { fmt, fmtMan } from '@/lib/format';

export const dynamic = 'force-dynamic';

export default async function JuneStatusPage() {
  const data = await loadJuneStatus();

  const findings = [
    { key: 'addon', label: '애드온 / 디자인 변경', text: data.key_findings.addon },
    { key: 'targeting_health', label: '성별·연령 타겟팅', text: data.key_findings.targeting_health },
    { key: 'geo_leakage', label: '지역 도달 정합성', text: data.key_findings.geo_leakage },
  ].filter((f) => f.text);

  return (
    <div className="space-y-8 animate-fade-in">
      <section>
        <div className="flex items-baseline justify-between flex-wrap gap-2">
          <h1 className="text-2xl font-bold text-fg tracking-tight">6월 운영 현황</h1>
          <span className="text-xs text-subtle tabular-nums">
            {data.proposal_meta?.data_period || '데이터 기간 미상'}
          </span>
        </div>
        <p className="text-sm text-muted mt-2">
          제안서 핵심 결론 + 운영 활동 요약. 실시간 KPI·이상 신호·체크리스트는 대행사 운영 콘솔에서 확인합니다.
        </p>
      </section>

      {/* 헤드라인 KPI 목표 */}
      <section className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <Card variant="default">
          <Stat
            label="6월 전환 목표 (기본)"
            value={fmt(data.headline.target_base, '건')}
          />
        </Card>
        <Card variant="default">
          <Stat
            label="6월 전환 목표 (상향)"
            value={fmt(data.headline.target_stretch, '건')}
          />
        </Card>
        <Card variant="default">
          <Stat
            label="평균 CPA 가드레일"
            value={fmt(data.headline.target_cpa, '원')}
          />
        </Card>
      </section>

      <Card variant="default" className="p-5">
        <p className="text-xs text-subtle">{data.headline.pace_caveat}</p>
      </Card>

      {/* 제안서 핵심 결론 */}
      {findings.length > 0 && (
        <Card variant="default" className="p-5">
          <h2 className="text-base font-semibold text-fg mb-4">6월 운영안 핵심 결론</h2>
          <ul className="space-y-4">
            {findings.map((f) => (
              <li key={f.key} className="border-l-2 pl-3 border-accent">
                <div className="text-sm font-medium mb-1 text-accent">{f.label}</div>
                <p className="text-sm text-muted leading-relaxed">{f.text}</p>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* 액션 활동 요약 */}
      <Card variant="default" className="p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-fg">운영 활동 요약</h2>
          <div className="flex gap-2">
            <Badge tone="neutral">전체 {data.action_stats.total}건</Badge>
            <Badge tone="info">최근 7일 {data.action_stats.last_7_days}건</Badge>
          </div>
        </div>

        {data.action_stats.by_type.length > 0 && (
          <div className="mb-4">
            <div className="text-xs text-subtle mb-2">유형별 분포</div>
            <div className="flex flex-wrap gap-2">
              {data.action_stats.by_type.map((t) => (
                <Badge key={t.type} tone="default">
                  {t.type}: {t.count}건
                </Badge>
              ))}
            </div>
          </div>
        )}

        {data.recent_actions.length > 0 ? (
          <div>
            <div className="text-xs text-subtle mb-2">최근 액션 (최대 20건)</div>
            <ul className="divide-y divide-border">
              {data.recent_actions.map((a, i) => (
                <li key={i} className="py-2 text-sm">
                  <div className="flex items-baseline gap-2 mb-0.5">
                    <span className="text-2xs text-subtle tabular-nums">{a.date}</span>
                    <span className="text-fg font-medium">{a.action_type}</span>
                    {a.branch && <span className="text-muted">· {a.branch}</span>}
                  </div>
                  {a.before && a.after && (
                    <div className="text-2xs text-muted ml-12">
                      {a.before} → {a.after}
                    </div>
                  )}
                  <div className="text-2xs text-subtle ml-12 italic">사유: {a.reason}</div>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-sm text-muted italic">기록된 액션 없음</p>
        )}
      </Card>

      <div className="text-right">
        <Link
          href={data.proposal_url}
          className="inline-flex items-center gap-1 text-sm text-accent hover:text-accent-strong font-medium"
        >
          제안서 원문 →
        </Link>
      </div>
    </div>
  );
}
