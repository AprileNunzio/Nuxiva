import { asRecord, asString, requestJson } from './http';
import { parseOverview } from './brainApi';
import { REF, list } from './parse';
import { BrainOverview } from './types';

const PRESET_ID = /^[a-z_]{1,40}$/;

export async function fetchPresets(signal?: AbortSignal): Promise<string[]> {
  return list(asRecord(await requestJson<unknown>('/api/brains/presets', { signal })).presets)
    .map((p) => asString(asRecord(p).id, 40))
    .filter((id): id is string => id !== null && PRESET_ID.test(id));
}

export async function applyPreset(preset: string): Promise<BrainOverview> {
  if (!PRESET_ID.test(preset)) {
    throw new RangeError('invalid_preset');
  }
  return parseOverview(await requestJson<unknown>('/api/brains/preset', { method: 'POST', body: JSON.stringify({ preset }) }));
}

export async function applyEverywhere(model: string, keepBackups: boolean): Promise<BrainOverview> {
  if (!REF.test(model)) {
    throw new RangeError('invalid_model');
  }
  return parseOverview(
    await requestJson<unknown>('/api/brains/everywhere', { method: 'POST', body: JSON.stringify({ model, keep_backups: keepBackups }) }),
  );
}
