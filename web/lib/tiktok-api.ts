/** TikTok Marketing API v1.3 HTTP 래퍼 (서버 전용). */
const HOST = 'https://business-api.tiktok.com/open_api/v1.3';

function getCreds() {
  const token = process.env.TIKTOK_ACCESS_TOKEN;
  const advertiser_id = process.env.TIKTOK_ADVERTISER_ID;
  if (!token || !advertiser_id) {
    throw new Error('TIKTOK_ACCESS_TOKEN / TIKTOK_ADVERTISER_ID 환경변수 미설정');
  }
  return { token, advertiser_id };
}

const DEFAULT_TIMEOUT_MS = 15_000;

// 토큰 만료/무효 코드 — 즉시 실패, 재시도 금지
const TOKEN_ERROR_CODES = new Set([40100, 40104, 40105, 40107, 40109, 40113, 40114]);

async function callApi<T = any>(
  method: 'GET' | 'POST',
  endpoint: string,
  body: Record<string, any>,
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<T> {
  const { token } = getCreds();
  const url = `${HOST}${endpoint}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const init: RequestInit = {
    method,
    headers: { 'Access-Token': token, 'Content-Type': 'application/json' },
    signal: controller.signal,
  };
  if (method === 'POST') init.body = JSON.stringify(body);

  try {
    const res = await fetch(url, init);
    if (res.status === 401 || res.status === 403) {
      throw new Error(`[TikTok API] ${endpoint} HTTP ${res.status} - 토큰 만료/권한 없음. TIKTOK_ACCESS_TOKEN 갱신 필요.`);
    }
    const json = await res.json();
    if (json.code !== 0) {
      if (TOKEN_ERROR_CODES.has(json.code)) {
        throw new Error(`[TikTok API] 토큰 만료/무효 (code=${json.code}). TIKTOK_ACCESS_TOKEN 갱신 필요.`);
      }
      throw new Error(`[TikTok API] ${endpoint} code=${json.code} msg=${json.message}`);
    }
    return json as T;
  } catch (e: any) {
    if (e.name === 'AbortError') {
      throw new Error(`[TikTok API] ${endpoint} timeout (${timeoutMs}ms)`);
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

/** ad/status/update/ — 광고 상태 변경 (ENABLE / DISABLE) */
export async function updateAdStatus(
  ad_ids: string[],
  operation_status: 'ENABLE' | 'DISABLE'
): Promise<any> {
  const { advertiser_id } = getCreds();
  return callApi('POST', '/ad/status/update/', {
    advertiser_id,
    ad_ids,
    operation_status,
  });
}

/** adgroup/update/ — 광고그룹 예산 변경 (KRW 정수값) */
export async function updateAdgroupBudget(
  adgroup_id: string,
  budget: number
): Promise<any> {
  const { advertiser_id } = getCreds();
  return callApi('POST', '/adgroup/update/', {
    advertiser_id,
    adgroup_id,
    budget,
  });
}
