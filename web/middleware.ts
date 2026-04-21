import { NextResponse, type NextRequest } from 'next/server';
import { validateToken } from '@/lib/session';

const AUTH_COOKIE = 'report_auth';
const PUBLIC_PATHS = ['/login', '/api/auth'];

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) return NextResponse.next();
  if (pathname.startsWith('/_next') || pathname.startsWith('/favicon')) return NextResponse.next();

  // DEV bypass: 명시적으로 ALLOW_DEV_BYPASS=true AND ACCESS_PASSWORD 미설정 둘 다 만족해야 생략
  const isDev = process.env.NODE_ENV === 'development';
  const bypassAllowed = process.env.ALLOW_DEV_BYPASS === 'true';
  if (isDev && bypassAllowed && !process.env.ACCESS_PASSWORD) {
    return NextResponse.next();
  }

  const token = req.cookies.get(AUTH_COOKIE)?.value;
  const valid = await validateToken(token);
  if (!valid) {
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
