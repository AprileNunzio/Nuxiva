import { Diagnosis } from '../diagnosis/diagnose';

export type LinkStatus = 'online' | 'down' | 'restored';

export interface FailedCall {
  readonly code: string;
  readonly diagnosis: Diagnosis;
  readonly count: number;
  readonly firstAt: number;
  readonly lastAt: number;
}

export interface ProbeResult {
  readonly ok: boolean;
  readonly detail: string | null;
}

export interface ConnectivitySnapshot {
  readonly status: LinkStatus;
  readonly offline: boolean;
  readonly since: number | null;
  readonly restoredAt: number | null;
  readonly attempts: number;
  readonly probing: boolean;
  readonly nextProbeAt: number | null;
  readonly lastProbe: string | null;
  readonly hidden: boolean;
  readonly calls: readonly FailedCall[];
}

export interface MonitorDeps {
  readonly probe: () => Promise<ProbeResult>;
  readonly now: () => number;
  readonly setTimer: (task: () => void, ms: number) => number;
  readonly clearTimer: (id: number) => void;
  readonly onRestored: () => void;
}

export const RETRY_STEPS_MS: readonly number[] = [2000, 4000, 8000, 15000, 30000];
export const RESTORED_VISIBLE_MS = 6000;
const MAX_CALLS = 16;

const IDLE: ConnectivitySnapshot = {
  status: 'online',
  offline: false,
  since: null,
  restoredAt: null,
  attempts: 0,
  probing: false,
  nextProbeAt: null,
  lastProbe: null,
  hidden: false,
  calls: [],
};

const callKey = (code: string, diagnosis: Diagnosis): string => `${code}|${diagnosis.method ?? ''}|${diagnosis.path ?? ''}`;

export function createConnectivityMonitor(deps: MonitorDeps) {
  const listeners = new Set<() => void>();
  let snapshot = IDLE;
  let timer: number | null = null;

  const emit = (next: Partial<ConnectivitySnapshot>): void => {
    snapshot = { ...snapshot, ...next };
    listeners.forEach((listener) => listener());
  };

  const clear = (): void => {
    if (timer !== null) {
      deps.clearTimer(timer);
      timer = null;
    }
  };

  const schedule = (): void => {
    clear();
    const delay = RETRY_STEPS_MS[Math.min(snapshot.attempts, RETRY_STEPS_MS.length - 1)];
    timer = deps.setTimer(() => void probe(), delay);
    emit({ nextProbeAt: deps.now() + delay });
  };

  const settle = (): void => {
    clear();
    timer = deps.setTimer(() => {
      timer = null;
      if (snapshot.status === 'restored') {
        emit(IDLE);
      }
    }, RESTORED_VISIBLE_MS);
  };

  async function probe(): Promise<void> {
    if (snapshot.status !== 'down' || snapshot.probing) {
      return;
    }
    clear();
    emit({ probing: true, nextProbeAt: null });
    const result = await deps.probe();
    if (snapshot.status !== 'down') {
      return;
    }
    if (result.ok) {
      emit({ status: 'restored', probing: false, restoredAt: deps.now(), attempts: snapshot.attempts + 1, lastProbe: result.detail, hidden: false, offline: false });
      settle();
      deps.onRestored();
      return;
    }
    emit({ probing: false, attempts: snapshot.attempts + 1, lastProbe: result.detail });
    schedule();
  }

  function noteFailure(code: string, diagnosis: Diagnosis): boolean {
    const now = deps.now();
    const started = snapshot.status !== 'down';
    const base = started ? { ...IDLE, status: 'down' as const, since: now } : snapshot;
    const key = callKey(code, diagnosis);
    const existing = base.calls.find((call) => callKey(call.code, call.diagnosis) === key);
    const updated: FailedCall = existing
      ? { ...existing, diagnosis, count: existing.count + 1, lastAt: now }
      : { code, diagnosis, count: 1, firstAt: now, lastAt: now };
    const calls = [updated, ...base.calls.filter((call) => call !== existing)].slice(0, MAX_CALLS);
    snapshot = { ...base, calls, offline: diagnosis.kind === 'offline' };
    if (started) {
      schedule();
    } else {
      emit({});
    }
    return started;
  }

  return {
    noteFailure,
    retryNow(): void {
      if (snapshot.status === 'down') {
        void probe();
      }
    },
    hide(): void {
      emit({ hidden: true });
    },
    subscribe(listener: () => void): () => void {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    getSnapshot(): ConnectivitySnapshot {
      return snapshot;
    },
  };
}

export type ConnectivityMonitor = ReturnType<typeof createConnectivityMonitor>;
