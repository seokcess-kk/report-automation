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

async function callApi<T = any>(
  method: 'GET' | 'POST',
  endpoint: string,
  body: Record<string, any>
): Promise<T> {
  const { token } = getCreds();
  const url = `${HOST}${endpoint}`;
  const init: RequestInit = {
    method,
    headers: { 'Access-Token': token, 'Content-Type': 'application/json' },
  };
  if (method === 'POST') {
    init.body = JSON.stringify(body);
  }
  const res = await fetch(url, init);
  const json = await res.json();
  if (json.code !== 0) {
    throw new Error(`[TikTok API] ${endpoint} code=${json.code} msg=${json.message}`);
  }
  return json as T;
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
