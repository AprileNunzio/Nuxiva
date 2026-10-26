import { CollaudoResult, UpdateHistoryResponse, UpdatePolicy, UpdaterStatus } from './types';

const BASE = '/api/v5/updater';
const JSON_HEADERS = { Accept: 'application/json', 'Content-Type': 'application/json' };

export class UpdaterApiError extends Error {
  constructor(
    readonly code: string,
    readonly status: number,
  ) {
    super(code);
    this.name = 'UpdaterApiError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, { cache: 'no-store', ...init, headers: { ...JSON_HEADERS, ...init?.headers } });
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const detail = typeof payload === 'object' && payload !== null ? (payload as { detail?: unknown }).detail : null;
    throw new UpdaterApiError(typeof detail === 'string' ? detail : 'request_failed', response.status);
  }
  return (await response.json()) as T;
}

const confirmed = JSON.stringify({ confirm: true });

export const fetchStatus = (signal?: AbortSignal) => request<UpdaterStatus>('/status', { signal });
export const checkNow = () => request<UpdaterStatus>('/check', { method: 'POST' });
export const applyUpdate = () => request<{ status: string; target_rev: string }>('/apply', { method: 'POST', body: confirmed });
export const savePolicy = (policy: UpdatePolicy) =>
  request<UpdaterStatus>('/policy', { method: 'PUT', body: JSON.stringify(policy) });
export const runCollaudo = () => request<CollaudoResult>('/collaudo', { method: 'POST' });
export const updateAllNodes = () => request<{ queued: string[] }>('/nodes/update', { method: 'POST', body: confirmed });
export const updateNode = (nodeId: string) =>
  request<{ queued: string[] }>(`/nodes/${encodeURIComponent(nodeId)}/update`, { method: 'POST', body: confirmed });
export const fetchHistory = (offset = 0, limit = 20, signal?: AbortSignal) =>
  request<UpdateHistoryResponse>(`/history?offset=${offset}&limit=${limit}`, { signal });
