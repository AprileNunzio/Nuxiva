import { asRecord, asString, requestJson } from './http';
import { MAX_CHAIN, REF, list, num, parseRef, refs, strings } from './parse';
import {
  BrainOverview,
  BrainRef,
  CatalogModel,
  ROUTING,
  RoleScope,
  RoleState,
  RoleStrategy,
  RouteResult,
  Routing,
  SCOPES,
  STRATEGIES,
} from './types';

const ROLE_ID = /^[a-z0-9_]{1,40}$/;

function parseRole(value: unknown): RoleState | null {
  const r = asRecord(value);
  const id = asString(r.id, 40);
  if (!id || !ROLE_ID.test(id)) {
    return null;
  }
  return {
    id,
    custom: r.custom === true,
    entries: refs(r.entries),
    effective: strings(r.effective, MAX_CHAIN, 230).filter((m) => REF.test(m)),
    active: parseRef(r.active),
    scope: SCOPES.find((s) => s === r.scope) ?? 'anywhere',
    strategy: STRATEGIES.find((s) => s === r.strategy) ?? 'order',
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
    installed: c.installed === true,
    fit: {
      level: fit.level === 'no' || fit.level === 'slow' ? fit.level : 'ok',
      tps: num(fit.tps),
      where: asString(fit.where, 20) ?? '',
    },
    restricted: asString(asRecord(c.license).warning, 300) !== null,
  };
}

export function parseOverview(value: unknown): BrainOverview {
  const raw = asRecord(value);
  const hw = asRecord(raw.hardware);
  const last = asRecord(raw.last);
  const lastRef = parseRef({ ...asRecord(raw.last_used), ref: asString(last.model, 230) });
  return {
    routing: ROUTING.find((r) => r === raw.routing) ?? 'auto',
    roles: list(raw.roles).map(parseRole).filter((r): r is RoleState => r !== null),
    catalog: list(raw.catalog).map(parseCatalog).filter((c): c is CatalogModel => c !== null),
    hardware: { ramGb: num(hw.ram_gb), vramGb: num(hw.vram_gb), gpu: asString(hw.gpu, 80) },
    last: lastRef ? { ref: lastRef, ms: num(last.ms), at: num(last.at) } : null,
  };
}

export async function fetchOverview(signal?: AbortSignal): Promise<BrainOverview> {
  return parseOverview(await requestJson<unknown>('/api/brains', { signal }));
}

export async function saveRoleChain(roleId: string, models: readonly string[]): Promise<BrainOverview> {
  if (!ROLE_ID.test(roleId) || models.length > MAX_CHAIN || !models.every((m) => REF.test(m))) {
    throw new RangeError('invalid_models');
  }
  return parseOverview(await requestJson<unknown>('/api/brains', { method: 'PUT', body: JSON.stringify({ [roleId]: models }) }));
}

export async function saveRouting(routing: Routing): Promise<BrainOverview> {
  return parseOverview(await requestJson<unknown>('/api/brains', { method: 'PUT', body: JSON.stringify({ routing }) }));
}

export async function saveRoleSettings(roleId: string, change: { scope?: RoleScope; strategy?: RoleStrategy }): Promise<BrainOverview> {
  if (!ROLE_ID.test(roleId)) {
    throw new RangeError('invalid_role');
  }
  return parseOverview(
    await requestJson<unknown>(`/api/brains/settings/${encodeURIComponent(roleId)}`, { method: 'PUT', body: JSON.stringify(change) }),
  );
}

export async function fetchPool(signal?: AbortSignal): Promise<BrainRef[]> {
  return refs(asRecord(await requestJson<unknown>('/api/brains/assignments', { signal })).pool);
}

export async function testRoute(text: string): Promise<RouteResult> {
  const raw = asRecord(
    await requestJson<unknown>('/api/brains/test', { method: 'POST', body: JSON.stringify({ text: text.slice(0, 2000) }) }),
  );
  return { kind: asString(raw.kind, 20) ?? '', models: strings(raw.models, MAX_CHAIN, 230) };
}

export async function fetchRevision(signal?: AbortSignal): Promise<string> {
  return asString(asRecord(await requestJson<unknown>('/api/v2/brain/config', { signal })).revision, 64) ?? '';
}
