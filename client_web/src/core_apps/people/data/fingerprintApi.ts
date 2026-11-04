import { NodeModuleError, asRecord, asString, requestJson } from '../../../node_apps/shared/data/http';
import { SLUG } from './peopleApi';

export const FINGERS = [
  'left_thumb', 'left_index', 'left_middle', 'left_ring', 'left_little',
  'right_thumb', 'right_index', 'right_middle', 'right_ring', 'right_little',
] as const;
export type Finger = (typeof FINGERS)[number];
export type Transport = 'usb' | 'bluetooth' | 'wifi' | 'builtin';

export interface FingerprintReader {
  readonly key: string;
  readonly label: string;
  readonly room: string;
  readonly transport: Transport;
  readonly online: boolean;
  readonly ready: boolean;
}

export interface FingerprintState {
  readonly enabled: boolean;
  readonly fingers: readonly { readonly finger: Finger; readonly reader: string }[];
  readonly readers: readonly FingerprintReader[];
  readonly pending: { readonly finger: Finger; readonly reader: string; readonly expiresIn: number } | null;
  readonly last: { readonly room: string; readonly at: number } | null;
}

const slugOf = (slug: string): string => {
  if (!SLUG.test(slug)) {
    throw new NodeModuleError('invalid_person', 400);
  }
  return encodeURIComponent(slug);
};
const list = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);
const isFinger = (value: unknown): value is Finger => typeof value === 'string' && (FINGERS as readonly string[]).includes(value);
const TRANSPORTS: readonly string[] = ['usb', 'bluetooth', 'wifi', 'builtin'];
const base = (slug: string): string => `/api/people/${slugOf(slug)}/fingerprint`;

export async function fetchFingerprint(slug: string, signal?: AbortSignal): Promise<FingerprintState> {
  const raw = asRecord(await requestJson<unknown>(base(slug), { signal }));
  const pending = asRecord(raw.pending);
  const last = asRecord(raw.last);
  return {
    enabled: raw.enabled === true,
    fingers: list(raw.fingers).map(asRecord).flatMap((f) => (isFinger(f.finger) ? [{ finger: f.finger, reader: asString(f.reader, 80) ?? '' }] : [])),
    readers: list(raw.readers).map(asRecord).flatMap((r) => {
      const key = asString(r.key, 80) ?? '';
      return key && TRANSPORTS.includes(String(r.transport))
        ? [{ key, label: asString(r.label, 40) ?? key, room: asString(r.room, 60) ?? '', transport: r.transport as Transport, online: r.online === true, ready: r.ready !== false }]
        : [];
    }),
    pending: isFinger(pending.finger) ? { finger: pending.finger, reader: asString(pending.reader, 80) ?? '', expiresIn: Number(pending.expires_in) || 0 } : null,
    last: typeof last.at === 'number' ? { room: asString(last.room, 60) ?? '', at: last.at } : null,
  };
}

export const setFingerprintEnabled = (slug: string, enabled: boolean) =>
  requestJson<unknown>(base(slug), { method: 'PUT', body: JSON.stringify({ enabled }) });

export const startFingerprintEnroll = (slug: string, finger: Finger, reader: string) =>
  requestJson<unknown>(`${base(slug)}/enroll`, { method: 'POST', body: JSON.stringify({ finger, reader }) });

export const cancelFingerprintEnroll = (slug: string) => requestJson<unknown>(`${base(slug)}/enroll`, { method: 'DELETE' });

export const forgetFingerprint = (slug: string, finger?: Finger) =>
  requestJson<unknown>(finger ? `${base(slug)}?finger=${finger}` : base(slug), { method: 'DELETE' });
