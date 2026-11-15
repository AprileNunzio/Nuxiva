export type Translate = (key: string, params?: Record<string, string | number>) => string;

const HASH_PREFIX = /^[0-9a-f]{8,}[._-]/;
const KNOWN_COMPONENTS = new Set(['browser', 'nuxiva-core', 'ollama', 'whisper', 'tts', 'vision', 'database']);

export function readableId(id: string): string {
  const stripped = id.replace(HASH_PREFIX, '').replace(/[._-]+/g, ' ').trim();
  if (!stripped) return id;
  return stripped.charAt(0).toUpperCase() + stripped.slice(1);
}

export function componentLabel(id: string, t: Translate): string {
  return KNOWN_COMPONENTS.has(id) ? t(`res_name_${id.replace(/-/g, '_')}`) : readableId(id);
}

export function tierLabel(tier: string | undefined, t: Translate): string {
  if (!tier) return '';
  const match = /^Tier-(\d)/i.exec(tier);
  if (!match) return tier;
  return match[1] === '1' ? t('tier_main') : match[1] === '2' ? t('tier_edge') : t('tier_light');
}

export interface Grouped<T> {
  readonly item: T;
  readonly count: number;
}

export function groupRepeats<T>(items: readonly T[], keyOf: (item: T) => string): Grouped<T>[] {
  const order: string[] = [];
  const seen = new Map<string, Grouped<T>>();
  for (const item of items) {
    const key = keyOf(item);
    const hit = seen.get(key);
    if (hit) {
      seen.set(key, { item: hit.item, count: hit.count + 1 });
    } else {
      order.push(key);
      seen.set(key, { item, count: 1 });
    }
  }
  return order.flatMap((key) => {
    const entry = seen.get(key);
    return entry ? [entry] : [];
  });
}
