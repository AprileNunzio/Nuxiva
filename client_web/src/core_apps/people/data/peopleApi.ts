import { adminPath } from '../../../shared/http/basePath';
import { NodeModuleError, asRecord, asString, asStringList, requestJson } from '../../../node_apps/shared/data/http';

export const SLUG = /^[a-z0-9][a-z0-9-]{0,39}$/;
export const PHOTO_KINDS = ['front', 'three_left', 'three_right', 'left', 'right', 'up', 'down', 'body', 'body_back'] as const;
export type PhotoKind = (typeof PHOTO_KINDS)[number];

export type FieldType = 'text' | 'select' | 'tags' | 'list' | 'date' | 'bool' | 'number' | 'textarea' | 'tel' | 'email' | 'url' | 'person';

export interface SchemaField {
  readonly key: string;
  readonly label: string;
  readonly type: FieldType;
  readonly options: readonly string[];
  readonly labels: Readonly<Record<string, string>>;
  readonly placeholder: string;
  readonly fields: readonly SchemaField[];
}

export interface SchemaSection {
  readonly id: string;
  readonly title: string;
  readonly icon: string;
  readonly private: boolean;
  readonly fields: readonly SchemaField[];
}

export interface Habits {
  readonly summary: string;
  readonly arrivalHours: readonly number[];
  readonly weekdays: readonly number[];
  readonly avgMinutes: number;
}

export interface PersonSummary {
  readonly slug: string;
  readonly name: string;
  readonly role: string;
  readonly membership: string;
  readonly nickname: string;
  readonly scanned: boolean;
  readonly quality: number;
  readonly lastSeen: number | null;
  readonly visits: number;
  readonly age: number | null;
}

export type Profile = Readonly<Record<string, unknown>>;

export interface Photo {
  readonly id: string;
  readonly url: string;
  readonly kind: string;
  readonly primary: boolean;
  readonly createdAt: number;
}

export interface Memory {
  readonly id: string;
  readonly text: string;
  readonly kind: string;
  readonly score: number;
  readonly created: number;
  readonly hits: number;
}

export interface MoodEntry {
  readonly id: string;
  readonly at: number;
  readonly mood: string;
  readonly intensity: number;
  readonly note: string;
  readonly source: string;
}

export interface Voiceprint {
  readonly samples: number;
  readonly enrolled: boolean;
}

const num = (value: unknown, fallback = 0): number => (typeof value === 'number' && Number.isFinite(value) ? value : fallback);
const list = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);
const slugOf = (slug: string): string => {
  if (!SLUG.test(slug)) {
    throw new NodeModuleError('invalid_person', 400);
  }
  return encodeURIComponent(slug);
};

function parseField(value: unknown): SchemaField | null {
  const f = asRecord(value);
  const key = asString(f.key, 60);
  if (!key) {
    return null;
  }
  const labels = asRecord(f.labels);
  return {
    key,
    label: asString(f.label, 120) ?? key,
    type: (asString(f.type, 12) ?? 'text') as FieldType,
    options: list(f.options).map((o) => String(o ?? '')).slice(0, 60),
    labels: Object.fromEntries(Object.entries(labels).map(([k, v]) => [k, String(v ?? '').slice(0, 80)])),
    placeholder: asString(f.placeholder, 120) ?? '',
    fields: list(f.fields).map(parseField).filter((x): x is SchemaField => x !== null),
  };
}

export async function fetchSchema(signal?: AbortSignal): Promise<{ sections: SchemaSection[]; voices: Record<string, string> }> {
  const raw = asRecord(await requestJson<unknown>('/api/people/schema', { signal }));
  const voices = asRecord(raw.voices);
  return {
    sections: list(raw.sections).map(asRecord).flatMap((s) => {
      const id = asString(s.id, 40);
      return id
        ? [{ id, title: asString(s.title, 80) ?? id, icon: asString(s.icon, 8) ?? '', private: s.private === true,
             fields: list(s.fields).map(parseField).filter((x): x is SchemaField => x !== null) }]
        : [];
    }),
    voices: Object.fromEntries(Object.entries(voices).map(([k, v]) => [k, String(v ?? '')])),
  };
}

function parseSummary(value: unknown): PersonSummary | null {
  const p = asRecord(value);
  const slug = asString(p.slug, 40);
  if (!slug || !SLUG.test(slug)) {
    return null;
  }
  const stats = asRecord(p.stats);
  const computed = asRecord(p.computed);
  return {
    slug,
    name: asString(computed.display_name, 120) ?? asString(p.name, 120) ?? slug,
    role: asString(p.role, 20) ?? 'guest',
    membership: asString(p.membership, 12) ?? '',
    nickname: asString(p.nickname, 60) ?? '',
    scanned: p.is_scanned === true,
    quality: num(p.quality_pct),
    lastSeen: typeof stats.last_seen === 'number' ? stats.last_seen : null,
    visits: num(stats.visits),
    age: typeof computed.age === 'number' ? computed.age : null,
  };
}

export async function fetchPeople(signal?: AbortSignal): Promise<{ people: PersonSummary[]; roles: Record<string, string> }> {
  const raw = asRecord(await requestJson<unknown>('/api/people', { signal }));
  const roles = asRecord(raw.roles);
  return {
    people: list(raw.people).map(parseSummary).filter((p): p is PersonSummary => p !== null),
    roles: Object.fromEntries(Object.entries(roles).map(([k, v]) => [k, String(v ?? '')])),
  };
}

export async function fetchPerson(slug: string, signal?: AbortSignal): Promise<Profile> {
  return asRecord(await requestJson<unknown>(`/api/people/${slugOf(slug)}`, { signal }));
}

export function habitsOf(profile: Profile): Habits {
  const h = asRecord(profile.habits);
  return {
    summary: asString(h.summary, 400) ?? '',
    arrivalHours: list(h.arrival_hours).map((v) => num(v)).slice(0, 24),
    weekdays: list(h.weekdays).map((v) => num(v)).slice(0, 7),
    avgMinutes: num(h.avg_minutes),
  };
}

export function voiceprintOf(profile: Profile): Voiceprint {
  const v = asRecord(profile.voiceprint);
  return { samples: num(v.samples), enrolled: v.enrolled === true };
}

export const createPerson = (name: string) => requestJson<unknown>('/api/people', { method: 'POST', body: JSON.stringify({ name }) });
export const updatePerson = (slug: string, changes: Record<string, unknown>) =>
  requestJson<unknown>(`/api/people/${slugOf(slug)}`, { method: 'PUT', body: JSON.stringify(changes) });
export const deletePerson = (slug: string) => requestJson<unknown>(`/api/people/${slugOf(slug)}`, { method: 'DELETE' });
export const associatePerson = (from: string, to: string) =>
  requestJson<unknown>(`/api/people/${slugOf(from)}/associate`, { method: 'POST', body: JSON.stringify({ to_slug: to }) });

export async function fetchPhotos(slug: string, signal?: AbortSignal): Promise<Photo[]> {
  const raw = asRecord(await requestJson<unknown>(`/api/people/${slugOf(slug)}/photos`, { signal }));
  return list(raw.photos)
    .map(asRecord)
    .flatMap((p) => {
      const id = asString(p.id, 130);
      const url = asString(p.url, 300);
      return id && url && url.startsWith('/api/') ? [{ id, url: adminPath(url), kind: asString(p.kind, 20) ?? 'sample', primary: p.is_primary === true, createdAt: num(p.created_at) }] : [];
    });
}

export async function fetchCoverage(slug: string, signal?: AbortSignal): Promise<Record<string, number>> {
  const raw = asRecord(asRecord(await requestJson<unknown>(`/api/people/${slugOf(slug)}/views`, { signal })).views);
  return Object.fromEntries(Object.entries(raw).map(([k, v]) => [k, num(v)]));
}

export const capturePhoto = (slug: string, kind: PhotoKind) =>
  requestJson<unknown>(`/api/people/${slugOf(slug)}/views/capture?kind=${kind}`, { method: 'POST' });

export async function uploadPhoto(slug: string, file: File): Promise<void> {
  const response = await fetch(`/api/people/${slugOf(slug)}/views?kind=auto`, {
    method: 'POST',
    body: file,
    headers: { 'Content-Type': file.type },
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new NodeModuleError('upload_failed', response.status);
  }
}

export const deletePhoto = (slug: string, id: string) =>
  requestJson<unknown>(`/api/people/${slugOf(slug)}/photos/${encodeURIComponent(id)}`, { method: 'DELETE' });
export const reproject = (slug: string) => requestJson<unknown>(`/api/people/${slugOf(slug)}/reproject`, { method: 'POST' });

export const startVoiceTraining = (slug: string) =>
  requestJson<unknown>(`/api/people/${slugOf(slug)}/voice-training/start`, { method: 'POST' });
export const forgetVoiceTraining = (slug: string) =>
  requestJson<unknown>(`/api/people/${slugOf(slug)}/voice-training`, { method: 'DELETE' });
export const forgetVoiceprint = (slug: string) => requestJson<unknown>(`/api/people/${slugOf(slug)}/voiceprint`, { method: 'DELETE' });

export async function fetchMemories(slug: string, signal?: AbortSignal): Promise<Memory[]> {
  const raw = asRecord(await requestJson<unknown>(`/api/people/${slugOf(slug)}/memories`, { signal }));
  return list(raw.memories)
    .map(asRecord)
    .flatMap((m) => {
      const id = asString(m.id, 16);
      return id && /^[0-9a-f]{6,16}$/.test(id)
        ? [{ id, text: asString(m.text, 200) ?? '', kind: asString(m.kind, 20) ?? '', score: num(m.score), created: num(m.created), hits: num(m.hits) }]
        : [];
    });
}

export const addMemory = (slug: string, text: string) =>
  requestJson<unknown>(`/api/people/${slugOf(slug)}/memories`, { method: 'POST', body: JSON.stringify({ text }) });
export const deleteMemory = (id: string) => {
  if (!/^[0-9a-f]{6,16}$/.test(id)) {
    throw new NodeModuleError('invalid_memory', 400);
  }
  return requestJson<unknown>(`/api/mind/facts/${id}`, { method: 'DELETE' });
};

export async function fetchMood(slug: string, signal?: AbortSignal): Promise<{ moods: string[]; journal: MoodEntry[] }> {
  const raw = asRecord(await requestJson<unknown>(`/api/people/${slugOf(slug)}/mood`, { signal }));
  return {
    moods: asStringList(raw.moods, 32),
    journal: list(raw.journal)
      .map(asRecord)
      .flatMap((e) => {
        const id = asString(e.id, 16);
        return id
          ? [{ id, at: num(e.at), mood: asString(e.mood, 20) ?? '', intensity: num(e.intensity, 3), note: asString(e.note, 300) ?? '', source: asString(e.source, 12) ?? '' }]
          : [];
      }),
  };
}

export const addMood = (slug: string, mood: string, intensity: number, note: string) =>
  requestJson<unknown>(`/api/people/${slugOf(slug)}/mood`, { method: 'POST', body: JSON.stringify({ mood, intensity, note }) });
export const deleteMood = (slug: string, id: string) =>
  requestJson<unknown>(`/api/people/${slugOf(slug)}/mood/${encodeURIComponent(id)}`, { method: 'DELETE' });

export async function fetchPresence(signal?: AbortSignal): Promise<{ status: string; present: string[] }> {
  const presence = asRecord(asRecord(await requestJson<unknown>('/api/state', { signal })).presence);
  return {
    status: asString(presence.status, 20) ?? '',
    present: list(presence.people)
      .map(asRecord)
      .filter((p) => p.known === true)
      .map((p) => asString(p.slug, 40))
      .filter((s): s is string => s !== null),
  };
}
