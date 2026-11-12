import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function useBoardI18n() {
  return useScopedI18n('node_apps/whiteboard');
}

export type Tool = 'pen' | 'eraser' | 'text';

export const fieldClass =
  'rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-cyan-400/70 focus-visible:ring-2 focus-visible:ring-cyan-400/40';
