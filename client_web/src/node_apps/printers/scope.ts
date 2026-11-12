import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function usePrintersI18n() {
  return useScopedI18n('node_apps/printers');
}

export const fieldClass =
  'w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-cyan-400 focus:outline-none';
