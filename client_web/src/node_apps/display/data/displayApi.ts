import { NodeModuleError, asRecord, asString, requestJson } from '../../shared/data/http';

export interface ActiveScreen {
  readonly index: number;
  readonly width: number;
  readonly height: number;
  readonly local: boolean;
  readonly ear: string | null;
}

export interface DisplayClient {
  readonly client: string;
  readonly screen: number;
  readonly size: string | null;
  readonly metrics: readonly (readonly [string, string])[];
}

export interface ScreensState {
  readonly screens: readonly ActiveScreen[];
  readonly clients: readonly DisplayClient[];
}

export interface AvatarFile {
  readonly name: string;
  readonly size: number;
}

export interface Avatar {
  readonly name: string;
  readonly files: readonly AvatarFile[];
  readonly model: string | null;
}

export interface AvatarLibrary {
  readonly avatars: readonly Avatar[];
  readonly active: string;
  readonly maxBytes: number;
}

export const AVATAR_NAME = /^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$/;
export const AVATAR_ACCEPT = '.glb,.fbx,.png,.jpg,.jpeg,.webp';
const METRIC = /^([a-z_]{1,16})=([\w.%-]{1,24})$/;

const int = (value: unknown, fallback = 0): number => (typeof value === 'number' && Number.isFinite(value) ? Math.round(value) : fallback);

function parseScreen(value: unknown): ActiveScreen {
  const s = asRecord(value);
  return { index: int(s.n), width: int(s.w), height: int(s.h), local: s.local === true, ear: asString(s.ear, 40) };
}

function parseClient(value: unknown): DisplayClient {
  const c = asRecord(value);
  const perf = asString(c.perf, 300) ?? '';
  const metrics = perf
    .split(/\s+/)
    .map((token) => METRIC.exec(token))
    .filter((m): m is RegExpExecArray => m !== null)
    .map((m) => [m[1], m[2]] as const)
    .slice(0, 8);
  return { client: asString(c.client, 80) ?? '?', screen: int(c.screen), size: asString(c.size, 20), metrics };
}

export async function fetchScreens(signal?: AbortSignal): Promise<ScreensState> {
  const raw = asRecord(await requestJson<unknown>('/api/state', { signal }));
  return {
    screens: (Array.isArray(raw.screens) ? raw.screens : []).slice(0, 16).map(parseScreen),
    clients: (Array.isArray(raw.displays) ? raw.displays : []).slice(0, 32).map(parseClient),
  };
}

function parseLibrary(value: unknown): AvatarLibrary {
  const raw = asRecord(value);
  const avatars = (Array.isArray(raw.avatars) ? raw.avatars : []).map(asRecord).flatMap((a) => {
    const name = asString(a.name, 40);
    if (!name || !AVATAR_NAME.test(name)) {
      return [];
    }
    const files = (Array.isArray(a.files) ? a.files : [])
      .map(asRecord)
      .map((f) => ({ name: asString(f.name, 100) ?? '', size: int(f.size) }))
      .filter((f) => f.name);
    return [{ name, files, model: asString(a.model, 100) }];
  });
  const active = asString(raw.active, 40) ?? '';
  return { avatars, active: AVATAR_NAME.test(active) ? active : '', maxBytes: int(raw.max_bytes, 64 * 1024 * 1024) };
}

export async function fetchAvatars(signal?: AbortSignal): Promise<AvatarLibrary> {
  return parseLibrary(await requestJson<unknown>('/api/avatars', { signal }));
}

export async function activateAvatar(name: string): Promise<AvatarLibrary> {
  return parseLibrary(await requestJson<unknown>('/api/avatars/active', { method: 'POST', body: JSON.stringify({ name }) }));
}

export async function deleteAvatar(name: string): Promise<AvatarLibrary> {
  if (!AVATAR_NAME.test(name)) {
    throw new NodeModuleError('invalid_name', 400);
  }
  return parseLibrary(await requestJson<unknown>(`/api/avatars/${encodeURIComponent(name)}`, { method: 'DELETE' }));
}

export async function uploadAvatar(name: string, file: File): Promise<AvatarLibrary> {
  const form = new FormData();
  form.append('name', name);
  form.append('file', file, file.name);
  const response = await fetch('/api/avatars/upload', { method: 'POST', body: form, cache: 'no-store' });
  if (!response.ok) {
    throw new NodeModuleError('upload_failed', response.status);
  }
  return parseLibrary(await response.json());
}
