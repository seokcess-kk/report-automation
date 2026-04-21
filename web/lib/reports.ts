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
  const fp = path.join(OUTPUT_DIR, 'weekly', date, `tiktok_weekly_dayt_${date}.json`);
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
