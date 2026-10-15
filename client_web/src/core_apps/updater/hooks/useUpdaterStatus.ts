import { useCallback, useEffect, useRef, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { fetchStatus } from '../api';
import { UpdaterStatus } from '../types';

const IDLE_INTERVAL_MS = 10000;
const ACTIVE_INTERVAL_MS = 2000;

export interface UpdaterState {
  readonly status: UpdaterStatus | null;
  readonly unreachable: boolean;
  readonly applying: boolean;
  readonly setStatus: (status: UpdaterStatus) => void;
  readonly markApplying: (fromRev: string | null) => void;
  readonly refresh: () => void;
}

export function useUpdaterStatus(): UpdaterState {
  const [status, setStatus] = useState<UpdaterStatus | null>(null);
  const [unreachable, setUnreachable] = useState(false);
  const [applyingFrom, setApplyingFrom] = useState<string | null | undefined>(undefined);
  const [tick, setTick] = useState(0);
  const timer = useRef<number | null>(null);
  const applying = applyingFrom !== undefined;

  useEffect(() => {
    const controller = new AbortController();
    fetchStatus(controller.signal)
      .then((next) => {
        setStatus(next);
        setUnreachable(false);
        if (applying && next.local_rev && next.local_rev !== applyingFrom && next.phase !== 'UPDATING') {
          setApplyingFrom(undefined);
        }
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setUnreachable(true);
        if (!applying) {
          reportError('updater_unreachable', cause);
        }
      });
    const busy = applying || status?.phase === 'UPDATING';
    timer.current = window.setTimeout(() => setTick((value) => value + 1), busy ? ACTIVE_INTERVAL_MS : IDLE_INTERVAL_MS);
    return () => {
      controller.abort();
      if (timer.current !== null) {
        window.clearTimeout(timer.current);
      }
    };
  }, [tick, applying]);

  const refresh = useCallback(() => setTick((value) => value + 1), []);
  const markApplying = useCallback((fromRev: string | null) => setApplyingFrom(fromRev), []);

  return { status, unreachable, applying, setStatus, markApplying, refresh };
}
