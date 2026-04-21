/** Edge-runtime 호환 세션 관리 (Web Crypto API 기반).
 *
 * 쿠키에는 `<timestamp>.<HMAC>` 형식의 서명 토큰만 저장.
 * 비밀번호/세션 비밀값은 쿠키에 절대 포함하지 않는다.
 *
 * 서명 키 우선순위: SESSION_SECRET > ACCESS_PASSWORD (fallback, 개발 편의)
 * 만료: 30일
 */

export const SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000;

function getSecret(): string {
  return (
    process.env.SESSION_SECRET ||
    process.env.ACCESS_PASSWORD ||
    'dev-only-insecure-fallback'
  );
}

function bufToHex(buf: ArrayBuffer | Uint8Array): string {
  const arr = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  let hex = '';
  for (let i = 0; i < arr.length; i++) hex += arr[i].toString(16).padStart(2, '0');
  return hex;
}

async function hmacHex(data: string, secret: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(data));
  return bufToHex(sig);
}

/** Timing-safe 문자열 비교 (Web Crypto API 없이 constant-time). */
export function timingSafeEqual(a: string, b: string): boolean {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

/** 새 세션 토큰 생성 (로그인 성공 시). */
export async function createToken(): Promise<string> {
  const ts = Date.now().toString();
  const sig = await hmacHex(ts, getSecret());
  return `${ts}.${sig}`;
}

/** 쿠키의 세션 토큰 검증 (middleware + API 라우트에서 공용 사용). */
export async function validateToken(token: string | undefined | null): Promise<boolean> {
  if (!token || typeof token !== 'string') return false;
  const dot = token.indexOf('.');
  if (dot < 0) return false;
  const ts = token.slice(0, dot);
  const sig = token.slice(dot + 1);
  const tsNum = Number(ts);
  if (!Number.isFinite(tsNum) || tsNum <= 0) return false;
  const age = Date.now() - tsNum;
  if (age < 0 || age > SESSION_TTL_MS) return false;
  const expected = await hmacHex(ts, getSecret());
  return timingSafeEqual(sig, expected);
}
