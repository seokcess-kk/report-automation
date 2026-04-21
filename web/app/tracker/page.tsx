import { loadLatestTracker } from '@/lib/reports';
import { PaceHeader } from '@/components/PaceHeader';
import { TrackerClient } from '@/components/TrackerClient';
import { AnalysisTabs } from '@/components/AnalysisTabs';

export const dynamic = 'force-dynamic';

export default async function TrackerPage() {
  const tracker = await loadLatestTracker();

  if (!tracker) {
    return (
      <div className="card">
        <h1 className="text-xl font-bold mb-2">목표 달성 트래커</h1>
        <p className="text-slate-400 text-sm">
          트래커 데이터가 아직 생성되지 않았습니다. <code>python run_analysis.py</code> 실행 후 이용하세요.
        </p>
      </div>
    );
  }

  const { pace, proposals, segments } = tracker;

  return (
    <div className="space-y-6">
      <PaceHeader pace={pace} />
      <TrackerClient pace={pace} proposals={proposals} />
      {segments && <AnalysisTabs segments={segments} />}
    </div>
  );
}
