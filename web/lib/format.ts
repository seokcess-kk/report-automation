export const fmt = (n: number | null | undefined, unit = ''): string =>
  n == null || !isFinite(n as number) ? '-' : `${Math.round(n as number).toLocaleString()}${unit}`;

export const fmtMan = (n: number | null | undefined): string =>
  n == null ? '-' : `${(n / 10000).toFixed(1)}만`;

export const fmtPct = (n: number | null | undefined, digits = 2): string =>
  n == null || !isFinite(n as number) ? '-' : `${(n as number).toFixed(digits)}%`;

export const fmtDiff = (n: number | null | undefined, unit = '원'): string => {
  if (n == null || n === 0) return '-';
  const sign = n > 0 ? '▲+' : '▼';
  return `${sign}${Math.abs(Math.round(n)).toLocaleString()}${unit}`;
};

export function diffColor(n: number | null | undefined, invert = false): string {
  if (n == null || n === 0) return 'text-slate-400';
  const isGood = invert ? n < 0 : n > 0;
  return isGood ? 'text-brand-success' : 'text-brand-danger';
}
