import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function usePeopleI18n() {
  return useScopedI18n('core_apps/people');
}

export const fieldClass =
  'w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-cyan-400/70 focus-visible:ring-2 focus-visible:ring-cyan-400/40 disabled:opacity-50';
export const panelClass = 'rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-900/70 to-slate-950/90 p-4 sm:p-5';
export const chipClass =
  'flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-semibold transition disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400';
export const primaryClass =
  'flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-4 py-2 text-sm font-bold text-slate-950 transition hover:brightness-110 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200';

export const PERMISSION_KEYS = ['role', 'membership', 'business_role', 'subrole', 'authorization', 'allowed_zones', 'allowed_schedule', 'consent', 'share_health'] as const;

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
