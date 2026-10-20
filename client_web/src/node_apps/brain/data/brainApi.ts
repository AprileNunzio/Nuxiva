import { asRecord, asString, requestJson } from '../../shared/data/http';
import { BrainRef, REF, list, num, parseRef, refs } from './parse';

export const ROUTING = ['auto', '1', '0'] as const;
export type Routing = (typeof ROUTING)[number];

export interface RoleState {
  readonly id: string;
  readonly label: string;
  readonly custom: boolean;
  readonly entries: readonly BrainRef[];
  readonly effective: readonly string[];
  readonly active: BrainRef | null;
}

export interface Fit {
  readonly level: 'ok' | 'slow' | 'no';
  readonly tps: number;
  readonly where: string;
}

export interface CatalogModel {
  readonly name: string;
  readonly label: string;
  readonly sizeGb: number | null;
  readonly category: string;
  readonly notes: string;
  readonly installed: boolean;
  readonly fit: Fit;
  readonly licenseWarning: string;
}

export interface Hardware {
  readonly ramGb: number;
  readonly vramGb: number;
  readonly gpu: string | null;
}

export interface BrainOverview {
  readonly routing: Routing;
  readonly roles: readonly RoleState[];
  readonly catalog: readonly CatalogModel[];
  readonly hardware: Hardware;
  readonly last: { readonly ref: BrainRef; readonly ms: number; readonly kind: string; readonly at: number } | null;
}

export interface RouteResult {
  readonly kind: string;
  readonly reason: string;
  readonly models: readonly string[];
  readonly skipped: readonly { readonly ref: string; readonly why: string }[];
}

function parseRole(value: unknown): RoleState | null {
  const r = asRecord(value);
  const id = asString(r.id, 40);
  if (!id || !/^[a-z0-9_]{1,40}$/.test(id)) {
    return null;
  }
  return {
    id,
    label: asString(r.label, 80) ?? id,
    custom: r.custom === true,
    entries: refs(r.entries),
    effective: list(r.effective).filter((m): m is string => typeof m === 'string' && REF.test(m)),
    active: parseRef(r.active),
  };
}

function parseCatalog(value: unknown): CatalogModel | null {
  const c = asRecord(value);
  const name = asString(c.name, 120);
  if (!name) {
    return null;
  }
  const fit = asRecord(c.fit);
  return {
    name,
    label: asString(c.label, 80) ?? name,
    sizeGb: typeof c.size_gb === 'number' ? c.size_gb : null,
    category: asString(c.category, 30) ?? 'other',
    notes: asString(c.notes, 300) ?? '',
    installed: c.installed === true,
    fit: {
      level: fit.level === 'no' || fit.level === 'slow' ? fit.level : 'ok',
      tps: num(fit.tps),
      where: asString(fit.where, 20) ?? '',
    },
    licenseWarning: asString(asRecord(c.license).warning, 300) ?? '',
  };
}

export async function fetchBrains(signal?: AbortSignal): Promise<BrainOverview> {
  const raw = asRecord(await requestJson<unknown>('/api/brains', { signal }));
  const hw = asRecord(raw.hardware);
  const last = asRecord(raw.last);
  const lastRef = parseRef({ ...asRecord(raw.last_used), ref: asString(last.model, 230) });
  return {
    routing: ROUTING.find((r) => r === raw.routing) ?? 'auto',
    roles: list(raw.roles).map(parseRole).filter((r): r is RoleState => r !== null),
    catalog: list(raw.catalog).map(parseCatalog).filter((c): c is CatalogModel => c !== null),
    hardware: { ramGb: num(hw.ram_gb), vramGb: num(hw.vram_gb), gpu: asString(hw.gpu, 80) },
    last: lastRef ? { ref: lastRef, ms: num(last.ms), kind: asString(last.kind, 20) ?? '', at: num(last.at) } : null,
  };
}

export async function saveRole(roleId: string, models: readonly string[]): Promise<BrainOverview> {
  if (!models.every((m) => REF.test(m)) || models.length > 12) {
    throw new Error('invalid_models');
  }
  await requestJson('/api/brains', { method: 'PUT', body: JSON.stringify({ [roleId]: models }) });
  return fetchBrains();
}

export async function saveRouting(routing: Routing): Promise<BrainOverview> {
  await requestJson('/api/brains', { method: 'PUT', body: JSON.stringify({ routing }) });
  return fetchBrains();
}

export async function fetchPool(signal?: AbortSignal): Promise<BrainRef[]> {
  return refs(asRecord(await requestJson<unknown>('/api/brains/assignments', { signal })).pool);
}

export async function testRoute(text: string): Promise<RouteResult> {
  const raw = asRecord(await requestJson<unknown>('/api/brains/test', { method: 'POST', body: JSON.stringify({ text: text.slice(0, 2000) }) }));
  return {
    kind: asString(raw.kind, 20) ?? '',
    reason: asString(raw.reason, 200) ?? '',
    models: list(raw.models).filter((m): m is string => typeof m === 'string').slice(0, 12),
    skipped: list(raw.skipped)
      .map(asRecord)
      .map((s) => ({ ref: asString(s.ref, 230) ?? '', why: asString(s.why, 120) ?? '' }))
      .slice(0, 12),
  };
}
