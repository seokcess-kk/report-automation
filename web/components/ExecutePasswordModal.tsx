'use client';
import { useEffect, useState } from 'react';
import { DecisionRecord } from './ActionDetailModal';
import { Button } from './ui';

type Adgroup = { adgroup_id: string; adgroup_name: string; budget: number; budget_mode: string; operation_status: string };
type Ad = { ad_id: string; ad_name: string; status: string };

export function ExecutePasswordModal({
  decision, onClose, onExecuted,
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
          const rec = p.recommended_value || {};
          const totalCur = ags.reduce((s: number, a: Adgroup) => s + (a.budget || 0), 0);
          const totalProp = rec.proposed || totalCur;
          const ratio = totalCur > 0 ? totalProp / totalCur : 1;
          const defaults: Record<string, number> = {};
          for (const ag of ags) defaults[ag.adgroup_id] = Math.round((ag.budget || 0) * ratio);
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
    if (!password) { setError('비밀번호를 입력하세요.'); return; }
    setSubmitting(true); setError(null);
    try {
      const body: any = { decision_id: decision.id, admin_password: password };
      if (isBudget) body.budget_overrides = budgetOverrides;
      const res = await fetch('/api/actions/execute', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const j = await res.json();
      if (!res.ok) throw new Error(j.error || `HTTP ${res.status}`);
      onExecuted(j.decision);
    } catch (e: any) { setError(String(e.message || e)); }
    finally { setSubmitting(false); }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in" onClick={onClose}>
      <div className="bg-surface border border-border-strong rounded-xl shadow-raised w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 bg-surface/95 backdrop-blur border-b border-border px-5 py-4 flex items-center justify-between">
          <h3 className="text-base font-semibold text-fg">실행 확인</h3>
          <button type="button" onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-md text-muted hover:text-fg hover:bg-elevated">✕</button>
        </div>

        <div className="p-5 space-y-4">
          <div className="bg-elevated/50 border border-border rounded-lg px-4 py-3">
            <div className="text-2xs text-subtle uppercase tracking-wider mb-1">대상</div>
            <div className="text-sm font-semibold text-fg">{p.title}</div>
          </div>

          {isManual && (
            <div className="text-xs text-info bg-info-soft/40 border border-info-soft rounded-md px-3 py-2">
              이 액션 타입은 TikTok API 자동 실행 미지원입니다. 실행 시 "수동 조정 안내"로 기록됩니다.
            </div>
          )}

          {loadingPreview && <div className="text-sm text-muted">대상 정보 불러오는 중...</div>}

          {!loadingPreview && isBudget && (
            <div>
              <div className="text-2xs text-subtle uppercase tracking-wider font-semibold mb-2">
                adgroup별 예산 설정 ({adgroups.length}개)
              </div>
              {adgroups.length === 0 ? (
                <div className="text-sm text-danger">⚠️ "{p.target}" 지점의 adgroup을 찾지 못했습니다.</div>
              ) : (
                <>
                  <div className="grid grid-cols-[1fr_auto_auto] gap-2 text-2xs text-subtle px-3 mb-1">
                    <div>adgroup</div>
                    <div className="text-right">현재 (원)</div>
                    <div className="text-right w-32">신규 예산 (원)</div>
                  </div>
                  <div className="space-y-1 max-h-64 overflow-y-auto">
                    {adgroups.map((ag) => (
                      <div key={ag.adgroup_id} className="grid grid-cols-[1fr_auto_auto] gap-2 items-center bg-elevated/40 border border-border rounded-md px-3 py-2">
                        <div className="text-xs text-fg truncate">{ag.adgroup_name}</div>
                        <div className="text-xs font-mono text-subtle text-right tabular-nums">{ag.budget.toLocaleString()}</div>
                        <input
                          type="number"
                          step={10000}
                          value={budgetOverrides[ag.adgroup_id] ?? ag.budget}
                          onChange={(e) => setBudgetOverrides({ ...budgetOverrides, [ag.adgroup_id]: Number(e.target.value) })}
                          className="w-32 bg-surface border border-border-strong rounded px-2 py-1 text-xs text-right font-mono tabular-nums text-fg focus:border-accent"
                        />
                      </div>
                    ))}
                  </div>
                  <div className="text-2xs text-subtle mt-2">기본값은 제안 비율 적용값. 필요 시 각 입력란을 수정하세요.</div>
                </>
              )}
            </div>
          )}

          {!loadingPreview && isCreative && (
            <div>
              <div className="text-2xs text-subtle uppercase tracking-wider font-semibold mb-2">대상 광고 ({ads.length}개)</div>
              {ads.length === 0 ? (
                <div className="text-sm text-danger">⚠️ "{p.target}"에 매칭되는 광고를 찾지 못했습니다.</div>
              ) : (
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {ads.map((a) => (
                    <div key={a.ad_id} className="flex items-center justify-between bg-elevated/40 border border-border rounded px-3 py-2 text-xs">
                      <span className="truncate text-fg">{a.ad_name}</span>
                      <span className="text-2xs text-subtle shrink-0 ml-2">{a.status}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="text-xs text-warn bg-warn-soft/30 border border-warn-soft/60 rounded-md px-3 py-2">
            ⚠️ 실제 TikTok API 호출이 이뤄집니다. 되돌리려면 반대 액션을 별도로 실행해야 합니다.
          </div>

          <label className="block">
            <span className="text-2xs text-subtle uppercase tracking-wider font-semibold">관리 비밀번호</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
              autoFocus
              className="w-full mt-1.5 bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-fg focus:border-accent"
            />
          </label>

          {error && <div className="text-xs text-danger bg-danger-soft/30 border border-danger-soft rounded px-3 py-2">⚠️ {error}</div>}

          <div className="flex items-center justify-end gap-2 pt-2">
            <Button variant="ghost" onClick={onClose} disabled={submitting}>취소</Button>
            <Button variant="danger" onClick={submit} disabled={submitting || !password}>
              {submitting ? '실행 중…' : '실행'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
