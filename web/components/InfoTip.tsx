/** 간단한 hover tooltip — 용어/기준 설명용.
 *
 * Usage:
 *   <InfoTip text="효율점수 = 전환비중 / 비용비중" />
 *   <InfoTip text="..."><span>CPA</span></InfoTip>
 */
export function InfoTip({ text, children }: { text: string; children?: React.ReactNode }) {
  return (
    <span className="relative inline-flex group items-center gap-1 align-middle">
      {children}
      <span
        className="inline-flex w-3.5 h-3.5 text-[9px] items-center justify-center rounded-full bg-brand-bg border border-brand-border text-slate-400 cursor-help"
        aria-label="정보"
      >
        ⓘ
      </span>
      <span
        role="tooltip"
        className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 z-40
                   hidden group-hover:block
                   bg-brand-bg border border-brand-border rounded
                   text-[11px] text-slate-200 font-normal
                   px-2 py-1 whitespace-pre-line max-w-xs text-left
                   shadow-lg pointer-events-none"
      >
        {text}
      </span>
    </span>
  );
}
