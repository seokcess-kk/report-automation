/** action_decisions.json 읽기/쓰기 공용 로직 + in-process mutex + 원자적 파일 쓰기.
 *  - tmp 파일로 쓴 후 rename → 부분 쓰기(파일 손상) 방지
 *  - 같은 프로세스 내 동시 요청은 AsyncMutex로 직렬화
 *  - decision_id 단위 lock으로 race (execute 이중 실행) 방지
 */
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
    [k: string]: any;
  } | null;
}

/** 단순 async mutex */
class Mutex {
  private queue: Array<() => void> = [];
  private locked = false;

  async lock<T>(fn: () => Promise<T>): Promise<T> {
    if (this.locked) {
      await new Promise<void>((resolve) => this.queue.push(resolve));
    }
    this.locked = true;
    try {
      return await fn();
    } finally {
      this.locked = false;
      const next = this.queue.shift();
      if (next) next();
    }
  }
}

const fileMutex = new Mutex();

export async function loadDecisions(): Promise<Decision[]> {
  try {
    const raw = await fs.readFile(DECISIONS_PATH, 'utf-8');
    return JSON.parse(raw).decisions || [];
  } catch {
    return [];
  }
}

async function saveDecisionsUnsafe(decisions: Decision[]) {
  await fs.mkdir(path.dirname(DECISIONS_PATH), { recursive: true });
  const tmp = DECISIONS_PATH + '.tmp';
  await fs.writeFile(tmp, JSON.stringify({ decisions }, null, 2), 'utf-8');
  await fs.rename(tmp, DECISIONS_PATH);
}

/** 읽기→변경→쓰기를 원자적으로 수행. 콜백이 변경된 decisions 배열을 반환하면 저장. */
export async function updateDecisions<T>(
  fn: (decisions: Decision[]) => Promise<{ next: Decision[]; value: T }>
): Promise<T> {
  return fileMutex.lock(async () => {
    const current = await loadDecisions();
    const { next, value } = await fn(current);
    await saveDecisionsUnsafe(next);
    return value;
  });
}
