/** 액션 타입별 실행 어댑터.
 *
 * 지원 (실제 API):
 *   - pause_creative       ad_ids → DISABLE
 *   - reactivate_creative  ad_ids → ENABLE
 *   - budget_decrease      adgroup별 budget update (사용자 지정값)
 *   - budget_increase      adgroup별 budget update (사용자 지정값)
 *
 * 미지원 (수동 안내):
 *   - budget_reallocate, creative_review, scale_creative,
 *     exclude_age, expand_age, dayparting, weekday_boost, type_scale
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { updateAdStatus, updateAdgroupBudget } from './tiktok-api';

const OUTPUT_DIR = path.join(process.cwd(), '..', 'output');

export interface AdMapping {
  ads: Record<string, {
    ad_id: string;
    ad_name: string;
    adgroup_id: string;
    adgroup_name: string;
    지점: string | null;
    operation_status: string;
  }>;
  adgroups_by_branch: Record<string, Array<{
    adgroup_id: string;
    adgroup_name: string;
    budget: number;
    budget_mode: string;
    operation_status: string;
  }>>;
}

export interface ExecutionResult {
  status: 'success' | 'partial' | 'failed' | 'skipped';
  message: string;
  dry_run: boolean;
  details?: any[];
}

export interface ExecutionContext {
  /** budget_* 액션에 대한 adgroup별 예산 (adgroup_id → new_budget). */
  budget_overrides?: Record<string, number>;
}

async function loadLatestMapping(): Promise<AdMapping | null> {
  const dir = path.join(OUTPUT_DIR, 'data');
  try {
    const dates = (await fs.readdir(dir))
      .filter((d) => /^\d{8}$/.test(d))
      .sort()
      .reverse();
    for (const d of dates) {
      const p = path.join(dir, d, 'ad_mapping.json');
      try {
        const raw = await fs.readFile(p, 'utf-8');
        return JSON.parse(raw);
      } catch {
        continue;
      }
    }
  } catch {}
  return null;
}

/** 소재구분/매칭키로 ad_ids 검색 */
function findAdIdsByCreative(mapping: AdMapping, target: string): string[] {
  const ids: string[] = [];
  for (const [adid, ad] of Object.entries(mapping.ads)) {
    const name = ad.ad_name || '';
    // ad_name이 target으로 시작하거나 포함하면 매칭
    if (name.includes(target) || target.includes(name.split('_')[0])) {
      // ON 상태만 (중단/재활성화 대상)
      if (ad.operation_status === 'ENABLE' || ad.operation_status === 'DISABLE') {
        ids.push(adid);
      }
    }
  }
  return ids;
}

export async function executeAction(
  proposal: any,
  ctx: ExecutionContext = {}
): Promise<ExecutionResult> {
  const type = proposal.action_type;

  // 수동 안내만 필요한 타입
  const manualOnly: Record<string, string> = {
    creative_review: 'TikTok Ads Manager에서 해당 지점 전 소재를 리뷰하세요.',
    scale_creative: 'TikTok Ads Manager에서 예산 증액 또는 소재 복제를 진행하세요.',
    exclude_age: 'TikTok Ads Manager의 adgroup 타겟팅에서 나이대를 조정하세요.',
    expand_age: 'TikTok Ads Manager의 adgroup 타겟팅에서 나이대 비중을 확대하세요.',
    dayparting: 'TikTok Ads Manager의 adgroup 스케줄(dayparting)을 조정하세요.',
    weekday_boost: 'TikTok Ads Manager의 adgroup 스케줄에서 요일 가중을 설정하세요.',
    type_scale: '해당 유형의 신규 소재를 제작·업로드하세요 (운영 차원).',
    budget_reallocate: '양측 지점의 adgroup 예산을 각각 조정하세요 (Phase 3.5에서 자동화 예정).',
  };

  if (type in manualOnly) {
    return {
      status: 'skipped',
      message: `수동 조정 필요 — ${manualOnly[type]}`,
      dry_run: false,
    };
  }

  const mapping = await loadLatestMapping();
  if (!mapping) {
    return {
      status: 'failed',
      message: 'ad_mapping.json 없음 — python run_analysis.py --collect 먼저 실행 필요',
      dry_run: false,
    };
  }

  // pause / reactivate
  if (type === 'pause_creative' || type === 'reactivate_creative') {
    const target = proposal.target;
    const adIds = findAdIdsByCreative(mapping, target);
    if (adIds.length === 0) {
      return {
        status: 'failed',
        message: `"${target}" 매칭되는 ad 없음 — ad_mapping 갱신 또는 이름 확인`,
        dry_run: false,
      };
    }
    const newStatus = type === 'pause_creative' ? 'DISABLE' : 'ENABLE';
    try {
      const resp = await updateAdStatus(adIds, newStatus);
      return {
        status: 'success',
        message: `${adIds.length}개 광고 ${newStatus} 완료`,
        dry_run: false,
        details: [{ ad_ids: adIds, api_response: resp }],
      };
    } catch (e: any) {
      return {
        status: 'failed',
        message: String(e.message || e),
        dry_run: false,
      };
    }
  }

  // budget_decrease / budget_increase — 사용자 지정값 사용
  if (type === 'budget_decrease' || type === 'budget_increase') {
    const branch = proposal.target;
    const adgroups = mapping.adgroups_by_branch[branch] || [];
    if (adgroups.length === 0) {
      return {
        status: 'failed',
        message: `"${branch}" 지점의 adgroup 없음`,
        dry_run: false,
      };
    }
    const overrides = ctx.budget_overrides || {};
    if (Object.keys(overrides).length === 0) {
      return {
        status: 'failed',
        message: 'budget_overrides 없음 — adgroup별 예산을 지정해 주세요',
        dry_run: false,
      };
    }

    const results: any[] = [];
    let successCount = 0;
    let failCount = 0;
    for (const ag of adgroups) {
      const newBudget = overrides[ag.adgroup_id];
      if (newBudget == null || newBudget === ag.budget) {
        continue; // 변경 없음 skip
      }
      try {
        const resp = await updateAdgroupBudget(ag.adgroup_id, Math.round(newBudget));
        results.push({ adgroup_id: ag.adgroup_id, new_budget: newBudget, ok: true, api_response: resp });
        successCount += 1;
      } catch (e: any) {
        results.push({ adgroup_id: ag.adgroup_id, new_budget: newBudget, ok: false, error: String(e.message || e) });
        failCount += 1;
      }
    }

    if (successCount === 0 && failCount === 0) {
      return {
        status: 'skipped',
        message: '변경 사항 없음 (모든 adgroup 예산 동일)',
        dry_run: false,
      };
    }
    return {
      status: failCount === 0 ? 'success' : successCount > 0 ? 'partial' : 'failed',
      message: `${successCount}개 adgroup 예산 변경 완료${failCount > 0 ? `, ${failCount}개 실패` : ''}`,
      dry_run: false,
      details: results,
    };
  }

  return {
    status: 'failed',
    message: `알 수 없는 action_type: ${type}`,
    dry_run: false,
  };
}

/** 실행 전 adgroup 후보 조회 (budget 모달 UI용) */
export async function getBranchAdgroups(branch: string): Promise<AdMapping['adgroups_by_branch'][string]> {
  const mapping = await loadLatestMapping();
  return mapping?.adgroups_by_branch[branch] || [];
}

/** 실행 전 매칭 ad 조회 (소재 모달 UI용) */
export async function getCreativeAds(target: string): Promise<Array<{ad_id: string; ad_name: string; status: string}>> {
  const mapping = await loadLatestMapping();
  if (!mapping) return [];
  const result: Array<{ad_id: string; ad_name: string; status: string}> = [];
  for (const [adid, ad] of Object.entries(mapping.ads)) {
    const name = ad.ad_name || '';
    if (name.includes(target) || target.includes(name.split('_')[0])) {
      result.push({ ad_id: adid, ad_name: name, status: ad.operation_status });
    }
  }
  return result;
}
