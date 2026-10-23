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
  return { available: raw.available === true, linked: raw.linked === true, pending: raw.pending === true, email: asString(raw.email, 120) ?? '', granted: asStringList(raw.granted, 16) };
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
export const googleCancel = (slug: string) => requestJson<unknown>(`/api/google/${slugOf(slug)}/pending`, { method: 'DELETE' });
export const googleUnlink = (slug: string) => requestJson<unknown>(`/api/google/${slugOf(slug)}`, { method: 'DELETE' });
