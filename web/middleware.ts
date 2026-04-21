import { NextResponse, type NextRequest } from 'next/server';

const AUTH_COOKIE = 'report_auth';
const PUBLIC_PATHS = ['/login', '/api/auth'];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) return NextResponse.next();
  if (pathname.startsWith('/_next') || pathname.startsWith('/favicon')) return NextResponse.next();

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
