import { NodeModuleError, asRecord, asString, requestJson } from '../../shared/data/http';
import { MODEL_NAME, list, num } from './parse';

export interface LocalModel {
  readonly name: string;
  readonly size: number;
  readonly loaded: boolean;
}

export interface PullProgress {
  readonly name: string;
  readonly status: string;
  readonly percent: number;
}

export async function fetchLocalModels(signal?: AbortSignal): Promise<LocalModel[]> {
  const raw = asRecord(await requestJson<unknown>('/api/models', { signal }));
  const loaded = new Set(list(raw.loaded).filter((m): m is string => typeof m === 'string'));
  return list(raw.models)
    .map(asRecord)
    .flatMap((m) => {
      const name = asString(m.name, 120);
      return name ? [{ name, size: num(m.size), loaded: loaded.has(name) }] : [];
    });
}

export async function pullModel(name: string): Promise<void> {
  if (!MODEL_NAME.test(name)) {
    throw new NodeModuleError('invalid_model', 400);
  }
  await requestJson('/api/models/pull', { method: 'POST', body: JSON.stringify({ name }) });
}

export async function deleteModel(name: string): Promise<void> {
  if (!MODEL_NAME.test(name)) {
    throw new NodeModuleError('invalid_model', 400);
  }
  await requestJson(`/api/models/${name.split('/').map(encodeURIComponent).join('/')}`, { method: 'DELETE' });
}

export async function fetchPullProgress(signal?: AbortSignal): Promise<PullProgress | null> {
  const pull = asRecord(asRecord(await requestJson<unknown>('/api/state', { signal })).model_pull);
  const name = asString(pull.name, 120);
  return name ? { name, status: asString(pull.status, 160) ?? '', percent: Math.max(0, Math.min(100, num(pull.percent))) } : null;
}
