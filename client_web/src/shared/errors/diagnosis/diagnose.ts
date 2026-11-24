import { FetchFailure } from '../../http/fetchFailure';

export type FailureKind = 'unreachable' | 'offline' | 'timeout' | 'aborted' | 'http' | 'invalid_response' | 'application';

export interface Diagnosis {
  readonly kind: FailureKind;
  readonly method: string | null;
  readonly path: string | null;
  readonly status: number | null;
  readonly serverCode: string | null;
  readonly serverMessage: string | null;
  readonly elapsedMs: number | null;
  readonly raw: string;
}

const NETWORK_MESSAGES = [/failed to fetch/i, /networkerror/i, /load failed/i, /network request failed/i, /fetch failed/i];
const CODE = /^[a-z][a-z0-9_.:-]{0,79}$/;
const METHOD = /^[A-Z]{3,10}$/;
const PATH = /^(https?:\/\/[^\s/]+)?\/[^\s?#]{0,199}$/;
const CONTROL = /[\u0000-\u001f\u007f-\u009f​-‏‪-‮⁦-⁩]/g;

const clean = (value: string, max: number): string => value.replace(CONTROL, ' ').trim().slice(0, max);

const text = (value: unknown, max: number): string | null =>
  typeof value === 'string' && value.trim() ? clean(value, max) : null;

const matching = (value: unknown, pattern: RegExp): string | null =>
  typeof value === 'string' && pattern.test(value) ? value : null;

const named = (cause: unknown, name: string): boolean =>
  typeof cause === 'object' && cause !== null && (cause as { name?: unknown }).name === name;

const online = (): boolean => typeof navigator === 'undefined' || navigator.onLine !== false;

function rawText(cause: unknown): string {
  if (cause instanceof Error) {
    return clean(`${cause.name}: ${cause.message}`, 300);
  }
  if (typeof cause === 'string') {
    return clean(cause, 300) || 'unknown';
  }
  return clean(String(cause), 300) || 'unknown';
}

export function diagnose(cause: unknown): Diagnosis {
  const base: Diagnosis = {
    kind: 'application',
    method: null,
    path: null,
    status: null,
    serverCode: null,
    serverMessage: null,
    elapsedMs: null,
    raw: rawText(cause),
  };
  if (cause instanceof FetchFailure) {
    return {
      ...base,
      kind: cause.online ? 'unreachable' : 'offline',
      method: matching(cause.method, METHOD),
      path: matching(cause.path, PATH),
      elapsedMs: Number.isFinite(cause.elapsedMs) ? Math.max(0, Math.round(cause.elapsedMs)) : null,
    };
  }
  if (named(cause, 'TimeoutError')) {
    return { ...base, kind: 'timeout' };
  }
  if (named(cause, 'AbortError')) {
    return { ...base, kind: 'aborted' };
  }
  if (cause instanceof TypeError && NETWORK_MESSAGES.some((pattern) => pattern.test(cause.message))) {
    return { ...base, kind: online() ? 'unreachable' : 'offline' };
  }
  if (cause instanceof SyntaxError) {
    return { ...base, kind: 'invalid_response' };
  }
  if (typeof cause !== 'object' || cause === null) {
    return base;
  }
  const record = cause as Record<string, unknown>;
  const status = typeof record.status === 'number' && Number.isInteger(record.status) && record.status >= 100 && record.status <= 599 ? record.status : null;
  if (status === null) {
    return base;
  }
  const code = matching(record.code, CODE);
  return {
    ...base,
    kind: code === 'invalid_response' ? 'invalid_response' : 'http',
    status,
    serverCode: code && code !== 'request_failed' && code !== 'invalid_response' ? code : null,
    serverMessage: text(record.detailMessage, 300),
    method: matching(record.method, METHOD),
    path: matching(record.path, PATH),
  };
}

export const isConnectivityFailure = (diagnosis: Diagnosis): boolean =>
  diagnosis.kind === 'unreachable' || diagnosis.kind === 'offline';

const HTTP_HINTS: ReadonlyArray<readonly [number, string]> = [
  [400, 'hint_http_400'],
  [401, 'hint_http_401'],
  [403, 'hint_http_403'],
  [404, 'hint_http_404'],
  [409, 'hint_http_409'],
  [413, 'hint_http_413'],
  [422, 'hint_http_400'],
  [429, 'hint_http_429'],
  [500, 'hint_http_500'],
  [502, 'hint_http_503'],
  [503, 'hint_http_503'],
  [504, 'hint_http_503'],
];

export function hintKey(diagnosis: Diagnosis): string {
  if (diagnosis.kind === 'http') {
    const match = HTTP_HINTS.find(([status]) => status === diagnosis.status);
    if (match) {
      return match[1];
    }
    return diagnosis.status !== null && diagnosis.status >= 500 ? 'hint_http_500' : 'hint_http_other';
  }
  if (diagnosis.kind === 'aborted') {
    return 'hint_application';
  }
  return `hint_${diagnosis.kind}`;
}

export function outcomeKey(diagnosis: Diagnosis): string {
  return diagnosis.kind === 'aborted' ? 'outcome_application' : `outcome_${diagnosis.kind}`;
}
