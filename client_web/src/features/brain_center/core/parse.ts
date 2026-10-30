import { asRecord, asString } from './http';
import type { BrainRef, Origin } from './types';

export const REF = /^(cloud:[A-Za-z0-9._-]{1,64}\/)?[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,159}$/;
export const MODEL_NAME = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}$/;
export const PROVIDER_ID = /^[a-z0-9][a-z0-9._-]{0,63}$/;
export const HTTPS_URL = /^https:\/\/[^\s"'<>]{1,300}$/;
export const SERVICE_URL = /^https?:\/\/[A-Za-z0-9.\-:[\]]+(\/[A-Za-z0-9._~\-/%]*)?$/;
export const MAX_CHAIN = 12;

const ORIGINS: readonly Origin[] = ['local', 'server', 'cloud', 'lan'];

export const num = (value: unknown, fallback = 0): number =>
  typeof value === 'number' && Number.isFinite(value) ? value : fallback;

export const list = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);

export const strings = (value: unknown, max = 100, length = 200): string[] =>
  list(value)
    .map((item) => asString(item, length))
    .filter((item): item is string => item !== null)
    .slice(0, max);

export function parseRef(value: unknown): BrainRef | null {
  const r = asRecord(value);
  const ref = asString(r.ref, 230) ?? asString(r.name, 230);
  if (!ref || !REF.test(ref)) {
    return null;
  }
  const origin = ORIGINS.find((item) => item === r.origin) ?? 'local';
  return {
    ref,
    model: asString(r.model, 160) ?? ref,
    origin,
    provider: asString(r.provider, 80) ?? '',
    available: r.available !== false,
  };
}

export const refs = (value: unknown): BrainRef[] =>
  list(value)
    .map(parseRef)
    .filter((r): r is BrainRef => r !== null);

export function providerPath(id: string): string {
  if (!PROVIDER_ID.test(id)) {
    throw new RangeError('invalid_provider');
  }
  return encodeURIComponent(id);
}
