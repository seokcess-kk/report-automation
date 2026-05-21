/** 6월 운영 현황 데이터 로더 — 클라이언트 보고용
 *
 * 빌드 타임에 다음 자산을 읽어 클라이언트 친화적 형태로 가공:
 *   - output/proposal/202606/proposal_daeat_202606.json (6월 운영 제안서)
 *   - output/data/<latest>/parsed.parquet은 빌드 타임 변환 어려움 — JSON 산출물 우선
 *   - output/tracker/actions.jsonl (액션 활동 로그)
 *   - config/june_checklist.yaml 은 별도 파싱 필요 (yaml 패키지)
 *
 * Phase 3 MVP: 제안서 + 액션 로그 기반 요약 화면만 노출.
 * dashboard/ Flask 콘솔의 풀 기능은 대행사 운영자용으로 따로 운영.
 */
import fs from 'node:fs/promises';
import path from 'node:path';

const OUTPUT_DIR = path.join(process.cwd(), '..', 'output');
const PROPOSAL_MONTH = '202606';

export interface JuneStatus {
  generated_at: string;
  proposal_meta: {
    data_period: string;
    branches: string[];
  } | null;
  headline: {
    target_base: number;
    target_stretch: number;
    target_cpa: number;
    pace_caveat: string;   // "6월 시작 전" 또는 페이스 텍스트
  };
  key_findings: {
    addon: string | null;
    targeting_health: string | null;
    geo_leakage: string | null;
  };
  recent_actions: ActionLog[];
  action_stats: {
    total: number;
    last_7_days: number;
    by_type: { type: string; count: number }[];
  };
  proposal_url: string;
}

export interface ActionLog {
  id?: string;
  date: string;
  timestamp: string;
  action_type: string;
  branch?: string | null;
  creative_name?: string | null;
  before?: string | null;
  after?: string | null;
  reason: string;
  effects?: { d1?: any; d3?: any; d7?: any };
}

async function loadProposal(): Promise<any | null> {
  const fp = path.join(OUTPUT_DIR, 'proposal', PROPOSAL_MONTH, `proposal_daeat_daeat_${PROPOSAL_MONTH}.json`);
  // 파일명 일관성: 실제 파일은 proposal_daeat_202606.json
  const actualFp = path.join(OUTPUT_DIR, 'proposal', PROPOSAL_MONTH, `proposal_daeat_${PROPOSAL_MONTH}.json`);
  try {
    const raw = await fs.readFile(actualFp, 'utf-8');
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

async function loadActions(): Promise<ActionLog[]> {
  const fp = path.join(OUTPUT_DIR, 'tracker', 'actions.jsonl');
  try {
    const raw = await fs.readFile(fp, 'utf-8');
    const lines = raw.split('\n').filter((l) => l.trim());
    return lines.map((l) => JSON.parse(l));
  } catch {
    return [];
  }
}

function summarizeAddon(addon: any): string | null {
  if (!addon) return null;
  const rec = addon.judgement?.recommended_action;
  if (!rec) return null;
  return `${rec.label} — ${rec.summary?.slice(0, 200) || ''}`;
}

function summarizeTargeting(th: any): string | null {
  if (!th?.available) return null;
  return th.recommendation?.headline || null;
}

function summarizeGeo(geo: any): string | null {
  if (!geo?.available) return null;
  return geo.recommendation?.headline || null;
}

export async function loadJuneStatus(): Promise<JuneStatus> {
  const proposal = await loadProposal();
  const actions = await loadActions();

  const last7Cutoff = new Date();
  last7Cutoff.setDate(last7Cutoff.getDate() - 7);
  const cutoffStr = last7Cutoff.toISOString().slice(0, 10);

  const byTypeMap: Record<string, number> = {};
  for (const a of actions) {
    byTypeMap[a.action_type] = (byTypeMap[a.action_type] || 0) + 1;
  }
  const byType = Object.entries(byTypeMap)
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count);

  const sortedActions = [...actions].sort((a, b) => (b.timestamp || '').localeCompare(a.timestamp || ''));

  return {
    generated_at: new Date().toISOString(),
    proposal_meta: proposal?.meta || null,
    headline: {
      target_base: 762,
      target_stretch: 822,
      target_cpa: 27278,
      pace_caveat: '6월 시작 전이거나 부분 운영 상태 — 콘솔에서 실시간 페이스 확인 권장',
    },
    key_findings: {
      addon: summarizeAddon(proposal?.addon_effect),
      targeting_health: summarizeTargeting(proposal?.targeting_health),
      geo_leakage: summarizeGeo(proposal?.geo_leakage),
    },
    recent_actions: sortedActions.slice(0, 20),
    action_stats: {
      total: actions.length,
      last_7_days: actions.filter((a) => (a.date || '') >= cutoffStr).length,
      by_type: byType,
    },
    proposal_url: `/proposal/${PROPOSAL_MONTH}`,
  };
}
