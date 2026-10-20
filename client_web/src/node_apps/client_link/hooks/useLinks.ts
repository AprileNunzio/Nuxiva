import { useCallback, useEffect, useRef, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { LinkOverview, fetchLinks } from '../data/linkApi';

const POLL_MS = 4000;

export interface LinksHandle {
  readonly overview: LinkOverview | null;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<void>, errorCode: string) => Promise<boolean>;
}

export function useLinks(enabled: boolean): LinksHandle {
  const [overview, setOverview] = useState<LinkOverview | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const failures = useRef(0);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const controller = new AbortController();
    fetchLinks(controller.signal)
      .then((next) => {
        failures.current = 0;
        setOverview(next);
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted && failures.current++ === 0) {
          reportError('node_links_unavailable', cause);
        }
      });
    const timer = window.setTimeout(() => setTick((value) => value + 1), POLL_MS);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [enabled, tick]);

  const run = useCallback(async (key: string, task: () => Promise<void>, errorCode: string) => {
    setBusy(key);
    try {
      await task();
      setTick((value) => value + 1);
      return true;
    } catch (cause) {
      reportError(errorCode, cause);
      return false;
    } finally {
      setBusy(null);
    }
  }, []);

  return { overview, busy, run };
}

export function useNow(intervalMs = 1000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), intervalMs);
    return () => window.clearInterval(timer);
  }, [intervalMs]);
  return now;
}
