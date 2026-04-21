'use client';
import { useEffect, useState } from 'react';
import { DecisionRecord } from './ActionDetailModal';

type Adgroup = {
  adgroup_id: string;
  adgroup_name: string;
  budget: number;
  budget_mode: string;
  operation_status: string;
};

type Ad = {
  ad_id: string;
  ad_name: string;
  status: string;
};

export function ExecutePasswordModal({
  decision,
  onClose,
  onExecuted,
}: {
  decision: DecisionRecord;
  onClose: () => void;
  onExecuted: (d: DecisionRecord) => void;
}) {
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [adgroups, setAdgroups] = useState<Adgroup[]>([]);
  const [ads, setAds] = useState<Ad[]>([]);
  const [budgetOverrides, setBudgetOverrides] = useState<Record<string, number>>({});
  const [loadingPreview, setLoadingPreview] = useState(true);

  const p = decision.proposal_snapshot || {};
  const actionType = p.action_type as string;
  const isBudget = actionType === 'budget_decrease' || actionType === 'budget_increase';
  const isCreative = actionType === 'pause_creative' || actionType === 'reactivate_creative';
  const isManual = [
    'creative_review', 'scale_creative', 'exclude_age', 'expand_age',
    'dayparting', 'weekday_boost', 'type_scale', 'budget_reallocate',
  ].includes(actionType);

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [onClose]);

  useEffect(() => {
    if (isBudget) {
      fetch(`/api/actions/preview?branch=${encodeURIComponent(p.target)}`)
        .then((r) => r.json())
        .then((j) => {
          const ags = j.adgroups || [];
          setAdgroups(ags);
          // 제안 비율 계산: 총 예산을 현재 예산으로 나눈 비율
          const rec = p.recommended_value || {};
          const totalCur = ags.reduce((s: number, a: Adgroup) => s + (a.budget || 0), 0);
          const totalProp = rec.proposed || totalCur;
          const ratio = totalCur > 0 ? totalProp / totalCur : 1;
          const defaults: Record<string, number> = {};
          for (const ag of ags) {
            defaults[ag.adgroup_id] = Math.round((ag.budget || 0) * ratio);
          }
          setBudgetOverrides(defaults);
        })
        .catch((e) => setError(String(e)))
        .finally(() => setLoadingPreview(false));
    } else if (isCreative) {
      fetch(`/api/actions/preview?creative=${encodeURIComponent(p.target)}`)
        .then((r) => r.json())
        .then((j) => setAds(j.ads || []))
        .catch((e) => setError(String(e)))
        .finally(() => setLoadingPreview(false));
    } else {
      setLoadingPreview(false);
    }
  }, [actionType, p.target, isBudget, isCreative]);

  async function submit() {
    if (!password) {
      setError('비밀번호를 입력하세요.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const body: any = {
        decision_id: decision.id,
        admin_password: password,
      };
      if (isBudget) {
        body.budget_overrides = budgetOverrides;
      }
      const res = await fetch('/api/actions/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const j = await res.json();
      if (!res.ok) throw new Error(j.error || `HTTP ${res.status}`);
      onExecuted(j.decision);
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div className="card w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-3">
          <h3 className="font-bold">실행 확인</h3>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-white">✕</button>
        </div>

        <div className="text-sm text-slate-300 mb-3 bg-brand-bg/60 rounded p-3">
          <div className="text-xs text-slate-500 mb-1">대상</div>
          <div className="font-semibold">{p.title}</div>
        </div>

        {isManual && (
          <div className="text-xs text-sky-300 bg-sky-900/20 rounded p-3 mb-3">
            ℹ️ 이 액션 타입은 TikTok API 자동 실행 미지원입니다. 실행 시 "수동 조정 안내"로 기록됩니다.
          </div>
        )}

        {loadingPreview && <div className="text-sm text-slate-500 mb-3">대상 정보 불러오는 중...</div>}

        {!loadingPreview && isBudget && (
          <div className="mb-4">
            <div className="text-xs text-slate-400 mb-2 font-semibold">
              adgroup별 예산 설정 ({adgroups.length}개)
            </div>
            {adgroups.length === 0 ? (
              <div className="text-sm text-brand-danger">
                ⚠️ "{p.target}" 지점의 adgroup을 찾지 못했습니다. ad_mapping 갱신 필요.
              </div>
            ) : (
              <>
                <div className="grid grid-cols-[1fr_auto_auto] gap-2 text-[10px] text-slate-500 mb-1 px-2">
                  <div>adgroup</div>
                  <div className="text-right">현재 (원)</div>
                  <div className="text-right w-32">신규 예산 (원)</div>
                </div>
                <div className="space-y-1 max-h-64 overflow-y-auto">
                  {adgroups.map((ag) => (
                    <div key={ag.adgroup_id} className="grid grid-cols-[1fr_auto_auto] gap-2 items-center bg-brand-bg/40 rounded px-2 py-1.5">
                      <div className="text-xs text-slate-300 truncate">{ag.adgroup_name}</div>
                      <div className="text-xs font-mono text-slate-400 text-right">{ag.budget.toLocaleString()}</div>
                      <input
                        type="number"
                        step={10000}
                        value={budgetOverrides[ag.adgroup_id] ?? ag.budget}
                        onChange={(e) => setBudgetOverrides({ ...budgetOverrides, [ag.adgroup_id]: Number(e.target.value) })}
                        className="w-32 bg-brand-bg border border-brand-border rounded px-2 py-1 text-xs text-right font-mono"
                      />
                    </div>
                  ))}
                </div>
                <div className="text-[10px] text-slate-500 mt-2">
                  기본값은 제안 비율이 균등 적용된 값입니다. 필요 시 각 입력란을 수정하세요.
                </div>
              </>
            )}
          </div>
        )}

        {!loadingPreview && isCreative && (
          <div className="mb-4">
            <div className="text-xs text-slate-400 mb-2 font-semibold">
              대상 광고 ({ads.length}개)
            </div>
            {ads.length === 0 ? (
              <div className="text-sm text-brand-danger">
                ⚠️ "{p.target}"에 매칭되는 광고를 찾지 못했습니다.
              </div>
            ) : (
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {ads.map((a) => (
                  <div key={a.ad_id} className="flex items-center justify-between bg-brand-bg/40 rounded px-2 py-1.5 text-xs">
                    <span className="truncate">{a.ad_name}</span>
                    <span className="text-[10px] text-slate-500 shrink-0 ml-2">{a.status}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="text-xs text-brand-warn bg-amber-900/20 rounded p-2 mb-3">
          ⚠️ 실행 시 실제 TikTok API 호출이 이뤄집니다. 되돌리려면 반대 액션을 별도로 실행해야 합니다.
        </div>

        <label className="block mb-3">
          <span className="text-xs text-slate-400">관리 비밀번호</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
            autoFocus
            className="w-full mt-1 bg-brand-bg border border-brand-border rounded px-3 py-2 text-sm"
          />
        </label>

        {error && <div className="text-xs text-brand-danger mb-2">⚠️ {error}</div>}

        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="px-3 py-1.5 text-sm rounded border border-brand-border text-slate-300 hover:bg-brand-bg"
          >
            취소
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={submitting || !password}
            className="px-3 py-1.5 text-sm rounded bg-brand-danger text-white font-semibold hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? '실행 중…' : '실행'}
          </button>
        </div>
      </div>
    </div>
  );
}
