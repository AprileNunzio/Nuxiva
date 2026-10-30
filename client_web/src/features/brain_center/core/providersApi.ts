import { asRecord, asString, requestJson } from './http';
import { HTTPS_URL, PROVIDER_ID, SERVICE_URL, list, num, providerPath, strings } from './parse';
import { CloudProvider, ModelServer, NewServer, ProviderChange, ProviderTest } from './types';

function parseProvider(value: unknown): CloudProvider | null {
  const p = asRecord(value);
  const id = asString(p.id, 64);
  if (!id || !PROVIDER_ID.test(id) || id.startsWith('srv-')) {
    return null;
  }
  const keyUrl = asString(p.key_url, 300);
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
  };
}

function parseServer(value: unknown): ModelServer | null {
  const s = asRecord(value);
  const id = asString(s.id, 64);
  if (!id || !PROVIDER_ID.test(id)) {
    return null;
  }
  return {
    id,
    name: asString(s.name, 40) ?? id,
    flavor: s.flavor === 'openai' ? 'openai' : 'ollama',
    url: asString(s.url, 300) ?? '',
    online: s.online === true,
    models: strings(s.models, 200, 160),
  };
}

export function validateChange(change: ProviderChange): ProviderChange {
  if (change.key !== undefined && change.key !== '' && !/^[\x21-\x7e]{8,512}$/.test(change.key)) {
    throw new RangeError('invalid_key');
  }
  if (change.base_url !== undefined && change.base_url !== '' && !SERVICE_URL.test(change.base_url)) {
    throw new RangeError('invalid_url');
  }
  return change;
}

export function validateServer(server: NewServer): NewServer {
  const name = server.name.trim();
  if (!name || name.length > 40 || /[<>"'`]/.test(name)) {
    throw new RangeError('invalid_name');
  }
  validateChange({ base_url: server.url.trim(), key: server.key.trim() || undefined });
  return { name, flavor: server.flavor, url: server.url.trim(), key: server.key.trim() };
}

export async function fetchProviders(signal?: AbortSignal): Promise<CloudProvider[]> {
  const raw = asRecord(await requestJson<unknown>('/api/cloud', { signal }));
  return list(raw.providers)
    .map(parseProvider)
    .filter((p): p is CloudProvider => p !== null);
}

export async function updateProvider(id: string, change: ProviderChange): Promise<void> {
  await requestJson(`/api/cloud/${providerPath(id)}`, { method: 'PUT', body: JSON.stringify(validateChange(change)) });
}

export async function removeProviderKey(id: string): Promise<void> {
  await requestJson(`/api/cloud/${providerPath(id)}/key`, { method: 'DELETE' });
}

export async function testProvider(id: string): Promise<ProviderTest> {
  const raw = asRecord(await requestJson<unknown>(`/api/cloud/${providerPath(id)}/test`, { method: 'POST', body: '{}' }));
  return { ok: raw.ok === true, detail: asString(raw.ok === true ? raw.reply : raw.error, 200) ?? '', ms: num(raw.ms) };
}

export async function fetchServers(signal?: AbortSignal): Promise<ModelServer[]> {
  return list(asRecord(await requestJson<unknown>('/api/brains/servers', { signal })).servers)
    .map(parseServer)
    .filter((s): s is ModelServer => s !== null);
}

export async function testServer(server: NewServer): Promise<{ ok: boolean; count: number }> {
  const raw = asRecord(
    await requestJson<unknown>('/api/brains/servers/test', { method: 'POST', body: JSON.stringify(validateServer(server)) }),
  );
  return { ok: raw.ok === true, count: list(raw.models).length };
}

export async function addServer(server: NewServer): Promise<void> {
  await requestJson('/api/brains/servers', { method: 'POST', body: JSON.stringify(validateServer(server)) });
}

export async function removeServer(id: string): Promise<void> {
  await requestJson(`/api/brains/servers/${providerPath(id)}`, { method: 'DELETE' });
}
