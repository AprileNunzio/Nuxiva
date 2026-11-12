export function clock(ms: number, lang: string, withSeconds = true): string {
  return new Intl.DateTimeFormat(lang, {
    hour: '2-digit',
    minute: '2-digit',
    second: withSeconds ? '2-digit' : undefined,
  }).format(new Date(ms));
}

export function dayLabel(ms: number, lang: string): string {
  return new Intl.DateTimeFormat(lang, { weekday: 'short', day: 'numeric', month: 'short' }).format(new Date(ms));
}

export function bytes(value: number, lang: string): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = Math.max(0, value);
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${new Intl.NumberFormat(lang, { maximumFractionDigits: unit ? 1 : 0 }).format(size)} ${units[unit]}`;
}

export const ZOOMS = [
  { key: 'zoom_1h', ms: 3_600_000 },
  { key: 'zoom_6h', ms: 21_600_000 },
  { key: 'zoom_24h', ms: 86_400_000 },
  { key: 'zoom_7d', ms: 604_800_000 },
] as const;

export const KIND_GROUPS: Record<string, string[]> = {
  all: [],
  people: ['person', 'face'],
  vehicles: ['car', 'truck', 'motorcycle', 'bicycle', 'license_plate'],
  speech: ['speech'],
  motion: ['motion'],
  animals: ['dog', 'cat', 'bird'],
};

export function markerTone(kind: string): string {
  if (KIND_GROUPS.people.includes(kind)) return 'bg-primary';
  if (KIND_GROUPS.vehicles.includes(kind)) return 'bg-secondary';
  if (kind === 'speech') return 'bg-tertiary';
  if (KIND_GROUPS.animals.includes(kind)) return 'bg-tertiary-container';
  return 'bg-outline';
}
