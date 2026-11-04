import { NodeModuleError, asRecord, asString, requestJson } from '../../../node_apps/shared/data/http';
import { SLUG } from './peopleApi';

export interface Fill {
  readonly filled: number;
  readonly total: number;
}

export interface Overview {
  readonly since: number | null;
  readonly sections: Readonly<Record<string, Fill>>;
  readonly face: number;
  readonly voice: boolean;
  readonly health: { readonly metrics: number; readonly heartRate: number | null; readonly recovery: number | null; readonly signals: number };
  readonly mood: { readonly entries: number; readonly last: string; readonly at: number | null };
  readonly memories: { readonly count: number; readonly last: string };
  readonly learned: number;
  readonly habits: { readonly summary: string; readonly visits: number };
  readonly connectors: readonly string[];
}

const num = (value: unknown): number | null => (typeof value === 'number' && Number.isFinite(value) ? value : null);
const MOOD = /^[a-z]{2,20}$/;
const ID = /^[a-z0-9_-]{1,40}$/;

export function parseOverview(value: unknown): Overview {
  const raw = asRecord(value);
  const health = asRecord(raw.health);
  const mood = asRecord(raw.mood);
  const last = asRecord(mood.last);
  const memories = asRecord(raw.memories);
  const habits = asRecord(raw.habits);
  const sections = Object.fromEntries(
    Object.entries(asRecord(raw.sections))
      .filter(([k]) => ID.test(k))
      .map(([k, v]) => {
        const f = asRecord(v);
        return [k, { filled: Math.max(0, num(f.filled) ?? 0), total: Math.max(0, num(f.total) ?? 0) }];
      }),
  );
  const moodName = asString(last.mood, 20) ?? '';
  return {
    since: num(raw.since),
    sections,
    face: Math.max(0, Math.min(100, num(asRecord(raw.face).quality) ?? 0)),
    voice: asRecord(raw.voice).enrolled === true,
    health: { metrics: num(health.metrics) ?? 0, heartRate: num(health.heart_rate), recovery: num(health.recovery), signals: num(health.signals) ?? 0 },
    mood: { entries: num(mood.entries) ?? 0, last: MOOD.test(moodName) ? moodName : '', at: num(last.at) },
    memories: { count: num(memories.count) ?? 0, last: asString(memories.last, 200) ?? '' },
    learned: num(asRecord(raw.learned).count) ?? 0,
    habits: { summary: asString(habits.summary, 200) ?? '', visits: num(habits.visits) ?? 0 },
    connectors: (Array.isArray(asRecord(raw.connectors).linked) ? (asRecord(raw.connectors).linked as unknown[]) : [])
      .map((v) => String(v ?? ''))
      .filter((v) => ID.test(v))
      .slice(0, 20),
  };
}

export async function fetchOverview(slug: string, signal?: AbortSignal): Promise<Overview> {
  if (!SLUG.test(slug)) {
    throw new NodeModuleError('invalid_person', 400);
  }
  return parseOverview(await requestJson<unknown>(`/api/people/${encodeURIComponent(slug)}/overview`, { signal }));
}
