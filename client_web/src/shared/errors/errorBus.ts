import { connectivity } from './connectivity/connectivity';
import { Diagnosis, diagnose, isConnectivityFailure } from './diagnosis/diagnose';

export type ErrorSeverity = 'warning' | 'critical';

export const SERVER_UNREACHABLE = 'server_unreachable';

export interface ReportedError {
  readonly id: number;
  readonly code: string;
  readonly severity: ErrorSeverity;
  readonly occurredAt: number;
  readonly cause: unknown;
  readonly diagnosis: Diagnosis;
}

type Listener = (error: ReportedError) => void;

const DEDUPE_WINDOW_MS = 15000;
const listeners = new Set<Listener>();
const lastNotified = new Map<string, number>();
let sequence = 0;

function publish(code: string, cause: unknown, severity: ErrorSeverity, diagnosis: Diagnosis, now: number): void {
  sequence += 1;
  const entry: ReportedError = { id: sequence, code, severity, occurredAt: now, cause, diagnosis };
  listeners.forEach((listener) => listener(entry));
}

export function reportError(code: string, cause: unknown, severity: ErrorSeverity = 'warning'): void {
  const diagnosis = diagnose(cause);
  console.error(`[nuxiva:${code}]`, diagnosis, cause);
  if (diagnosis.kind === 'aborted') {
    return;
  }
  const now = Date.now();
  if (isConnectivityFailure(diagnosis)) {
    if (connectivity.noteFailure(code, diagnosis)) {
      publish(SERVER_UNREACHABLE, cause, 'warning', diagnosis, now);
    }
    return;
  }
  const key = `${code}|${diagnosis.status ?? ''}|${diagnosis.path ?? ''}`;
  const previous = lastNotified.get(key);
  if (previous !== undefined && now - previous < DEDUPE_WINDOW_MS) {
    return;
  }
  lastNotified.set(key, now);
  publish(code, cause, severity, diagnosis, now);
}

export function subscribeErrors(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
