import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function usePeopleI18n() {
  return useScopedI18n('core_apps/people');
}

export const fieldClass =
  'w-full rounded-xl border border-outline bg-surface-container-lowest px-3 py-2 text-sm text-on-surface placeholder:text-on-surface-variant outline-none transition focus:border-primary focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-50';
export const panelClass = 'md-enter rounded-3xl bg-surface-container-low p-4 sm:p-5';
export const chipClass =
  'md-state flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold disabled:opacity-50';
export const primaryClass =
  'md-state flex items-center justify-center gap-2 rounded-full border-0 bg-primary px-5 py-2 text-sm font-semibold text-on-primary shadow-[var(--md-elevation-1)] disabled:opacity-50';

export const PERMISSION_KEYS = ['role', 'membership', 'business_role', 'subrole', 'authorization', 'allowed_zones', 'allowed_schedule', 'consent', 'share_health', 'camera_vitals'] as const;

export function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase() ?? '').join('') || '?';
}

export function relative(epochSeconds: number | null, lang: string, nowMs = Date.now()): string {
  if (!epochSeconds) {
    return '';
  }
  const delta = Math.round(epochSeconds - nowMs / 1000);
  const units: [Intl.RelativeTimeFormatUnit, number][] = [['day', 86400], ['hour', 3600], ['minute', 60], ['second', 1]];
  const [unit, size] = units.find(([, s]) => Math.abs(delta) >= s) ?? units[3];
  return new Intl.RelativeTimeFormat(lang, { numeric: 'auto' }).format(Math.round(delta / size), unit);
}

export function localLabel(t: (key: string) => string, lang: string, key: string, fallback: string): string {
  if (lang.toLowerCase().startsWith('it')) {
    return fallback;
  }
  const value = t(key);
  return value === key ? fallback : value;
}
