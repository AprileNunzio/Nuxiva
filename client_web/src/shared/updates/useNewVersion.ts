import { useCallback, useEffect, useRef, useState } from 'react';
import { appRoot, bundleDir, entryOf, isNewer, loadedEntry } from './pageVersion';
import { canAutoReload, nextRecord, pollDelay, readRecord, settled, writeRecord } from './reloadGuard';

const COUNTDOWN_S = 8;
const SNOOZE_MS = 30 * 60 * 1000;
const PRELOAD_TARGET = '/__preload__';

export interface NewVersion {
  readonly available: boolean;
  readonly automatic: boolean;
  readonly seconds: number;
  readonly reload: () => void;
  readonly later: () => void;
}

function reloadFor(target: string): void {
  writeRecord(nextRecord(readRecord(), target, Date.now()));
  window.location.reload();
}

async function servedEntry(loaded: string): Promise<string | null> {
  const response = await fetch(appRoot(window.location.pathname), {
    cache: 'no-store',
    credentials: 'same-origin',
    redirect: 'error',
    headers: { Accept: 'text/html' },
  });
  if (!response.ok || !(response.headers.get('content-type') ?? '').includes('text/html')) {
    return null;
  }
  return entryOf(await response.text(), bundleDir(loaded));
}

export function useNewVersion(): NewVersion {
  const [target, setTarget] = useState<string | null>(null);
  const [automatic, setAutomatic] = useState(false);
  const [seconds, setSeconds] = useState(COUNTDOWN_S);
  const loaded = useRef<string | null>(loadedEntry());
  const snoozedUntil = useRef(0);

  useEffect(() => {
    if (settled(readRecord(), loaded.current)) {
      writeRecord(null);
    }
  }, []);

  const reload = useCallback(() => {
    if (target) {
      reloadFor(target);
    }
  }, [target]);

  const later = useCallback(() => {
    snoozedUntil.current = Date.now() + SNOOZE_MS;
    setTarget(null);
  }, []);

  useEffect(() => {
    const current = loaded.current;
    if (!current || target) {
      return undefined;
    }
    let alive = true;
    let failures = 0;
    let timer = 0;
    const schedule = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => void check(), pollDelay(failures));
    };
    const check = async () => {
      if (!alive || document.hidden || Date.now() < snoozedUntil.current) {
        schedule();
        return;
      }
      let served: string | null = null;
      try {
        served = await servedEntry(current);
        failures = 0;
      } catch {
        failures += 1;
      }
      if (!alive) {
        return;
      }
      if (served && isNewer(current, served)) {
        setAutomatic(canAutoReload(readRecord(), served, Date.now()));
        setTarget(served);
        return;
      }
      schedule();
    };
    const onVisible = () => {
      if (!document.hidden) {
        void check();
      }
    };
    schedule();
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('online', onVisible);
    return () => {
      alive = false;
      window.clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('online', onVisible);
    };
  }, [target]);

  useEffect(() => {
    const onPreloadError = (event: Event) => {
      if (!canAutoReload(readRecord(), PRELOAD_TARGET, Date.now())) {
        return;
      }
      event.preventDefault();
      reloadFor(PRELOAD_TARGET);
    };
    window.addEventListener('vite:preloadError', onPreloadError);
    return () => window.removeEventListener('vite:preloadError', onPreloadError);
  }, []);

  useEffect(() => {
    setSeconds(COUNTDOWN_S);
    if (!target || !automatic) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      setSeconds((value) => Math.max(0, value - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [target, automatic]);

  useEffect(() => {
    if (target && automatic && seconds === 0) {
      reloadFor(target);
    }
  }, [target, automatic, seconds]);

  return { available: target !== null, automatic, seconds, reload, later };
}
