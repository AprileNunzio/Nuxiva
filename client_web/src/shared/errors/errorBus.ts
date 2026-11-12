export type ErrorSeverity = 'warning' | 'critical';

export interface ReportedError {
  readonly id: number;
  readonly code: string;
  readonly severity: ErrorSeverity;
  readonly occurredAt: number;
  readonly cause: unknown;
}

type Listener = (error: ReportedError) => void;

const DEDUPE_WINDOW_MS = 15000;
const listeners = new Set<Listener>();
const lastNotified = new Map<string, number>();
let sequence = 0;

export function reportError(code: string, cause: unknown, severity: ErrorSeverity = 'warning'): void {
  console.error(`[nuxiva:${code}]`, cause);
  const now = Date.now();
  const previous = lastNotified.get(code);
  if (previous !== undefined && now - previous < DEDUPE_WINDOW_MS) {
    return;
  }
  lastNotified.set(code, now);
  sequence += 1;
  const entry: ReportedError = { id: sequence, code, severity, occurredAt: now, cause };
  listeners.forEach((listener) => listener(entry));
}

export function subscribeErrors(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
