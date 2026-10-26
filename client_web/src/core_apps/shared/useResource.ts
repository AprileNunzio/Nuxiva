import { useCallback, useEffect, useRef, useState } from 'react';
import { reportError } from '../../shared/errors/errorBus';
import { getJson } from './http';
import { useWindowToolbar } from '../../app_shell/window_manager/WindowContext';

export interface Resource<T> {
  readonly dataUrl: string | null;
  readonly data: T | null;
  readonly error: boolean;
  readonly loading: boolean;
  readonly reload: () => void;
}

export function useResource<T>(url: string, intervalMs = 0): Resource<T> {
  const [data, setData] = useState<T | null>(null);
  const [dataUrl, setDataUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    let inFlight = false;
    setLoading(true);
    const load = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const next = await getJson<T>(url, controller.signal);
        if (alive.current && !controller.signal.aborted) {
          setData(next);
          setDataUrl(url);
          setError(false);
        }
      } catch (cause) {
        if (controller.signal.aborted) {
          return;
        }
        if (alive.current && !controller.signal.aborted) {
          setError(true);
        }
        reportError('core_app_load_failed', cause);
      } finally {
        inFlight = false;
        if (alive.current && !controller.signal.aborted) {
          setLoading(false);
        }
      }
    };
    void load();
    const timer = intervalMs > 0 ? window.setInterval(() => !document.hidden && void load(), intervalMs) : 0;
    return () => {
      alive.current = false;
      controller.abort();
      if (timer) {
        window.clearInterval(timer);
      }
    };
  }, [url, intervalMs, tick]);

  const reload = useCallback(() => setTick((value) => value + 1), []);
  useWindowToolbar(id=>{if(id==='refresh')reload();});
  return { data, dataUrl, error, loading, reload };
}

export function useAction(onDone?: () => void) {
  const [busy, setBusy] = useState(false);
  const run = useCallback(
    async <R,>(task: () => Promise<R>, code = 'core_app_action_failed'): Promise<R | null> => {
      setBusy(true);
      try {
        const result = await task();
        onDone?.();
        return result;
      } catch (cause) {
        reportError(code, cause);
        return null;
      } finally {
        setBusy(false);
      }
    },
    [onDone],
  );
  return { busy, run };
}
