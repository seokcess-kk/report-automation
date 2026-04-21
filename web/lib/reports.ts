/** 레포 루트 output/ 디렉토리에서 리포트 데이터 로드 */
import fs from 'node:fs/promises';
import path from 'node:path';

const OUTPUT_DIR = path.join(process.cwd(), '..', 'output');

export interface WeeklyData {
  period_this: string;
  period_this_full: string;
  period_prev: string;
  issue_date: string;
  kpi_this: { cost: number; conv: number; clicks: number; cpa: number; ctr: number; cvr: number };
  kpi_prev: typeof kpiShape;
  target_cpa: number;
  branch: BranchRow[];
  tier_list: any[];
  tier_this: any[];
  new_creatives: any[];
  off_list: any[];
  on_list: any[];
  off_creative_analysis: any[];
  branch_creative: any[];
  daily: any[];
  insights: any[];
  monthly_target_conv: number;
  conv_so_far: number;
  proj_conv: number;
  conv_pct: number;
  proj_pct: number;
  end_date_str: string;
}

declare const kpiShape: { cost: number; conv: number; clicks: number; cpa: number; ctr: number; cvr: number };

export interface BranchRow {
  branch: string;
  총비용: number;
  총전환: number;
  총클릭: number;
  총노출: number;
  CPA: number;
  CTR: number;
  CVR: number;
  CPA_prev: number;
  CTR_prev: number;
  CVR_prev: number;
  CPA_diff: number;
  CTR_diff: number;
  CVR_diff: number;
  효율점수: number;
}

export async function listWeeklyDates(): Promise<string[]> {
  const dir = path.join(OUTPUT_DIR, 'weekly');
  try {
    const entries = await fs.readdir(dir);
    return entries.filter((e) => /^\d{8}$/.test(e)).sort().reverse();
  } catch {
    return [];
  }
}

export async function loadWeekly(date: string): Promise<WeeklyData | null> {
  const fp = path.join(OUTPUT_DIR, 'weekly', date, `tiktok_weekly_daeat_${date}.json`);
  try {
    const raw = await fs.readFile(fp, 'utf-8');
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export async function loadLatestWeekly(): Promise<{ date: string; data: WeeklyData } | null> {
  const dates = await listWeeklyDates();
  for (const d of dates) {
    const data = await loadWeekly(d);
    if (data) return { date: d, data };
  }
  return null;
}

export async function loadDailySnapshot(): Promise<any | null> {
  const fp = path.join(OUTPUT_DIR, 'daily', 'daily_snapshot.json');
  try {
    return JSON.parse(await fs.readFile(fp, 'utf-8'));
  } catch {
    return null;
  }
}

// ─────── Daily ───────

export interface DailyBranch {
  branch: string;
  daily_conv: number;
  cum_cvr: number;
  cum_cpa: number | null;
  target: number;
  tag: 'best' | 'focus';
  ratio: number | null;
}

export interface DailyData {
  date: string;
  date_label: string;
  goal: {
    conv_current: number;
    conv_target: number;
    conv_pct: number;
    remaining_days: number;
    budget_pct: number;
    budget_total: number;
  };
  kpi_daily: { cost: number; conv: number; cpa: number | null; ctr: number; cvr: number };
  kpi_cum: { cost: number; conv: number; cpa: number | null; ctr: number; cvr: number };
  kpi_prev: { cost?: number; conv?: number; cpa?: number | null; ctr?: number; cvr?: number };
  branches: DailyBranch[];
  zero_conv_lines: string[];
  anomaly_lines: string[];
  notable_lines: string[];
  checkpoints: string[];
}

export async function listDailyDates(): Promise<string[]> {
  const dir = path.join(OUTPUT_DIR, 'daily');
  try {
    const entries = await fs.readdir(dir);
    return entries.filter((e) => /^\d{8}$/.test(e)).sort().reverse();
  } catch {
    return [];
  }
}

export async function loadDaily(date: string): Promise<DailyData | null> {
  const fp = path.join(OUTPUT_DIR, 'daily', date, `tiktok_daily_${date}.json`);
  try {
    return JSON.parse(await fs.readFile(fp, 'utf-8'));
  } catch {
    return null;
  }
}

export async function loadLatestDaily(): Promise<{ date: string; data: DailyData } | null> {
  for (const d of await listDailyDates()) {
    const data = await loadDaily(d);
    if (data) return { date: d, data };
  }
  return null;
}

// ─────── Monthly ───────

export interface MonthlyData {
  period: any;
  kpi: { cost: number; conv: number; cpa: number; ctr: number; cvr: number; lpv?: number };
  target_cpa: number;
  monthly_target_conv: number;
  budget: Record<string, number>;
  creative: any[];
  creative_new: any[];
  branch: any[];
  by_branch: Record<string, any>;
  cross_gap: any[];
  lifetime: any[];
  hook_compare: any[];
  daily: any[];
  next_budget: any[];
  off_cumul: any[];
  expansion: any[];
  off_perf: any[];
  before_after: any[];
}

export async function listMonthlyDates(): Promise<string[]> {
  const dir = path.join(OUTPUT_DIR, 'monthly');
  try {
    const entries = await fs.readdir(dir);
    return entries.filter((e) => /^\d{6}$/.test(e)).sort().reverse();
  } catch {
    return [];
  }
}

export async function loadMonthly(month: string): Promise<MonthlyData | null> {
  const fp = path.join(OUTPUT_DIR, 'monthly', month, `tiktok_monthly_daeat_${month}.json`);
  try {
    return JSON.parse(await fs.readFile(fp, 'utf-8'));
  } catch {
    return null;
  }
}

// ─────── Tracker (Phase 1: 목표 달성 트래커) ───────

export interface BranchPace {
  branch: string;
  budget: number;
  cost_so_far: number;
  budget_pct: number;
  conv_target: number;
  conv_so_far: number;
  conv_pct: number;
  proj_conv: number;
  proj_pct: number;
  clicks: number;
  impressions: number;
  cpa: number | null;
  target_cpa: number;
  cpa_vs_target_pct: number | null;
  status: 'ok' | 'warn' | 'danger';
  sparkline: { date: string; cost: number; conv: number }[];
  tier_distribution?: Record<string, number>;
}

export interface BranchPaceData {
  updated: string;
  month: string;
  days_total: number;
  days_elapsed: number;
  date_progress: number;
  overall: {
    budget_total: number;
    cost_so_far: number;
    budget_pct: number;
    conv_target: number;
    conv_so_far: number;
    conv_pct: number;
    proj_conv: number;
    proj_pct: number;
    target_cpa: number;
    status: 'ok' | 'warn' | 'danger';
  };
  branches: BranchPace[];
  days_total_remaining?: number;
}

export interface ActionProposal {
  id: string;
  priority: 'high' | 'medium' | 'low';
  scope: 'branch' | 'creative' | 'age';
  target: string;
  action_type: string;
  title: string;
  reason: string;
  recommended_value: Record<string, any>;
  evidence: Record<string, any>;
}

export interface ProposalsData {
  updated: string;
  rule_version: string;
  proposals: ActionProposal[];
  summary: { total: number; high: number; medium: number; low: number };
}

async function listDataDirs(): Promise<string[]> {
  const dir = path.join(OUTPUT_DIR, 'data');
  try {
    const entries = await fs.readdir(dir);
    return entries.filter((e) => /^\d{8}$/.test(e)).sort().reverse();
  } catch {
    return [];
  }
}

export interface SegmentRow {
  [key: string]: any;
  총비용: number;
  총전환: number;
  CPA: number | null;
  CTR: number | null;
  CVR: number | null;
  비용비중: number;
  전환비중: number;
  예산효율점수: number | null;
}

export interface SegmentAnalysis {
  weekday: SegmentRow[];
  creative_type: SegmentRow[];
  hour: SegmentRow[];
}

export type TrackerBundle = {
  date: string;
  pace: BranchPaceData;
  proposals: ProposalsData;
  segments: SegmentAnalysis | null;
};

// 메모리 캐시 60초 (데이터는 일 1회만 갱신되므로 충분히 안전, 수동 갱신은 dev restart)
const TRACKER_TTL_MS = 60_000;
let trackerCache: { data: TrackerBundle | null; fetchedAt: number } | null = null;

export async function loadLatestTracker(): Promise<TrackerBundle | null> {
  const now = Date.now();
  if (trackerCache && now - trackerCache.fetchedAt < TRACKER_TTL_MS) {
    return trackerCache.data;
  }
  const fresh = await _loadLatestTrackerFresh();
  trackerCache = { data: fresh, fetchedAt: now };
  return fresh;
}

async function _loadLatestTrackerFresh(): Promise<TrackerBundle | null> {
  for (const d of await listDataDirs()) {
    const pacePath = path.join(OUTPUT_DIR, 'data', d, 'branch_pace.json');
    const propPath = path.join(OUTPUT_DIR, 'data', d, 'action_proposals.json');
    try {
      const pace = JSON.parse(await fs.readFile(pacePath, 'utf-8'));
      const proposals = JSON.parse(await fs.readFile(propPath, 'utf-8'));
      let segments: SegmentAnalysis | null = null;
      try {
        const segPath = path.join(OUTPUT_DIR, 'data', d, 'segment_analysis.json');
        segments = JSON.parse(await fs.readFile(segPath, 'utf-8'));
      } catch {
        // segment 데이터 없으면 null
      }
      return { date: d, pace, proposals, segments };
    } catch {
      continue;
    }
  }
  return null;
}
