import { useCallback, useEffect, useRef, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';

export interface ActionHandle {
  readonly busy: string | null;
  readonly run: <T>(key: string, task: () => Promise<T>, errorCode: string) => Promise<T | undefined>;
}

export function useAction(onDone?: () => void): ActionHandle {
  const [busy, setBusy] = useState<string | null>(null);
  const run = useCallback(
    async <T,>(key: string, task: () => Promise<T>, errorCode: string): Promise<T | undefined> => {
      setBusy(key);
      try {
        const result = await task();
        onDone?.();
        return result;
      } catch (cause) {
        reportError(errorCode, cause);
        return undefined;
      } finally {
        setBusy(null);
      }
    },
    [onDone],
  );
  return { busy, run };
}

export function usePolled<T>(load: (signal: AbortSignal) => Promise<T>, errorCode: string, enabled: boolean, intervalMs = 0) {
  const [data, setData] = useState<T | null>(null);
  const [tick, setTick] = useState(0);
  const refresh = useCallback(() => setTick((value) => value + 1), []);
  usePollEffect(load, errorCode, enabled, intervalMs, tick, setData, refresh);
  return { data, refresh, setData };
}

function usePollEffect<T>(
  load: (signal: AbortSignal) => Promise<T>,
  errorCode: string,
  enabled: boolean,
  intervalMs: number,
  tick: number,
  setData: (value: T) => void,
  refresh: () => void,
) {
  const failures = useRef(0);
  const loader = useRef(load);
  loader.current = load;
  useEffect(() => {
    if (!enabled) {
      return;
    }
    const controller = new AbortController();
    loader
      .current(controller.signal)
      .then((value) => {
        failures.current = 0;
        setData(value);
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted && failures.current++ === 0) {
          reportError(errorCode, cause);
        }
      });
    const timer = intervalMs > 0 ? window.setTimeout(refresh, intervalMs) : 0;
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [enabled, intervalMs, tick, errorCode, setData, refresh]);
}
