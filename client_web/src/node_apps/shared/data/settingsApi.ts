import { ControlScope } from '../../console/data/nodeConsoleApi';
import { NodeModuleError, asRecord, requestJson } from './http';

export interface SettingValue {
  readonly value: string;
  readonly inherited: string;
  readonly custom: boolean;
}

export type SettingsMap = Readonly<Record<string, SettingValue>>;

interface RawItem {
  readonly key?: unknown;
  readonly value?: unknown;
  readonly global?: unknown;
  readonly custom?: unknown;
  readonly secret?: unknown;
}

const KEY_PATTERN = /^NUXIVA_[A-Z0-9_]{1,60}$/;

function toMap(items: unknown, scope: ControlScope): SettingsMap {
  const result: Record<string, SettingValue> = {};
  if (!Array.isArray(items)) {
    return result;
  }
  for (const raw of items as RawItem[]) {
    const key = typeof raw.key === 'string' ? raw.key : '';
    if (!KEY_PATTERN.test(key) || raw.secret === true) {
      continue;
    }
    const value = typeof raw.value === 'string' ? raw.value : '';
    const inherited = typeof raw.global === 'string' ? raw.global : '';
    result[key] = scope === 'paired' ? { value: value || inherited, inherited, custom: raw.custom === true } : { value, inherited: '', custom: false };
  }
  return result;
}

export async function fetchSettings(nodeId: string, scope: ControlScope, signal?: AbortSignal): Promise<SettingsMap> {
  if (scope === 'local') {
    const payload = asRecord(await requestJson<unknown>('/api/config', { signal }));
    return toMap(payload.editable, scope);
  }
  if (scope === 'paired') {
    const payload = asRecord(await requestJson<unknown>(`/api/nodes/${encodeURIComponent(nodeId)}/settings`, { signal }));
    return toMap(payload.items, scope);
  }
  throw new NodeModuleError('node_not_paired', 409);
}

export async function saveSettings(nodeId: string, scope: ControlScope, updates: Readonly<Record<string, string>>): Promise<void> {
  const clean = Object.fromEntries(Object.entries(updates).filter(([key]) => KEY_PATTERN.test(key)));
  if (scope === 'local') {
    await requestJson('/api/config', { method: 'PUT', body: JSON.stringify(clean) });
    return;
  }
  if (scope === 'paired') {
    await requestJson(`/api/nodes/${encodeURIComponent(nodeId)}`, { method: 'PUT', body: JSON.stringify({ settings: clean }) });
    return;
  }
  throw new NodeModuleError('node_not_paired', 409);
}
