import { useCallback, useEffect, useRef, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { BluetoothState, fetchBluetooth } from '../data/bluetoothApi';

const IDLE_MS = 5000;
const SCAN_MS = 1500;

export interface BluetoothHandle {
  readonly state: BluetoothState | null;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<BluetoothState | void>, errorCode: string) => Promise<boolean>;
  readonly refresh: () => void;
}

export function useBluetooth(enabled: boolean): BluetoothHandle {
  const [state, setState] = useState<BluetoothState | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const failures = useRef(0);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const controller = new AbortController();
    fetchBluetooth(controller.signal)
      .then((next) => {
        failures.current = 0;
        setState(next);
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted && failures.current++ === 0) {
          reportError('node_bluetooth_unavailable', cause);
        }
      });
    return () => controller.abort();
  }, [enabled, tick]);

  const scanning = state?.scanning === true || state?.controller.discovering === true;
  useEffect(() => {
    if (!enabled) {
      return;
    }
    const timer = window.setTimeout(() => setTick((value) => value + 1), scanning ? SCAN_MS : IDLE_MS);
    return () => window.clearTimeout(timer);
  }, [enabled, scanning, tick]);

  const refresh = useCallback(() => setTick((value) => value + 1), []);

  const run = useCallback(async (key: string, task: () => Promise<BluetoothState | void>, errorCode: string) => {
    setBusy(key);
    try {
      const next = await task();
      if (next) {
        setState(next);
      } else {
        setTick((value) => value + 1);
      }
      return true;
    } catch (cause) {
      reportError(errorCode, cause);
      return false;
    } finally {
      setBusy(null);
    }
  }, []);

  return { state, busy, run, refresh };
}
