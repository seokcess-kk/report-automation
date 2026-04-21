import { NextResponse } from 'next/server';
import { createToken, timingSafeEqual } from '@/lib/session';

export async function POST(req: Request) {
  const { password } = await req.json().catch(() => ({ password: '' }));
  const expected = process.env.ACCESS_PASSWORD;
  if (!expected || typeof password !== 'string' || !timingSafeEqual(password, expected)) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }
  const token = await createToken();
  const res = NextResponse.json({ ok: true });
  res.cookies.set('report_auth', token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 30,
    path: '/',
  });
  return res;
}
