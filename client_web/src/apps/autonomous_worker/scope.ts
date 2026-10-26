import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function useAutonomousI18n() {
  return useScopedI18n('apps/autonomous_worker');
}

export const inputFieldClass =
  'w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-cyan-400/70 focus-visible:ring-2 focus-visible:ring-cyan-400/40 disabled:opacity-50';

export const primaryBtnClass =
  'inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-cyan-500 active:scale-95 disabled:pointer-events-none disabled:opacity-50';

export const secondaryBtnClass =
  'inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm font-medium text-slate-200 transition hover:bg-slate-800 active:scale-95 disabled:pointer-events-none disabled:opacity-50';
