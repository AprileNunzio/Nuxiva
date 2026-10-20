import { asRecord, asString } from '../../shared/data/http';

export const REF = /^(cloud:[A-Za-z0-9._-]{1,64}\/)?[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,159}$/;
export const MODEL_NAME = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}$/;

export type Origin = 'local' | 'server' | 'cloud' | 'lan';

export interface BrainRef {
  readonly ref: string;
  readonly model: string;
  readonly origin: Origin;
  readonly provider: string;
  readonly available: boolean;
}

export const num = (value: unknown, fallback = 0): number => (typeof value === 'number' && Number.isFinite(value) ? value : fallback);
export const list = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);

export function parseRef(value: unknown): BrainRef | null {
  const r = asRecord(value);
  const ref = asString(r.ref, 230) ?? asString(r.name, 230);
  if (!ref || !REF.test(ref)) {
    return null;
  }
  const origin = r.origin === 'cloud' || r.origin === 'server' || r.origin === 'lan' ? r.origin : 'local';
  return {
    ref,
    model: asString(r.model, 160) ?? ref,
    origin,
    provider: asString(r.provider, 80) ?? '',
    available: r.available !== false,
  };
}

export const refs = (value: unknown): BrainRef[] => list(value).map(parseRef).filter((r): r is BrainRef => r !== null);
