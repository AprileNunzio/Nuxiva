import { describe, expect, it } from 'vitest';
import { diagnose } from '../diagnosis/diagnose';
import { FetchFailure } from '../../http/fetchFailure';
import { createConnectivityMonitor, ProbeResult, RESTORED_VISIBLE_MS, RETRY_STEPS_MS } from './monitor';

function harness(results: ProbeResult[]) {
  let clock = 1000;
  const timers = new Map<number, { at: number; task: () => void }>();
  let nextId = 1;
  let restored = 0;
  const monitor = createConnectivityMonitor({
    probe: async () => results.shift() ?? { ok: false, detail: 'none' },
    now: () => clock,
    setTimer: (task, ms) => {
      const id = nextId++;
      timers.set(id, { at: clock + ms, task });
      return id;
    },
    clearTimer: (id) => {
      timers.delete(id);
    },
    onRestored: () => {
      restored += 1;
    },
  });
  const advance = async (ms: number) => {
    clock += ms;
    for (const [id, timer] of [...timers]) {
      if (timer.at <= clock) {
        timers.delete(id);
        timer.task();
      }
    }
    await Promise.resolve();
    await Promise.resolve();
  };
  return { monitor, advance, restoredCount: () => restored, pending: () => timers.size };
}

const failure = (path: string) => diagnose(new FetchFailure('GET', path, true, 5, 'Failed to fetch'));

describe('connectivity monitor', () => {
  it('groups simultaneous failures into one outage', () => {
    const { monitor } = harness([]);
    expect(monitor.noteFailure('core_app_load_failed', failure('/api/state'))).toBe(true);
    expect(monitor.noteFailure('node_bluetooth_unavailable', failure('/api/bluetooth'))).toBe(false);
    expect(monitor.noteFailure('core_app_load_failed', failure('/api/state'))).toBe(false);
    const snap = monitor.getSnapshot();
    expect(snap.status).toBe('down');
    expect(snap.calls).toHaveLength(2);
    expect(snap.calls.find((c) => c.code === 'core_app_load_failed')?.count).toBe(2);
  });

  it('backs off between probes and announces the recovery once', async () => {
    const { monitor, advance, restoredCount } = harness([{ ok: false, detail: 'HTTP 502 /healthz' }, { ok: true, detail: 'READY' }]);
    monitor.noteFailure('core_app_load_failed', failure('/api/state'));
    await advance(RETRY_STEPS_MS[0]);
    expect(monitor.getSnapshot()).toMatchObject({ status: 'down', attempts: 1, lastProbe: 'HTTP 502 /healthz' });
    await advance(RETRY_STEPS_MS[0]);
    expect(monitor.getSnapshot().status).toBe('down');
    await advance(RETRY_STEPS_MS[1] - RETRY_STEPS_MS[0]);
    expect(monitor.getSnapshot()).toMatchObject({ status: 'restored', lastProbe: 'READY' });
    expect(restoredCount()).toBe(1);
    await advance(RESTORED_VISIBLE_MS);
    expect(monitor.getSnapshot()).toMatchObject({ status: 'online', calls: [] });
  });

  it('retries immediately on demand and keeps the toast hidden until recovery', async () => {
    const { monitor, advance } = harness([{ ok: false, detail: 'TypeError: Failed to fetch' }, { ok: true, detail: null }]);
    monitor.noteFailure('x', failure('/api/x'));
    monitor.hide();
    monitor.retryNow();
    await advance(0);
    expect(monitor.getSnapshot()).toMatchObject({ attempts: 1, hidden: true });
    monitor.retryNow();
    await advance(0);
    expect(monitor.getSnapshot()).toMatchObject({ status: 'restored', hidden: false });
  });

  it('flags offline outages', () => {
    const { monitor } = harness([]);
    monitor.noteFailure('x', diagnose(new FetchFailure('GET', '/api/x', false, 1, 'Failed to fetch')));
    expect(monitor.getSnapshot().offline).toBe(true);
  });
});
