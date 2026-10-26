import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function useAgentsI18n() {
  return useScopedI18n('core_apps/agents');
}

export const fieldClass =
  'rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-cyan-300 focus-visible:ring-2 focus-visible:ring-cyan-300 disabled:opacity-50';

export const panelClass = 'rounded-2xl border border-slate-200 bg-gradient-to-br from-white to-white p-4 sm:p-5';

export const chipClass =
  'flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-semibold transition disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400';

export const primaryClass =
  'flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-4 py-2 text-sm font-bold text-slate-950 transition hover:brightness-110 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200';

export function tone(priority: number): string {
  return priority >= 90 ? 'text-rose-700 border-rose-300' : priority >= 60 ? 'text-amber-800 border-amber-300' : 'text-cyan-800 border-cyan-300';
}
