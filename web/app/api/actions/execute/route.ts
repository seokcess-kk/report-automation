import { NextResponse } from 'next/server';
import fs from 'node:fs/promises';
import path from 'node:path';
import type { Decision } from '../decisions/route';
import { executeAction } from '@/lib/action-executor';

const OUTPUT_DIR = path.join(process.cwd(), '..', 'output');
const DECISIONS_PATH = path.join(OUTPUT_DIR, 'action_decisions.json');

async function loadDecisions(): Promise<Decision[]> {
  try {
    const raw = await fs.readFile(DECISIONS_PATH, 'utf-8');
    return JSON.parse(raw).decisions || [];
  } catch {
    return [];
  }
}

async function saveDecisions(decisions: Decision[]) {
  await fs.writeFile(DECISIONS_PATH, JSON.stringify({ decisions }, null, 2), 'utf-8');
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { decision_id, admin_password, budget_overrides } = body as {
      decision_id: string;
      admin_password: string;
      budget_overrides?: Record<string, number>;
    };

    const expected = process.env.ADMIN_PASSWORD;
    if (!expected) {
      return NextResponse.json({ error: 'ADMIN_PASSWORD 미설정' }, { status: 500 });
    }
    if (admin_password !== expected) {
      return NextResponse.json({ error: '관리 비밀번호 불일치' }, { status: 401 });
    }

    if (!decision_id) {
      return NextResponse.json({ error: 'decision_id 필수' }, { status: 400 });
    }

    const decisions = await loadDecisions();
    const target = decisions.find((d) => d.id === decision_id);

    if (!target) {
      return NextResponse.json({ error: '결정 없음' }, { status: 404 });
    }
    if (!target.queued) {
      return NextResponse.json({ error: '실행 대기열에 없음' }, { status: 400 });
    }
    if (target.executed) {
      return NextResponse.json({ error: '이미 실행됨' }, { status: 400 });
    }

    // 실제 실행
    const result = await executeAction(target.proposal_snapshot, { budget_overrides });

    target.executed = true;
    target.executed_at = new Date().toISOString();
    target.execution_result = {
      status: result.status === 'success' ? 'success' : 'failed',
      message: result.message,
      dry_run: result.dry_run,
    };
    // details는 별도 (있을 때만)
    if ((result as any).details) {
      (target.execution_result as any).details = (result as any).details;
    }
    (target.execution_result as any).raw_status = result.status;

    await saveDecisions(decisions);

    return NextResponse.json({ ok: true, decision: target });
  } catch (e: any) {
    return NextResponse.json({ error: String(e.message || e) }, { status: 500 });
  }
}
