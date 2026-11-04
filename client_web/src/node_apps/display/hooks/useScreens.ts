import { useEffect, useRef, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { ScreensState, fetchScreens } from '../data/displayApi';

const POLL_MS = 5000;

export function useScreens(enabled: boolean): ScreensState | null {
  const [state, setState] = useState<ScreensState | null>(null);
  const [tick, setTick] = useState(0);
  const failures = useRef(0);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const controller = new AbortController();
    fetchScreens(controller.signal)
      .then((next) => {
        failures.current = 0;
        setState(next);
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted && failures.current++ === 0) {
          reportError('node_display_unavailable', cause);
        }
      });
    const timer = window.setTimeout(() => setTick((value) => value + 1), POLL_MS);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [enabled, tick]);

  return state;
}
