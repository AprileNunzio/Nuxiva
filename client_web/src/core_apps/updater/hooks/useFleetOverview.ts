import { useCallback, useEffect, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { fetchOverview } from '../api';
import type { FleetOverview } from '../types';

const REFRESH_MS = 10000;

export interface FleetState {
  readonly overview: FleetOverview | null;
  readonly unreachable: boolean;
  readonly refresh: () => void;
}

export function useFleetOverview(): FleetState {
  const [overview, setOverview] = useState<FleetOverview | null>(null);
  const [unreachable, setUnreachable] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchOverview(controller.signal)
      .then((next) => {
        setOverview(next);
        setUnreachable(false);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setUnreachable(true);
        reportError('updater_overview_unreachable', cause);
      });
    const timer = window.setTimeout(() => setTick((value) => value + 1), REFRESH_MS);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [tick]);

  const refresh = useCallback(() => setTick((value) => value + 1), []);
  return { overview, unreachable, refresh };
}
