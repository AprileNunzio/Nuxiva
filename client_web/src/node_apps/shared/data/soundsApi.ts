import { asRecord, asString, requestJson } from './http';

export interface SystemSound {
  readonly name: string;
  readonly label: string;
}

const NAME_PATTERN = /^[a-z0-9_-]{1,40}$/;

export async function fetchSounds(signal?: AbortSignal): Promise<SystemSound[]> {
  const payload = asRecord(await requestJson<unknown>('/api/sounds', { signal }));
  const list = Array.isArray(payload.sounds) ? payload.sounds : [];
  return list
    .map(asRecord)
    .map((s) => ({ name: asString(s.name, 40) ?? '', label: asString(s.label, 80) ?? '' }))
    .filter((s) => NAME_PATTERN.test(s.name) && s.label);
}

export async function playSound(name: string): Promise<void> {
  if (!NAME_PATTERN.test(name)) {
    throw new Error('invalid_sound');
  }
  await requestJson(`/api/sounds/play/${encodeURIComponent(name)}`, { method: 'POST' });
}
