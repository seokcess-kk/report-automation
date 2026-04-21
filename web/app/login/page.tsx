'use client';
import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

function LoginForm() {
  const router = useRouter();
  const search = useSearchParams();
  const next = search.get('next') || '/';
  const [password, setPassword] = useState('');
  const [err, setErr] = useState('');

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr('');
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    if (res.ok) {
      router.push(next);
      router.refresh();
    } else {
      setErr('비밀번호가 올바르지 않습니다.');
    }
  }

  return (
    <form onSubmit={submit} className="card w-full max-w-sm space-y-4">
      <h1 className="text-xl font-bold">다이트 TikTok 리포트</h1>
      <p className="text-sm text-slate-400">접근 비밀번호를 입력하세요.</p>
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        className="w-full bg-brand-bg border border-brand-border rounded px-3 py-2 text-sm"
        autoFocus
      />
      {err && <p className="text-sm text-brand-danger">{err}</p>}
      <button type="submit" className="w-full bg-brand-primary text-brand-bg rounded py-2 font-medium hover:opacity-90">
        로그인
      </button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Suspense fallback={<div className="text-slate-400 text-sm">로딩 중…</div>}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
