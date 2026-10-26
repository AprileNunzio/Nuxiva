import { useCallback, useEffect, useRef, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { fetchPage } from '../api';
import { FleetAgent, FleetFilters } from '../types';

const DEBOUNCE_MS = 250;

export interface FleetList {
  readonly items: readonly FleetAgent[];
  readonly more: boolean;
  readonly loading: boolean;
  readonly failed: boolean;
  readonly loadMore: () => void;
  readonly reload: () => void;
}

export function useFleetList(filters: FleetFilters): FleetList {
  const [items, setItems] = useState<readonly FleetAgent[]>([]);
  const [cursor, setCursor] = useState('');
  const [more, setMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [tick, setTick] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const filtersKey = JSON.stringify(filters);

  const run = useCallback(
    async (after: string, replace: boolean) => {
      controller.current?.abort();
      const current = new AbortController();
      controller.current = current;
      setLoading(true);
      try {
        const page = await fetchPage(JSON.parse(filtersKey) as FleetFilters, after, current.signal);
        if (current.signal.aborted) {
          return;
        }
        setItems((previous) => (replace ? page.items : [...previous, ...page.items]));
        setCursor(page.next);
        setMore(page.more);
        setFailed(false);
      } catch (cause) {
        if (!current.signal.aborted) {
          setFailed(true);
          reportError('fleet_list_failed', cause);
        }
      } finally {
        if (!current.signal.aborted) {
          setLoading(false);
        }
      }
    },
    [filtersKey],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => void run('', true), DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.current?.abort();
    };
  }, [run, tick]);

  const loadMore = useCallback(() => {
    if (more && !loading) {
      void run(cursor, false);
    }
  }, [more, loading, cursor, run]);
  const reload = useCallback(() => setTick((value) => value + 1), []);
  return { items, more, loading, failed, loadMore, reload };
}
