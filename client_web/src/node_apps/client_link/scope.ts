import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function useLinkI18n() {
  return useScopedI18n('node_apps/client_link');
}

const UNITS: readonly (readonly [Intl.RelativeTimeFormatUnit, number])[] = [
  ['day', 86400],
  ['hour', 3600],
  ['minute', 60],
  ['second', 1],
];

export function relativeTime(epochSeconds: number, nowMs: number, lang: string): string {
  const delta = Math.round(epochSeconds - nowMs / 1000);
  const [unit, size] = UNITS.find(([, s]) => Math.abs(delta) >= s) ?? UNITS[UNITS.length - 1];
  return new Intl.RelativeTimeFormat(lang, { numeric: 'auto' }).format(Math.round(delta / size), unit);
}

export function duration(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return d > 0 ? `${d}d ${h}h` : h > 0 ? `${h}h ${m}m` : `${m}m`;
}
