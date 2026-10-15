export class NodeModuleError extends Error {
  constructor(
    readonly code: string,
    readonly status: number,
  ) {
    super(code);
    this.name = 'NodeModuleError';
  }
}

const JSON_HEADERS = { Accept: 'application/json', 'Content-Type': 'application/json' };

export async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { cache: 'no-store', ...init, headers: { ...JSON_HEADERS, ...init?.headers } });
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const detail = typeof payload === 'object' && payload !== null ? (payload as { detail?: unknown }).detail : null;
    throw new NodeModuleError(typeof detail === 'string' ? detail : 'request_failed', response.status);
  }
  return (await response.json()) as T;
}

export function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

export function asString(value: unknown, max = 200): string | null {
  return typeof value === 'string' && value.trim() ? value.trim().slice(0, max) : null;
}

export function asStringList(value: unknown, max = 32): string[] {
  return Array.isArray(value) ? value.map((v) => asString(v, 120)).filter((v): v is string => v !== null).slice(0, max) : [];
}
