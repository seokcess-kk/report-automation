import { NextResponse, type NextRequest } from 'next/server';

const AUTH_COOKIE = 'report_auth';
const PUBLIC_PATHS = ['/login', '/api/auth'];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) return NextResponse.next();
  if (pathname.startsWith('/_next') || pathname.startsWith('/favicon')) return NextResponse.next();

  // 로컬 개발(ACCESS_PASSWORD 미설정)에선 인증 생략 — Vercel 배포 시 env가 설정되므로 보호 유지
  if (process.env.NODE_ENV === 'development' && !process.env.ACCESS_PASSWORD) {
    return NextResponse.next();
  }

  const token = req.cookies.get(AUTH_COOKIE)?.value;
  const expected = process.env.ACCESS_PASSWORD;
  if (!expected || token !== expected) {
    const url = req.nextUrl.clone();
    url.pathname = '/login';
    url.searchParams.set('next', pathname);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api/auth|_next/static|_next/image|favicon.ico|login).*)'],
};
