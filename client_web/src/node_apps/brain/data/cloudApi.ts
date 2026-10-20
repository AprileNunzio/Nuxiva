import { NodeModuleError, asRecord, asString, requestJson } from '../../shared/data/http';
import { list, num } from './parse';

export interface CloudProvider {
  readonly id: string;
  readonly name: string;
  readonly baseUrl: string;
  readonly keyUrl: string | null;
  readonly needsUrl: boolean;
  readonly keyOptional: boolean;
  readonly configured: boolean;
  readonly hasKey: boolean;
  readonly keyHint: string;
  readonly enabled: boolean;
  readonly notes: string;
}

export interface ModelServer {
  readonly id: string;
  readonly name: string;
  readonly flavor: 'ollama' | 'openai';
  readonly url: string;
  readonly online: boolean;
  readonly models: readonly string[];
  readonly error: string;
}

export interface CloudTest {
  readonly ok: boolean;
  readonly detail: string;
  readonly ms: number;
}

const PID = /^[a-z0-9][a-z0-9._-]{0,63}$/;
const HTTPS_URL = /^https:\/\//;

const pid = (id: string): string => {
  if (!PID.test(id)) {
    throw new NodeModuleError('invalid_provider', 400);
  }
  return encodeURIComponent(id);
};

function parseProvider(value: unknown): CloudProvider | null {
  const p = asRecord(value);
  const id = asString(p.id, 64);
  if (!id || !PID.test(id) || id.startsWith('srv-')) {
    return null;
  }
  const keyUrl = asString(p.key_url, 200);
  return {
    id,
    name: asString(p.name, 80) ?? id,
    baseUrl: asString(p.base_url, 300) ?? '',
    keyUrl: keyUrl && HTTPS_URL.test(keyUrl) ? keyUrl : null,
    needsUrl: p.needs_url === true,
    keyOptional: p.key_optional === true,
    configured: p.configured === true,
    hasKey: p.has_key === true,
    keyHint: asString(p.key_hint, 20) ?? '',
    enabled: p.enabled !== false,
    notes: asString(p.notes, 300) ?? '',
  };
}

export async function fetchProviders(signal?: AbortSignal): Promise<CloudProvider[]> {
  const raw = asRecord(await requestJson<unknown>('/api/cloud', { signal }));
  return list(raw.providers).map(parseProvider).filter((p): p is CloudProvider => p !== null);
}

export interface ProviderChange {
  readonly key?: string;
  readonly base_url?: string;
  readonly enabled?: boolean;
}

export async function updateProvider(id: string, change: ProviderChange): Promise<CloudProvider | null> {
  return parseProvider(await requestJson<unknown>(`/api/cloud/${pid(id)}`, { method: 'PUT', body: JSON.stringify(change) }));
}

export async function testProvider(id: string): Promise<CloudTest> {
  const raw = asRecord(await requestJson<unknown>(`/api/cloud/${pid(id)}/test`, { method: 'POST', body: '{}' }));
  return { ok: raw.ok === true, detail: asString(raw.ok === true ? raw.reply : raw.error, 200) ?? '', ms: num(raw.ms) };
}

function parseServer(value: unknown): ModelServer | null {
  const s = asRecord(value);
  const id = asString(s.id, 64);
  if (!id || !PID.test(id)) {
    return null;
  }
  return {
    id,
    name: asString(s.name, 40) ?? id,
    flavor: s.flavor === 'openai' ? 'openai' : 'ollama',
    url: asString(s.url, 300) ?? '',
    online: s.online === true,
    models: list(s.models).filter((m): m is string => typeof m === 'string').slice(0, 100),
    error: asString(s.error, 200) ?? '',
  };
}

export async function fetchServers(signal?: AbortSignal): Promise<ModelServer[]> {
  return list(asRecord(await requestJson<unknown>('/api/brains/servers', { signal })).servers)
    .map(parseServer)
    .filter((s): s is ModelServer => s !== null);
}

export interface NewServer {
  readonly name: string;
  readonly flavor: 'ollama' | 'openai';
  readonly url: string;
  readonly key: string;
}

export async function testServer(server: NewServer): Promise<{ ok: boolean; models: string[]; error: string }> {
  const raw = asRecord(await requestJson<unknown>('/api/brains/servers/test', { method: 'POST', body: JSON.stringify(server) }));
  return {
    ok: raw.ok === true,
    models: list(raw.models).filter((m): m is string => typeof m === 'string').slice(0, 100),
    error: asString(raw.error, 200) ?? '',
  };
}

export async function addServer(server: NewServer): Promise<void> {
  await requestJson('/api/brains/servers', { method: 'POST', body: JSON.stringify(server) });
}

export async function removeServer(id: string): Promise<void> {
  await requestJson(`/api/brains/servers/${pid(id)}`, { method: 'DELETE' });
}
