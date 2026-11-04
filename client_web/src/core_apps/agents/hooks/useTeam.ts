import { useCallback, useEffect, useRef, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { TeamOverview, fetchTeam } from '../data/teamApi';

const POLL_MS = 4000;

export interface TeamHandle {
  readonly team: TeamOverview | null;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, errorCode: string) => Promise<boolean>;
  readonly refresh: () => void;
}

export function useTeam(): TeamHandle {
  const [team, setTeam] = useState<TeamOverview | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const failures = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchTeam(controller.signal)
      .then((next) => {
        failures.current = 0;
        setTeam(next);
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted && failures.current++ === 0) {
          reportError('team_unavailable', cause);
        }
      });
    const timer = window.setTimeout(() => setTick((value) => value + 1), document.hidden ? POLL_MS * 4 : POLL_MS);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [tick]);

  const refresh = useCallback(() => setTick((value) => value + 1), []);

  const run = useCallback(async (key: string, task: () => Promise<unknown>, errorCode: string) => {
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

  return { team, busy, run, refresh };
}
