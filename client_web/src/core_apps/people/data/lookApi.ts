import { asRecord, asString, requestJson } from '../../../node_apps/shared/data/http';

export const LOOK_KINDS = ['glasses', 'beard', 'fringe', 'hair_color', 'smoking', 'smoker'] as const;
export type LookKind = (typeof LOOK_KINDS)[number];
export const HAIR_COLORS = ['black', 'brown', 'grey', 'white', 'red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'purple', 'pink'] as const;
export type HairColor = (typeof HAIR_COLORS)[number];
export type LookStatus = 'auto' | 'confirmed' | 'rejected';

export interface LookSummary {
  readonly glasses: boolean;
  readonly beard: boolean;
  readonly fringe: boolean;
  readonly hair: HairColor | null;
  readonly smoker: boolean;
  readonly smokingEpisodes: number;
  readonly observations: number;
}

export interface LookEvent {
  readonly id: string;
  readonly at: number;
  readonly kind: LookKind;
  readonly value: string;
  readonly previous: string | null;
  readonly status: LookStatus;
}

export interface LookDetails {
  readonly available: boolean;
  readonly consent: boolean;
  readonly summary: LookSummary | null;
  readonly events: readonly LookEvent[];
}

const ID = /^[0-9a-f]{10}$/;
const VALUE = /^[a-z]{1,16}$/;
const STATUSES: readonly LookStatus[] = ['auto', 'confirmed', 'rejected'];
const isKind = (value: unknown): value is LookKind => LOOK_KINDS.includes(value as LookKind);
const isHair = (value: unknown): value is HairColor => HAIR_COLORS.includes(value as HairColor);
const count = (value: unknown): number => (typeof value === 'number' && Number.isFinite(value) && value >= 0 ? Math.floor(value) : 0);
const word = (value: unknown): string | null => {
  const text = asString(value, 16);
  return text && VALUE.test(text) ? text : null;
};

function summaryOf(raw: unknown): LookSummary | null {
  if (raw === null || typeof raw !== 'object') {
    return null;
  }
  const s = asRecord(raw);
  return {
    glasses: s.glasses === true,
    beard: s.beard === true,
    fringe: s.fringe === true,
    hair: isHair(s.hair) ? s.hair : null,
    smoker: s.smoker === true,
    smokingEpisodes: count(s.smoking_episodes),
    observations: count(s.observations),
  };
}

function eventOf(raw: unknown): LookEvent[] {
  const e = asRecord(raw);
  const id = asString(e.id, 10);
  const value = word(e.value);
  const status = STATUSES.find((s) => s === e.status);
  if (!id || !ID.test(id) || !isKind(e.kind) || !value || !status) {
    return [];
  }
  return [{ id, at: typeof e.at === 'number' ? e.at : 0, kind: e.kind, value, previous: word(e.previous), status }];
}

export async function fetchLook(slug: string, signal?: AbortSignal): Promise<LookDetails> {
  const raw = asRecord(await requestJson<unknown>(`/api/people/${encodeURIComponent(slug)}/look`, { signal }));
  return {
    available: raw.available === true,
    consent: raw.consent !== false,
    summary: summaryOf(raw.summary),
    events: Array.isArray(raw.events) ? raw.events.slice(0, 60).flatMap(eventOf) : [],
  };
}

export async function judgeLook(slug: string, id: string, verdict: 'ok' | 'wrong'): Promise<void> {
  if (!ID.test(id)) {
    throw new Error('people_look_invalid');
  }
  await requestJson<unknown>(`/api/people/${encodeURIComponent(slug)}/look/${id}`, {
    method: 'POST',
    body: JSON.stringify({ verdict }),
  });
}
