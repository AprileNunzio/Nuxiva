import { useCallback, useEffect, useRef, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { BoardView, fetchBoard } from '../data/boardApi';

const VISIBLE_MS = 900;
const HIDDEN_MS = 5000;

export interface BoardHandle {
  readonly view: BoardView | null;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, errorCode: string) => Promise<boolean>;
  readonly refresh: () => void;
}

export function useBoard(enabled: boolean): BoardHandle {
  const [view, setView] = useState<BoardView | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const rev = useRef(0);
  const failures = useRef(0);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const controller = new AbortController();
    fetchBoard(rev.current, controller.signal)
      .then((next) => {
        failures.current = 0;
        if (next) {
          rev.current = next.rev;
          setView(next);
        }
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted && failures.current++ === 0) {
          reportError('node_board_unavailable', cause);
        }
      });
    const timer = window.setTimeout(() => setTick((value) => value + 1), document.hidden ? HIDDEN_MS : VISIBLE_MS);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [enabled, tick]);

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

  return { view, busy, run, refresh };
}
