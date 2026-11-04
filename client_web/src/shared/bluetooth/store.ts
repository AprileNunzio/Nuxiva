import { reportError } from '../errors/errorBus';
import { fetchBluetooth } from './api';
import { BluetoothState } from './model';

const SCAN_MS = 1500;
const IDLE_MS = 5000;
const HIDDEN_MS = 15000;

export interface BluetoothSnapshot {
  readonly state: BluetoothState | null;
  readonly busy: string | null;
  readonly reachable: boolean;
  readonly scanRequestedUntil: number;
}

type Listener = () => void;

const listeners = new Set<Listener>();
let snapshot: BluetoothSnapshot = { state: null, busy: null, reachable: true, scanRequestedUntil: 0 };
let timer: number | null = null;
let inflight: AbortController | null = null;
let failures = 0;
let queue: Promise<void> = Promise.resolve();

function emit(next: Partial<BluetoothSnapshot>): void {
  snapshot = { ...snapshot, ...next };
  listeners.forEach((listener) => listener());
}

const scanning = (): boolean =>
  snapshot.scanRequestedUntil > Date.now() || snapshot.state?.scanning === true || snapshot.state?.controller.discovering === true;

function schedule(): void {
  if (timer !== null) {
    window.clearTimeout(timer);
  }
  if (listeners.size === 0) {
    timer = null;
    return;
  }
  const delay = document.visibilityState === 'hidden' ? HIDDEN_MS : scanning() ? SCAN_MS : IDLE_MS;
  timer = window.setTimeout(() => void poll(), delay);
}

async function poll(): Promise<void> {
  inflight?.abort();
  const controller = new AbortController();
  inflight = controller;
  try {
    const state = await fetchBluetooth(controller.signal);
    failures = 0;
    emit({ state, reachable: true });
  } catch (cause) {
    if (controller.signal.aborted) {
      return;
    }
    if (failures++ === 0) {
      reportError('node_bluetooth_unavailable', cause);
    }
    emit({ reachable: false });
  } finally {
    if (inflight === controller) {
      inflight = null;
      schedule();
    }
  }
}

async function execute(key: string, task: () => Promise<BluetoothState | void>, errorCode: string): Promise<boolean> {
  emit({ busy: key });
  try {
    const next = await task();
    if (next) {
      emit({ state: next, reachable: true });
      if (next.notice) {
        reportError(next.notice, new Error(next.notice));
      }
    }
    return true;
  } catch (cause) {
    reportError(errorCode, cause);
    return false;
  } finally {
    emit({ busy: null });
    void poll();
  }
}

export const bluetoothStore = {
  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    if (listeners.size === 1) {
      void poll();
    }
    return () => {
      listeners.delete(listener);
      if (listeners.size === 0) {
        inflight?.abort();
        schedule();
      }
    };
  },
  getSnapshot(): BluetoothSnapshot {
    return snapshot;
  },
  refresh(): void {
    void poll();
  },
  markScanning(seconds: number): void {
    emit({ scanRequestedUntil: Date.now() + seconds * 1000 });
    schedule();
  },
  run(key: string, task: () => Promise<BluetoothState | void>, errorCode: string): Promise<boolean> {
    const job = queue.then(() => execute(key, task, errorCode));
    queue = job.then(
      () => undefined,
      () => undefined,
    );
    return job;
  },
};
