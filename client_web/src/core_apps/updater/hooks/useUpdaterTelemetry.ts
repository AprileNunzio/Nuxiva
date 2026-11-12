import { useEffect, useState } from 'react';
import { fetchTelemetry } from '../api';
import type { UpdaterTelemetry } from '../types';

const IDLE_MS = 10000;
const BUSY_MS = 1500;

export function useUpdaterTelemetry(busy: boolean, refreshKey: string): UpdaterTelemetry | null {
  const [telemetry, setTelemetry] = useState<UpdaterTelemetry | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchTelemetry(controller.signal)
      .then(setTelemetry)
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) console.warn('updater telemetry unavailable', cause);
      });
    const timer = window.setTimeout(() => setTick((value) => value + 1), busy ? BUSY_MS : IDLE_MS);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [tick, busy, refreshKey]);

  return telemetry;
}
