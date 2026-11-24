export class NodeModuleError extends Error {
  constructor(
    readonly code: string,
    readonly status: number,
    readonly detailMessage?: string,
    readonly method?: string,
    readonly path?: string,
  ) {
    super(detailMessage ? `${code}: ${detailMessage}` : code);
    this.name = 'NodeModuleError';
  }
}

const JSON_HEADERS = { Accept: 'application/json', 'Content-Type': 'application/json', 'X-Nuxiva-Request': '1' };

export async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? 'GET').toUpperCase();
  const path = url.split(/[?#]/)[0].slice(0, 200);
  const response = await fetch(url, { cache: 'no-store', credentials: 'same-origin', ...init, headers: { ...JSON_HEADERS, ...init?.headers } });
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    let code = 'request_failed';
    let detailMessage: string | undefined;
    if (typeof payload === 'object' && payload !== null) {
      const detail = (payload as { detail?: unknown }).detail;
      if (typeof detail === 'string') {
        code = detail;
      } else if (typeof detail === 'object' && detail !== null) {
        const obj = detail as { code?: string; message?: string };
        if (typeof obj.code === 'string') code = obj.code;
        if (typeof obj.message === 'string') detailMessage = obj.message;
      }
    }
    throw new NodeModuleError(code, response.status, detailMessage, method, path);
  }
  try {
    return (await response.json()) as T;
  } catch (cause) {
    if (cause instanceof SyntaxError) {
      throw new NodeModuleError('invalid_response', response.status, cause.message.slice(0, 200), method, path);
    }
    throw cause;
  }
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
