import { NodeModuleError, asRecord, asString, asStringList, requestJson } from '../../../node_apps/shared/data/http';
import { SLUG } from './peopleApi';

export interface TelegramChat {
  readonly id: string;
  readonly name: string;
  readonly username: string;
  readonly notify: boolean;
  readonly voice: boolean;
}

export interface TelegramState {
  readonly available: boolean;
  readonly linked: boolean;
  readonly bot: string;
  readonly chats: readonly TelegramChat[];
  readonly pairCode: string;
  readonly pairExpiresIn: number;
}

export interface GoogleState {
  readonly available: boolean;
  readonly linked: boolean;
  readonly pending: boolean;
  readonly email: string;
  readonly granted: readonly string[];
  readonly services: readonly GoogleService[];
  readonly remindMin: number;
}

export interface GoogleService {
  readonly id: string;
  readonly icon: string;
  readonly granted: boolean;
}

export interface Connectors {
  readonly telegram: TelegramState | null;
  readonly google: GoogleState | null;
}

const slugOf = (slug: string): string => {
  if (!SLUG.test(slug)) {
    throw new NodeModuleError('invalid_person', 400);
  }
  return encodeURIComponent(slug);
};
const serviceOf = (service: string): string => {
  if (!/^[a-z_]{2,24}$/.test(service)) {
    throw new NodeModuleError('invalid_service', 400);
  }
  return service;
};
const list = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);

export function parseTelegram(value: unknown): TelegramState {
  const raw = asRecord(value);
  return {
    available: raw.available === true,
    linked: raw.linked === true,
    bot: asString(raw.bot, 64) ?? '',
    chats: list(raw.chats).map(asRecord).flatMap((c) => {
      const id = asString(String(c.id ?? ''), 24);
      return id && /^-?\d+$/.test(id)
        ? [{ id, name: asString(c.name, 80) ?? '', username: asString(c.username, 64) ?? '', notify: c.notify !== false, voice: c.voice !== false }]
        : [];
    }),
    pairCode: /^\d{6}$/.test(String(raw.pair_code ?? '')) ? String(raw.pair_code) : '',
    pairExpiresIn: typeof raw.pair_expires_in === 'number' ? Math.max(0, raw.pair_expires_in) : 0,
  };
}

function parseGoogle(value: unknown): GoogleState {
  const raw = asRecord(value);
  return {
    available: raw.available === true,
    linked: raw.linked === true,
    pending: raw.pending === true,
    email: asString(raw.email, 120) ?? '',
    granted: asStringList(raw.granted, 16),
    remindMin: typeof raw.remind_min === 'number' ? Math.max(0, Math.min(240, Math.round(raw.remind_min))) : 10,
    services: list(raw.services).map(asRecord).flatMap((x) => {
      const id = asString(x.id, 24) ?? '';
      return /^[a-z_]{2,24}$/.test(id) ? [{ id, icon: asString(x.icon, 8) ?? '', granted: x.granted === true }] : [];
    }),
  };
}

export async function fetchConnectors(slug: string, signal?: AbortSignal): Promise<Connectors> {
  const raw = asRecord(await requestJson<unknown>(`/api/people/${slugOf(slug)}/connectors`, { signal }));
  const byId = new Map(list(raw.connectors).map(asRecord).map((c) => [String(c.id ?? ''), c] as const));
  const telegram = byId.get('telegram');
  const google = byId.get('google');
  return { telegram: telegram ? parseTelegram(telegram) : null, google: google ? parseGoogle(google) : null };
}

const base = (slug: string) => `/api/people/${slugOf(slug)}/telegram`;
export const telegramPair = (slug: string) => requestJson<unknown>(`${base(slug)}/pair-code`, { method: 'POST' });
export const telegramUnlink = (slug: string) => requestJson<unknown>(base(slug), { method: 'DELETE' });
export const telegramChat = (slug: string, chat: string, changes: { notify?: boolean; voice?: boolean }) => {
  if (!/^-?\d+$/.test(chat)) {
    throw new NodeModuleError('invalid_chat', 400);
  }
  return requestJson<unknown>(`${base(slug)}/${chat}`, { method: 'PUT', body: JSON.stringify(changes) });
};

export const googleAuthUrl = async (slug: string): Promise<string> => {
  const raw = asRecord(await requestJson<unknown>(`/api/google/${slugOf(slug)}/auth-url`, { method: 'POST', body: '{}' }));
  const url = asString(raw.url, 4000) ?? '';
  if (!/^https:\/\/accounts\.google\.com\//.test(url)) {
    throw new NodeModuleError('invalid_url', 502);
  }
  return url;
};
export const googleFinish = (slug: string, url: string) =>
  requestJson<unknown>('/api/google/finish', { method: 'POST', body: JSON.stringify({ slug, url: url.slice(0, 4000) }) });
export const googleEnableService = async (slug: string, service: string): Promise<string> => {
  const raw = asRecord(await requestJson<unknown>(`/api/google/${slugOf(slug)}/services/${serviceOf(service)}`, { method: 'POST', body: '{}' }));
  const url = asString(raw.url, 4000) ?? '';
  if (url && !/^https:\/\/accounts\.google\.com\//.test(url)) {
    throw new NodeModuleError('invalid_url', 502);
  }
  return url;
};
export const googleDisableService = (slug: string, service: string) =>
  requestJson<unknown>(`/api/google/${slugOf(slug)}/services/${serviceOf(service)}`, { method: 'DELETE' });
export const googleSetReminder = (slug: string, minutes: number) =>
  requestJson<unknown>(`/api/google/${slugOf(slug)}/reminder`, { method: 'PUT', body: JSON.stringify({ minutes }) });
export const googleCancel = (slug: string) => requestJson<unknown>(`/api/google/${slugOf(slug)}/pending`, { method: 'DELETE' });
export const googleUnlink = (slug: string) => requestJson<unknown>(`/api/google/${slugOf(slug)}`, { method: 'DELETE' });

export type VitalKind = 'ble' | 'push' | 'phone';
export type VitalState = 'off' | 'waiting' | 'seen' | 'connected' | 'streaming' | 'unsupported';
const VITAL_STATES: readonly string[] = ['off', 'waiting', 'seen', 'connected', 'streaming', 'unsupported'];

export interface VitalDevice {
  readonly id: string;
  readonly kind: VitalKind;
  readonly label: string;
  readonly address: string;
  readonly last: number;
  readonly state: VitalState;
}

export interface VitalValue {
  readonly metric: string;
  readonly value: number;
  readonly unit: string;
  readonly age: number;
  readonly kind: string;
}

export interface VitalsState {
  readonly devices: readonly VitalDevice[];
  readonly values: readonly VitalValue[];
  readonly leaseNode: string;
  readonly cloudReady: boolean;
  readonly nodes: readonly string[];
  readonly reasons: readonly string[];
  readonly reasonError: string;
}

export interface NewVitalDevice {
  readonly kind: VitalKind;
  readonly label: string;
  readonly address: string;
  readonly token: string;
}

const VITAL_KINDS: readonly string[] = ['ble', 'push', 'phone'];

export async function fetchVitals(slug: string, signal?: AbortSignal): Promise<VitalsState> {
  const raw = asRecord(await requestJson<unknown>(`/api/people/${slugOf(slug)}/vitals`, { signal }));
  const values = asRecord(raw.values);
  const lease = asRecord(raw.lease);
  const cloud = asRecord(raw.cloud);
  return {
    devices: list(raw.devices).map(asRecord).flatMap((d) => {
      const id = asString(d.id, 24) ?? '';
      const kind = String(d.kind ?? '');
      return /^[a-f0-9]{4,24}$/.test(id) && VITAL_KINDS.includes(kind)
        ? [{ id, kind: kind as VitalKind, label: asString(d.label, 40) ?? kind, address: asString(d.address, 17) ?? '', last: typeof d.last === 'number' ? d.last : 0, state: (VITAL_STATES.includes(String(d.state)) ? d.state : 'waiting') as VitalState }]
        : [];
    }),
    values: Object.entries(values).flatMap(([metric, entry]) => {
      const v = asRecord(entry);
      return typeof v.value === 'number' ? [{ metric, value: v.value, unit: asString(v.unit, 8) ?? '', age: typeof v.age === 'number' ? v.age : 0, kind: asString(v.kind, 12) ?? '' }] : [];
    }),
    leaseNode: asString(lease.node, 60) ?? '',
    cloudReady: cloud.ready === true,
    nodes: list(raw.nodes).flatMap((n) => (typeof n === 'string' ? [n.slice(0, 60)] : [])),
    reasons: list(asRecord(raw.diagnosis).reasons).flatMap((r) => (typeof r === 'string' && /^[a-z_]{3,32}$/.test(r) ? [r] : [])),
    reasonError: asString(asRecord(raw.diagnosis).error, 160) ?? '',
  };
}

export async function addVitalDevice(slug: string, body: { kind: VitalKind; label: string; address?: string; ref?: string }): Promise<NewVitalDevice> {
  const raw = asRecord(await requestJson<unknown>(`/api/people/${slugOf(slug)}/vitals/devices`, { method: 'POST', body: JSON.stringify(body) }));
  const device = asRecord(raw.device);
  return { kind: body.kind, label: asString(device.label, 40) ?? body.label, address: asString(device.address, 17) ?? '', token: asString(raw.token, 120) ?? '' };
}


const deviceBase = (slug: string, id: string): string => {
  if (!/^[a-f0-9]{4,24}$/.test(id)) {
    throw new NodeModuleError('invalid_device', 400);
  }
  return `/api/people/${slugOf(slug)}/vitals/devices/${id}`;
};
export const removeVitalDevice = (slug: string, id: string) => requestJson<unknown>(deviceBase(slug, id), { method: 'DELETE' });
export const rotateVitalDevice = async (slug: string, id: string): Promise<string> => {
  const raw = asRecord(await requestJson<unknown>(`${deviceBase(slug, id)}/token`, { method: 'POST' }));
  return asString(raw.token, 120) ?? '';
};

export const switchVitalDevice = (slug: string, id: string, action: 'disconnect' | 'reconnect') =>
  requestJson<unknown>(`${deviceBase(slug, id)}/${action}`, { method: 'POST' });

export interface NearbyDevice {
  readonly ref: string;
  readonly name: string;
  readonly level: number;
  readonly standard: boolean;
}

export interface NearbyState {
  readonly active: boolean;
  readonly nodes: readonly string[];
  readonly found: readonly NearbyDevice[];
}

const vitalsBase = (slug: string): string => `/api/people/${slugOf(slug)}/vitals`;

export const startVitalsSearch = (slug: string) => requestJson<unknown>(`${vitalsBase(slug)}/search`, { method: 'POST' });

export async function fetchNearby(slug: string, signal?: AbortSignal): Promise<NearbyState> {
  const raw = asRecord(await requestJson<unknown>(`${vitalsBase(slug)}/nearby`, { signal }));
  return {
    active: raw.active === true,
    nodes: list(raw.nodes).flatMap((n) => (typeof n === 'string' ? [n.slice(0, 60)] : [])),
    found: list(raw.found).map(asRecord).flatMap((d) => {
      const ref = asString(d.ref, 16) ?? '';
      return /^[a-f0-9]{4,16}$/.test(ref)
        ? [{ ref, name: asString(d.name, 60) ?? '', level: Math.max(0, Math.min(4, Number(d.level) || 0)), standard: d.standard === true }]
        : [];
    }),
  };
}

export interface VitalLogEntry {
  readonly at: number;
  readonly level: 'info' | 'warn' | 'error';
  readonly code: string;
  readonly params: Readonly<Record<string, string>>;
}

export async function fetchVitalsLog(slug: string, signal?: AbortSignal): Promise<readonly VitalLogEntry[]> {
  const raw = asRecord(await requestJson<unknown>(`${vitalsBase(slug)}/log`, { signal }));
  return list(raw.entries).map(asRecord).flatMap((e) => {
    const code = asString(e.code, 40) ?? '';
    const level = String(e.level);
    if (!/^[a-z_]{3,40}$/.test(code) || typeof e.at !== 'number' || !['info', 'warn', 'error'].includes(level)) {
      return [];
    }
    const params = Object.fromEntries(Object.entries(asRecord(e.params)).map(([k, v]) => [k.slice(0, 24), String(v).slice(0, 80)]));
    return [{ at: e.at, level: level as VitalLogEntry['level'], code, params }];
  });
}

export async function createPhoneCode(slug: string): Promise<{ code: string; expiresIn: number }> {
  const raw = asRecord(await requestJson<unknown>(`${vitalsBase(slug)}/phone-code`, { method: 'POST' }));
  return { code: asString(raw.code, 6) ?? '', expiresIn: Number(raw.expires_in) || 600 };
}
