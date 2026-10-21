import { useCallback, useEffect, useRef, useState } from 'react';
import { reportError } from '../../../../shared/errors/errorBus';
import { ExpertsOverview, fetchExperts, fetchLive } from '../data/expertsApi';
import { LiveSnapshot, parseLive } from '../data/live';

const POLL_MS = 4000;
const LIVE_MS: Record<string, number> = { debian: 5000, football: 30000, activity: 3000 };

function usePolling<T>(load: (signal: AbortSignal) => Promise<T>, every: number, errorCode: string, key: string) {
  const [value, setValue] = useState<T | null>(null);
  const [tick, setTick] = useState(0);
  const failures = useRef(0);

  useEffect(() => {
    setValue(null);
    failures.current = 0;
  }, [key]);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal)
      .then((next) => {
        failures.current = 0;
        setValue(next);
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted && failures.current++ === 0) {
          reportError(errorCode, cause);
        }
      });
    const timer = window.setTimeout(() => setTick((n) => n + 1), document.hidden ? every * 4 : every);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [tick, key, every, errorCode, load]);

  const refresh = useCallback(() => setTick((n) => n + 1), []);
  return { value, refresh };
}

export interface ExpertsHandle {
  readonly overview: ExpertsOverview | null;
  readonly busy: string | null;
  readonly run: <T>(key: string, task: () => Promise<T>, errorCode: string) => Promise<T | null>;
  readonly refresh: () => void;
}

export function useExperts(): ExpertsHandle {
  const { value, refresh } = usePolling(fetchExperts, POLL_MS, 'experts_unavailable', 'experts');
  const [busy, setBusy] = useState<string | null>(null);
  const run = useCallback(
    async <T,>(key: string, task: () => Promise<T>, errorCode: string): Promise<T | null> => {
      setBusy(key);
      try {
        const result = await task();
        refresh();
        return result;
      } catch (cause) {
        reportError(errorCode, cause);
        return null;
      } finally {
        setBusy(null);
      }
    },
    [refresh],
  );
  return { overview: value, busy, run, refresh };
}

export function useLive(id: string, kind: string): LiveSnapshot | null {
  const load = useCallback(async (signal: AbortSignal) => parseLive(await fetchLive(id, signal)), [id]);
  return usePolling(load, LIVE_MS[kind] ?? POLL_MS, 'expert_live_failed', `${id}:${kind}`).value;
}
