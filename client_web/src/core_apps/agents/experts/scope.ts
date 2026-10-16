import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';

export function useExpertsI18n() {
  return useScopedI18n('core_apps/agents/experts');
}

export const glassClass =
  'relative overflow-hidden rounded-2xl border border-cyan-400/15 bg-gradient-to-br from-slate-900/80 via-slate-950/90 to-indigo-950/40 p-4 shadow-[0_0_40px_rgba(34,211,238,0.06)] backdrop-blur sm:p-5';

export const labelClass = 'mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400';

export const GIB = 1024 ** 3;

export const fieldClass =
  'rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-cyan-400/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400';
