import { createConnectivityMonitor, ProbeResult } from './monitor';

export const SERVER_RESTORED_EVENT = 'nuxiva:server-restored';
const PROBE_PATH = '/healthz';
const PROBE_TIMEOUT_MS = 5000;
const PHASE = /^[A-Z_]{1,32}$/;

async function probeServer(): Promise<ProbeResult> {
  try {
    const response = await fetch(PROBE_PATH, { cache: 'no-store', signal: AbortSignal.timeout(PROBE_TIMEOUT_MS) });
    if (!response.ok) {
      return { ok: false, detail: `HTTP ${response.status} ${PROBE_PATH}` };
    }
    const body = (await response.json()) as { phase?: unknown };
    return { ok: true, detail: typeof body.phase === 'string' && PHASE.test(body.phase) ? body.phase : null };
  } catch (cause) {
    const name = cause instanceof Error ? cause.name : 'Error';
    const message = cause instanceof Error ? cause.message : String(cause);
    return { ok: false, detail: `${name}: ${message}`.slice(0, 160) };
  }
}

export const connectivity = createConnectivityMonitor({
  probe: probeServer,
  now: () => Date.now(),
  setTimer: (task, ms) => window.setTimeout(task, ms),
  clearTimer: (id) => window.clearTimeout(id),
  onRestored: () => window.dispatchEvent(new Event(SERVER_RESTORED_EVENT)),
});

export function onServerRestored(listener: () => void): () => void {
  window.addEventListener(SERVER_RESTORED_EVENT, listener);
  return () => window.removeEventListener(SERVER_RESTORED_EVENT, listener);
}

if (typeof window !== 'undefined') {
  window.addEventListener('online', () => connectivity.retryNow());
}
