import { getJson, sendJson } from '../shared/http';
import { AgentDraft, CatalogItem, FleetAgentDetail, FleetFilters, FleetPage, LinkKind } from './types';

const BASE = '/api/fleet';
export const PAGE_SIZE = 50;

export function listUrl(filters: FleetFilters, cursor: string): string {
  const params = new URLSearchParams({ limit: String(PAGE_SIZE) });
  (Object.keys(filters) as (keyof FleetFilters)[]).forEach((key) => filters[key] && params.set(key, filters[key]));
  if (cursor) {
    params.set('cursor', cursor);
  }
  return `${BASE}/agents?${params.toString()}`;
}

export const fetchPage = (filters: FleetFilters, cursor: string, signal: AbortSignal) => getJson<FleetPage>(listUrl(filters, cursor), signal);
export const fetchDetail = (id: string, signal?: AbortSignal) => getJson<FleetAgentDetail>(`${BASE}/agents/${encodeURIComponent(id)}`, signal);
export const fetchCatalog = (kind: LinkKind, query: string, signal?: AbortSignal) =>
  getJson<{ items: CatalogItem[] }>(`${BASE}/catalog?kind=${kind}&q=${encodeURIComponent(query)}&limit=30`, signal);
export const suggest = (purpose: string) => sendJson<{ tools: string[]; widgets: string[] }>(`${BASE}/suggest`, 'POST', { purpose });
export const createAgent = (draft: AgentDraft) => sendJson<FleetAgentDetail>(`${BASE}/agents`, 'POST', draft);
export const updateAgent = (id: string, changes: Record<string, unknown>) =>
  sendJson<FleetAgentDetail>(`${BASE}/agents/${encodeURIComponent(id)}`, 'PUT', changes);
export const deleteAgent = (id: string) => sendJson<{ ok: boolean }>(`${BASE}/agents/${encodeURIComponent(id)}`, 'DELETE');
export const attach = (id: string, kind: LinkKind, refs: readonly string[]) =>
  sendJson<FleetAgentDetail>(`${BASE}/agents/${encodeURIComponent(id)}/links`, 'POST', { kind, refs });
export const detach = (id: string, kind: LinkKind, ref: string) =>
  sendJson<FleetAgentDetail>(`${BASE}/agents/${encodeURIComponent(id)}/links/${kind}/${encodeURIComponent(ref)}`, 'DELETE');
export const bulkState = (filters: FleetFilters, state: string) =>
  sendJson<{ changed: number; more: boolean }>(`${BASE}/bulk/state`, 'POST', {
    state,
    from_state: filters.state,
    kind: filters.kind,
    category: filters.category,
    origin: filters.origin,
    q: filters.q,
  });
