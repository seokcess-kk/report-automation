import type { Metadata } from 'next';
import './globals.css';
import Link from 'next/link';

export const metadata: Metadata = {
  title: '다이트 TikTok 리포트',
  description: '다이트한의원 TikTok 광고 성과 리포트',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <header className="border-b border-brand-border bg-brand-bg/80 backdrop-blur sticky top-0 z-10">
          <nav className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-6 text-sm">
            <Link href="/" className="font-bold text-brand-primary">다이트 리포트</Link>
            <Link href="/weekly" className="text-slate-300 hover:text-white">위클리</Link>
            <span className="text-slate-500">데일리 · 먼슬리 (준비중)</span>
          </nav>
        </header>
        <main className="max-w-6xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
