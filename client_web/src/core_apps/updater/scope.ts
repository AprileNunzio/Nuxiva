import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function useUpdaterI18n() {
  return useScopedI18n('core_apps/updater');
}

export function formatDateTime(value: string | number | null, locale: string): string | null {
  if (value === null) {
    return null;
  }
  const date = typeof value === 'number' ? new Date(value * 1000) : new Date(value);
  return Number.isNaN(date.getTime())
    ? null
    : new Intl.DateTimeFormat(locale, { dateStyle: 'short', timeStyle: 'short' }).format(date);
}

export const shortRev = (rev: string | null): string | null => (rev ? rev.slice(0, 7) : null);

export const panelClass = 'rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-900/70 to-slate-950/90 p-4 sm:p-5';
export const buttonClass =
  'flex items-center justify-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-semibold transition disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400';
