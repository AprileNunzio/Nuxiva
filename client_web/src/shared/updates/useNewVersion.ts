import { useCallback, useEffect, useRef, useState } from 'react';
import { entryOf, isNewer, loadedEntry } from './pageVersion';

const POLL_MS = 20000;
const COUNTDOWN_S = 8;

export interface NewVersion {
  readonly available: boolean;
  readonly seconds: number;
  readonly reload: () => void;
  readonly later: () => void;
}

export function useNewVersion(): NewVersion {
  const [available, setAvailable] = useState(false);
  const [seconds, setSeconds] = useState(COUNTDOWN_S);
  const loaded = useRef<string | null>(loadedEntry());
  const postponed = useRef(false);

  const reload = useCallback(() => window.location.reload(), []);
  const later = useCallback(() => {
    postponed.current = true;
    setAvailable(false);
  }, []);

  useEffect(() => {
    let alive = true;
    const check = async () => {
      if (!alive || available) {
        return;
      }
      try {
        const response = await fetch('/', { cache: 'no-store', headers: { Accept: 'text/html' } });
        if (!response.ok || !(response.headers.get('content-type') ?? '').includes('text/html')) {
          return;
        }
        if (isNewer(loaded.current, entryOf(await response.text())) && alive) {
          setAvailable(true);
        }
      } catch {
        return;
      }
    };
    const onVisible = () => {
      if (!document.hidden) {
        void check();
      }
    };
    const onPreloadError = (event: Event) => {
      event.preventDefault();
      window.location.reload();
    };
    const timer = window.setInterval(() => void check(), POLL_MS);
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('online', onVisible);
    window.addEventListener('vite:preloadError', onPreloadError);
    return () => {
      alive = false;
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('online', onVisible);
      window.removeEventListener('vite:preloadError', onPreloadError);
    };
  }, [available]);

  useEffect(() => {
    if (!available) {
      setSeconds(COUNTDOWN_S);
      return undefined;
    }
    const timer = window.setInterval(() => {
      setSeconds((value) => {
        if (value <= 1) {
          window.location.reload();
        }
        return Math.max(0, value - 1);
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [available]);

  return { available, seconds, reload, later };
}
