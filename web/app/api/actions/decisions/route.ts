import { NextResponse } from 'next/server';
import { Decision, loadDecisions, updateDecisions } from '@/lib/decisions-store';

export type { Decision };

function nextId(decisions: Decision[]): string {
  const max = decisions.reduce((m, d) => {
    const n = parseInt(d.id.replace(/\D/g, ''), 10);
    return isFinite(n) ? Math.max(m, n) : m;
  }, 0);
  return `d${String(max + 1).padStart(3, '0')}`;
}

export async function GET() {
  const decisions = await loadDecisions();
  return NextResponse.json({ decisions });
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { proposal, decision, note, queued } = body as {
      proposal: any;
      decision: 'approve' | 'reject';
      note?: string;
      queued?: boolean;
    };

    if (!proposal?.id || !['approve', 'reject'].includes(decision)) {
      return NextResponse.json({ error: 'invalid payload' }, { status: 400 });
    }

    const newDecision = await updateDecisions(async (current) => {
      const filtered = current.filter((d) => d.proposal_id !== proposal.id);
      const created: Decision = {
        id: nextId(filtered),
        proposal_id: proposal.id,
        proposal_snapshot: proposal,
        decision,
        queued: decision === 'approve' && !!queued,
        decided_at: new Date().toISOString(),
        decided_by: 'local',
        note: typeof note === 'string' ? note : '',
        executed: false,
        executed_at: null,
        execution_result: null,
      };
      filtered.push(created);
      return { next: filtered, value: created };
    });

    return NextResponse.json({ ok: true, decision: newDecision });
  } catch (e: any) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
