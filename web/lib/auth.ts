/** 비밀번호 게이트 — env.ACCESS_PASSWORD 과 대조 */
import { cookies } from 'next/headers';

export const AUTH_COOKIE = 'report_auth';

export function checkAuth(): boolean {
  const token = cookies().get(AUTH_COOKIE)?.value;
  const expected = process.env.ACCESS_PASSWORD;
  if (!expected) return false;
  return token === expected;
}
