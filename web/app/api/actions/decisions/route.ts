import { NextResponse } from 'next/server';
import fs from 'node:fs/promises';
import path from 'node:path';

const OUTPUT_DIR = path.join(process.cwd(), '..', 'output');
const DECISIONS_PATH = path.join(OUTPUT_DIR, 'action_decisions.json');

export interface Decision {
  id: string;
  proposal_id: string;
  proposal_snapshot: any;
  decision: 'approve' | 'reject';
  queued: boolean;
  decided_at: string;
  decided_by: string;
  note: string;
  executed: boolean;
  executed_at: string | null;
  execution_result: {
    status: 'success' | 'failed';
    message: string;
    dry_run: boolean;
  } | null;
}

async function loadDecisions(): Promise<Decision[]> {
  try {
    const raw = await fs.readFile(DECISIONS_PATH, 'utf-8');
    const parsed = JSON.parse(raw);
    return parsed.decisions || [];
  } catch {
    return [];
  }
}

async function saveDecisions(decisions: Decision[]) {
  await fs.mkdir(path.dirname(DECISIONS_PATH), { recursive: true });
  await fs.writeFile(
    DECISIONS_PATH,
    JSON.stringify({ decisions }, null, 2),
    'utf-8'
  );
}

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

    const decisions = await loadDecisions();
    const filtered = decisions.filter((d) => d.proposal_id !== proposal.id);

    const newDecision: Decision = {
      id: nextId(filtered),
      proposal_id: proposal.id,
      proposal_snapshot: proposal,
      decision,
      queued: decision === 'approve' && !!queued,
      decided_at: new Date().toISOString(),
      decided_by: 'local',
      note: note || '',
      executed: false,
      executed_at: null,
      execution_result: null,
    };

    filtered.push(newDecision);
    await saveDecisions(filtered);

    return NextResponse.json({ ok: true, decision: newDecision });
  } catch (e: any) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
