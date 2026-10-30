import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { ActionHandle, useAction, usePolled } from '../../../node_apps/shared/hooks/useAction';
import { fetchOverview, fetchPool, fetchRevision } from './brainApi';
import { newSourceId, publishBrainChange, subscribeBrainChanges } from './liveSync';
import { BrainOverview, BrainRef } from './types';

const REVISION_POLL_MS = 5000;

export interface BrainStore {
  readonly overview: BrainOverview | null;
  readonly pool: readonly BrainRef[];
  readonly action: ActionHandle;
  readonly version: number;
  readonly refresh: () => void;
  readonly commit: (key: string, errorCode: string, task: () => Promise<BrainOverview>) => Promise<boolean>;
  readonly run: <T>(key: string, errorCode: string, task: () => Promise<T>) => Promise<T | undefined>;
}

export const BrainStoreContext = createContext<BrainStore | null>(null);

export function useBrain(): BrainStore {
  const store = useContext(BrainStoreContext);
  if (!store) {
    throw new Error('brain_store_missing');
  }
  return store;
}

export function useBrainStore(enabled: boolean): BrainStore {
  const source = useRef(newSourceId()).current;
  const overview = usePolled(fetchOverview, 'brain_overview_unavailable', enabled, 30000);
  const pool = usePolled(fetchPool, 'brain_pool_unavailable', enabled, 60000);
  const revision = usePolled(fetchRevision, 'brain_revision_unavailable', enabled, REVISION_POLL_MS);
  const action = useAction();
  const [version, setVersion] = useState(0);
  const seen = useRef('');
  const { refresh: refreshOverview, setData: setOverview } = overview;
  const { refresh: refreshPool } = pool;

  const refresh = useCallback(() => {
    refreshOverview();
    refreshPool();
    setVersion((v) => v + 1);
  }, [refreshOverview, refreshPool]);

  useEffect(() => subscribeBrainChanges(source, refresh), [source, refresh]);

  useEffect(() => {
    const current = revision.data;
    if (!current) {
      return;
    }
    if (seen.current && seen.current !== current) {
      refresh();
    }
    seen.current = current;
  }, [revision.data, refresh]);

  const run = useCallback(
    async <T,>(key: string, errorCode: string, task: () => Promise<T>): Promise<T | undefined> => {
      const result = await action.run(key, task, errorCode);
      if (result !== undefined) {
        publishBrainChange(source);
        refresh();
      }
      return result;
    },
    [action, refresh, source],
  );

  const commit = useCallback(
    async (key: string, errorCode: string, task: () => Promise<BrainOverview>): Promise<boolean> => {
      const result = await run(key, errorCode, task);
      if (result) {
        setOverview(result);
      }
      return result !== undefined;
    },
    [run, setOverview],
  );

  return useMemo(
    () => ({ overview: overview.data, pool: pool.data ?? [], action, version, refresh, commit, run }),
    [overview.data, pool.data, action, version, refresh, commit, run],
  );
}
