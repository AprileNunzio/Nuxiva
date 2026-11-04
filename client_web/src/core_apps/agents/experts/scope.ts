import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';

export function useExpertsI18n() {
  return useScopedI18n('core_apps/agents/experts');
}

export const glassClass =
  'relative overflow-hidden rounded-2xl border border-cyan-300 bg-gradient-to-br from-white via-white to-indigo-50 p-4 shadow-sm backdrop-blur sm:p-5';

export const labelClass = 'mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-600';

export const GIB = 1024 ** 3;

export const fieldClass =
  'rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 placeholder:text-slate-500 focus:border-cyan-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400';
