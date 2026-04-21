import { loadLatestTracker } from '@/lib/reports';
import { PaceHeader } from '@/components/PaceHeader';
import { TrackerClient } from '@/components/TrackerClient';

export const dynamic = 'force-dynamic';

export default async function TrackerPage() {
  const tracker = await loadLatestTracker();

  if (!tracker) {
    return (
      <div className="bg-surface border border-border rounded-xl p-8 text-center">
        <h1 className="text-xl font-bold text-fg mb-2">목표 달성 트래커</h1>
        <p className="text-muted text-sm">
          트래커 데이터가 아직 생성되지 않았습니다. <code className="bg-elevated px-1.5 py-0.5 rounded text-xs">python run_analysis.py</code> 실행 후 이용하세요.
        </p>
      </div>
    );
  }

  const { pace, proposals, segments } = tracker;

  return (
    <div className="space-y-8 animate-fade-in">
      <PaceHeader pace={pace} />
      <TrackerClient pace={pace} proposals={proposals} segments={segments} />
    </div>
  );
}
