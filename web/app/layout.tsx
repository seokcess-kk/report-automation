import type { Metadata } from 'next';
import './globals.css';
import Link from 'next/link';

export const metadata: Metadata = {
  title: '다이트 리포트',
  description: '다이트한의원 TikTok 광고 성과 리포트',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen">
        <header className="sticky top-0 z-30 bg-bg/80 backdrop-blur-md border-b border-border">
          <nav className="max-w-7xl mx-auto px-4 h-12 flex items-center gap-1 text-sm">
            <Link href="/" className="font-bold tracking-tight text-fg mr-4 flex items-baseline gap-1.5">
              <span className="text-accent">daeat</span>
              <span className="text-subtle text-xs font-medium uppercase tracking-wider">report</span>
            </Link>
            <NavLink href="/tracker">목표</NavLink>
            <NavLink href="/daily">데일리</NavLink>
            <NavLink href="/weekly">위클리</NavLink>
            <NavLink href="/monthly">먼슬리</NavLink>
            <Link href="/mobile" className="ml-auto text-subtle hover:text-fg text-xs">📱 모바일</Link>
          </nav>
        </header>
        <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="px-3 py-1.5 rounded-md text-muted hover:text-fg hover:bg-elevated transition-colors duration-150"
    >
      {children}
    </Link>
  );
}
