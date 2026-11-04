import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function useBluetoothI18n() {
  return useScopedI18n('node_apps/bluetooth');
}

export const fieldClass =
  'w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-2xs outline-none transition focus:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500/30 disabled:opacity-60';

export const buttonClass =
  'inline-flex items-center justify-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500';

export const tones = {
  primary: 'border-blue-600 bg-blue-600 text-white hover:bg-blue-700',
  positive: 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100',
  neutral: 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
  danger: 'border-transparent bg-transparent text-slate-400 hover:bg-rose-50 hover:text-rose-600',
} as const;
