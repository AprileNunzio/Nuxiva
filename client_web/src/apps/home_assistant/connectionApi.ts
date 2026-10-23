export type ProbeState = 'ok' | 'auth' | 'no_token' | 'unreachable' | 'timeout' | 'tls' | 'redirect' | 'not_home_assistant' | 'invalid' | 'error';

export interface HomeConnection {
  readonly urls: readonly string[];
  readonly tokenSet: boolean;
  readonly verifySsl: boolean;
  readonly status: string;
  readonly error: string;
  readonly activeUrl: string;
  readonly version: string;
  readonly name: string;
  readonly suggestions: readonly string[];
}

export interface ProbeResult {
  readonly url: string;
  readonly ok: boolean;
  readonly state: ProbeState;
  readonly message: string;
  readonly version: string;
  readonly name: string;
  readonly ms: number;
}

export interface ConnectionForm {
  readonly urls: readonly string[];
  readonly token: string;
  readonly clearToken: boolean;
  readonly verifySsl: boolean;
}

const STATES: readonly ProbeState[] = ['ok', 'auth', 'no_token', 'unreachable', 'timeout', 'tls', 'redirect', 'not_home_assistant', 'invalid', 'error'];

const record = (value: unknown): Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
const text = (value: unknown): string => (typeof value === 'string' ? value : '');
const list = (value: unknown): string[] => (Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []);

async function call(path: string, method: 'GET' | 'PUT' | 'POST', body?: unknown): Promise<unknown> {
  const response = await fetch(path, {
    method,
    cache: 'no-store',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = record(payload).detail;
    throw new Error(typeof detail === 'string' ? detail : `HTTP ${response.status}`);
  }
  return payload;
}

const toConnection = (raw: unknown): HomeConnection => {
  const row = record(raw);
  return {
    urls: list(row.urls),
    tokenSet: row.token_set === true,
    verifySsl: row.verify_ssl !== false,
    status: text(row.status),
    error: text(row.error),
    activeUrl: text(row.active_url),
    version: text(row.version),
    name: text(row.name),
    suggestions: list(row.suggestions),
  };
};

const toResult = (raw: unknown): ProbeResult => {
  const row = record(raw);
  const state = text(row.state) as ProbeState;
  return {
    url: text(row.url),
    ok: row.ok === true,
    state: STATES.includes(state) ? state : 'error',
    message: text(row.message),
    version: text(row.version),
    name: text(row.name),
    ms: typeof row.ms === 'number' ? row.ms : 0,
  };
};

const payload = (form: ConnectionForm) => ({
  urls: form.urls.map((item) => item.trim()).filter(Boolean),
  token: form.token.trim(),
  clear_token: form.clearToken,
  verify_ssl: form.verifySsl,
});

export const loadConnection = async (): Promise<HomeConnection> => toConnection(await call('/api/home/connection', 'GET'));
export const saveConnection = async (form: ConnectionForm): Promise<HomeConnection> => toConnection(await call('/api/home/connection', 'PUT', payload(form)));
export const testConnection = async (form: ConnectionForm): Promise<readonly ProbeResult[]> => {
  const body = record(await call('/api/home/connection/test', 'POST', payload(form)));
  return Array.isArray(body.results) ? body.results.map(toResult) : [];
};
