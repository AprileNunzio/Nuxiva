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

export const panelClass = 'os-card p-5 border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] text-[var(--md-sys-color-on-surface)] rounded-2xl shadow-sm';
export const buttonClass = 'os-btn text-xs font-semibold py-2 px-4';

export const labelClass = 'mb-3 font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--md-sys-color-on-surface-variant)]';
export const mutedClass = 'text-[var(--md-sys-color-on-surface-variant)]';

export const TONE: Readonly<Record<string, string>> = {
  ok: 'text-emerald-500',
  done: 'text-emerald-500',
  warn: 'text-amber-500',
  skipped: 'text-[var(--md-sys-color-on-surface-variant)]',
  error: 'text-rose-500',
  failed: 'text-rose-500',
  running: 'text-[var(--md-sys-color-primary)]',
  info: 'text-[var(--md-sys-color-on-surface-variant)]',
  pending: 'text-[var(--md-sys-color-on-surface-variant)] opacity-60',
};

export const tone = (key: string): string => TONE[key] ?? TONE.info;
