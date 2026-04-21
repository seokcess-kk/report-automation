import { NextResponse } from 'next/server';
import { Decision, updateDecisions } from '@/lib/decisions-store';
import { executeAction } from '@/lib/action-executor';
import { timingSafeEqual } from '@/lib/session';

function validateBudgetOverrides(v: any): v is Record<string, number> | undefined {
  if (v == null) return true;
  if (typeof v !== 'object') return false;
  for (const [k, val] of Object.entries(v)) {
    if (typeof k !== 'string' || typeof val !== 'number' || !Number.isFinite(val) || val <= 0) {
      return false;
    }
  }
  return true;
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { decision_id, admin_password, budget_overrides } = body as {
      decision_id: string;
      admin_password: string;
      budget_overrides?: Record<string, number>;
    };

    // 1. 관리 비밀번호 검증 (timing-safe)
    const expected = process.env.ADMIN_PASSWORD;
    if (!expected) {
      return NextResponse.json({ error: 'ADMIN_PASSWORD 미설정' }, { status: 500 });
    }
    if (typeof admin_password !== 'string' || !timingSafeEqual(admin_password, expected)) {
      return NextResponse.json({ error: '관리 비밀번호 불일치' }, { status: 401 });
    }

    // 2. 입력 검증
    if (!decision_id || typeof decision_id !== 'string' || !/^d\d{3,}$/.test(decision_id)) {
      return NextResponse.json({ error: 'decision_id 형식 오류' }, { status: 400 });
    }
    if (!validateBudgetOverrides(budget_overrides)) {
      return NextResponse.json(
        { error: 'budget_overrides 형식 오류 (양수 number 필요)' },
        { status: 400 }
      );
    }

    // 3. Race-safe 실행: 파일 lock 안에서 executed=true 즉시 마킹 → 실제 API 호출
    //    (API 호출 자체는 오래 걸릴 수 있으나 중복 진입은 차단)
    type Stage1 = { target: Decision } | { error: string; status: number };
    const stage1 = await updateDecisions<Stage1>(async (current) => {
      const target = current.find((d) => d.id === decision_id);
      if (!target) return { next: current, value: { error: '결정 없음', status: 404 } };
      if (!target.queued) return { next: current, value: { error: '실행 대기열에 없음', status: 400 } };
      if (target.executed) return { next: current, value: { error: '이미 실행됨', status: 400 } };

      target.executed = true;
      target.executed_at = new Date().toISOString();
      target.execution_result = { status: 'success', message: '(진행 중)', dry_run: false };
      return { next: current, value: { target } };
    });

    if ('error' in stage1) {
      return NextResponse.json({ error: stage1.error }, { status: stage1.status });
    }

    // 4. 실제 실행 (file lock 밖에서 — API 호출이 길어도 다른 결정은 처리 가능)
    const result = await executeAction(stage1.target.proposal_snapshot, { budget_overrides });

    // 5. 결과 기록
    const finalDecision = await updateDecisions<Decision>(async (current) => {
      const target = current.find((d) => d.id === decision_id);
      if (target) {
        target.execution_result = {
          status: result.status === 'success' ? 'success' : 'failed',
          message: result.message,
          dry_run: result.dry_run,
          ...(Array.isArray((result as any).details) ? { details: (result as any).details } : {}),
          raw_status: result.status,
        };
        // 실패 시 재실행 가능하도록 롤백
        if (result.status === 'failed') {
          target.executed = false;
          target.executed_at = null;
        }
      }
      return { next: current, value: target as Decision };
    });

    return NextResponse.json({ ok: true, decision: finalDecision });
  } catch (e: any) {
    return NextResponse.json({ error: String(e.message || e) }, { status: 500 });
  }
}
