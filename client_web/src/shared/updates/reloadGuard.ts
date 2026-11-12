export const MAX_ATTEMPTS = 2;
export const WINDOW_MS = 10 * 60 * 1000;
export const BASE_POLL_MS = 20000;
export const MAX_POLL_MS = 15 * 60 * 1000;
const KEY = 'nuxiva.update.reload-guard';
const TARGET = /^\/[A-Za-z0-9._~\/-]{1,512}$/;

export interface ReloadRecord {
  readonly target: string;
  readonly attempts: number;
  readonly at: number;
}

export function parseRecord(raw: string | null): ReloadRecord | null {
  if (!raw || raw.length > 2048) {
    return null;
  }
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!value || typeof value !== 'object') {
    return null;
  }
  const { target, attempts, at } = value as Record<string, unknown>;
  if (typeof target !== 'string' || !TARGET.test(target)) {
    return null;
  }
  if (typeof attempts !== 'number' || !Number.isInteger(attempts) || attempts < 0 || attempts > 1000) {
    return null;
  }
  if (typeof at !== 'number' || !Number.isFinite(at) || at < 0) {
    return null;
  }
  return { target, attempts, at };
}

function active(record: ReloadRecord | null, target: string, now: number): record is ReloadRecord {
  return Boolean(record && record.target === target && now - record.at >= 0 && now - record.at < WINDOW_MS);
}

export function canAutoReload(record: ReloadRecord | null, target: string, now: number): boolean {
  return !active(record, target, now) || record.attempts < MAX_ATTEMPTS;
}

export function nextRecord(record: ReloadRecord | null, target: string, now: number): ReloadRecord {
  return { target, attempts: active(record, target, now) ? record.attempts + 1 : 1, at: now };
}

export function settled(record: ReloadRecord | null, loaded: string | null): boolean {
  return Boolean(record && loaded && record.target === loaded);
}

export function pollDelay(failures: number): number {
  const step = Math.min(Math.max(0, Math.floor(failures)), 16);
  return Math.min(BASE_POLL_MS * 2 ** step, MAX_POLL_MS);
}

function storage(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function readRecord(): ReloadRecord | null {
  const store = storage();
  if (!store) {
    return null;
  }
  try {
    return parseRecord(store.getItem(KEY));
  } catch {
    return null;
  }
}

export function writeRecord(record: ReloadRecord | null): void {
  const store = storage();
  if (!store) {
    return;
  }
  try {
    if (record) {
      store.setItem(KEY, JSON.stringify(record));
    } else {
      store.removeItem(KEY);
    }
  } catch (error) {
    console.warn('[updates] reload guard not persisted', error);
  }
}
