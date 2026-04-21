'use client';
import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui';

function LoginForm() {
  const router = useRouter();
  const search = useSearchParams();
  const next = search.get('next') || '/';
  const [password, setPassword] = useState('');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr('');
    setLoading(true);
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    setLoading(false);
    if (res.ok) {
      router.push(next);
      router.refresh();
    } else {
      setErr('비밀번호가 올바르지 않습니다.');
    }
  }

  return (
    <form onSubmit={submit} className="bg-surface border border-border-strong rounded-xl shadow-card w-full max-w-sm p-6 space-y-4 animate-fade-in">
      <div>
        <div className="flex items-baseline gap-1.5 mb-2">
          <span className="text-2xl font-bold text-accent tracking-tight">dayt</span>
          <span className="text-subtle text-xs font-medium uppercase tracking-widest">report</span>
        </div>
        <p className="text-sm text-muted">접근 비밀번호를 입력하세요.</p>
      </div>
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        className="w-full bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-fg focus:border-accent"
        autoFocus
      />
      {err && <p className="text-sm text-danger">{err}</p>}
      <Button type="submit" variant="primary" size="lg" className="w-full" disabled={loading || !password}>
        {loading ? '로그인 중…' : '로그인'}
      </Button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 -mt-12">
      <Suspense fallback={<div className="text-muted text-sm">로딩 중…</div>}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
