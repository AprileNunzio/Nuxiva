import { useCallback, useEffect, useRef, useState } from 'react';
import { NodeModuleError } from '../../node_apps/shared/data/http';
import { addItem, createDiorama, deleteItem, fetchCatalog, fetchList, fetchOne, refineDiorama, removeDiorama, saveBase, saveLook, updateItem } from './api';
import type { Base, Catalog, Diorama, Item, Look, Summary } from './types';

const POLL_BUILDING_MS = 900;
const POLL_IDLE_MS = 6000;

export interface DioramaState {
  readonly catalog: Catalog | null;
  readonly library: readonly Summary[];
  readonly current: Diorama | null;
  readonly loadedOnce: boolean;
  readonly busy: boolean;
  readonly error: string;
  readonly building: boolean;
  open(id: string): void;
  close(): void;
  create(prompt: string): Promise<void>;
  refine(instruction: string): Promise<void>;
  remove(id: string): Promise<void>;
  patchLook(look: Partial<Look>): Promise<void>;
  patchBase(base: Partial<Base>): Promise<void>;
  add(kind: string, near?: Item): Promise<string>;
  patchItem(id: string, patch: Partial<Item>): Promise<void>;
  dropItem(id: string): Promise<void>;
}

const codeOf = (cause: unknown): string => (cause instanceof NodeModuleError ? cause.code : 'request_failed');

export function useDiorama(): DioramaState {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [library, setLibrary] = useState<readonly Summary[]>([]);
  const [current, setCurrent] = useState<Diorama | null>(null);
  const [loadedOnce, setLoadedOnce] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [activeId, setActiveId] = useState('');
  const alive = useRef(true);

  const guard = useCallback(async <T,>(work: () => Promise<T>, fallback: T): Promise<T> => {
    setBusy(true);
    setError('');
    try {
      return await work();
    } catch (cause) {
      if (alive.current) setError(codeOf(cause));
      return fallback;
    } finally {
      if (alive.current) setBusy(false);
    }
  }, []);

  const refreshLibrary = useCallback(async () => {
    try {
      const rows = await fetchList();
      if (alive.current) setLibrary(rows);
    } catch (cause) {
      if (alive.current) setError(codeOf(cause));
    }
  }, []);

  useEffect(() => {
    alive.current = true;
    void fetchCatalog().then((value) => alive.current && setCatalog(value)).catch((cause) => alive.current && setError(codeOf(cause)));
    void refreshLibrary();
    return () => {
      alive.current = false;
    };
  }, [refreshLibrary]);

  const building = current?.job.state === 'building';

  useEffect(() => {
    if (!activeId) return undefined;
    const controller = new AbortController();
    const pull = async () => {
      try {
        const next = await fetchOne(activeId, controller.signal);
        if (alive.current && !controller.signal.aborted) {
          setCurrent((prev) => (prev && prev.id === next.id && prev.revision === next.revision && prev.job.state === next.job.state && prev.job.stage === next.job.stage ? prev : next));
          setLoadedOnce(true);
        }
      } catch (cause) {
        if (!controller.signal.aborted && alive.current) setError(codeOf(cause));
      }
    };
    void pull();
    const timer = window.setInterval(pull, building ? POLL_BUILDING_MS : POLL_IDLE_MS);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [activeId, building]);

  useEffect(() => {
    if (current?.job.state === 'done') void refreshLibrary();
  }, [current?.job.state, current?.id, refreshLibrary]);

  const open = useCallback((id: string) => {
    setLoadedOnce(false);
    setCurrent(null);
    setActiveId(id);
  }, []);

  const close = useCallback(() => {
    setActiveId('');
    setCurrent(null);
    setLoadedOnce(false);
  }, []);

  const create = useCallback(async (prompt: string) => {
    const id = await guard(() => createDiorama(prompt), '');
    if (id) open(id);
  }, [guard, open]);

  const reload = useCallback(async (id: string) => {
    const next = await fetchOne(id);
    if (alive.current) setCurrent(next);
  }, []);

  const mutate = useCallback(async (work: (id: string) => Promise<unknown>) => {
    if (!activeId) return;
    await guard(async () => {
      await work(activeId);
      await reload(activeId);
    }, undefined);
  }, [activeId, guard, reload]);

  const refine = useCallback((instruction: string) => mutate((id) => refineDiorama(id, instruction)), [mutate]);
  const patchLook = useCallback((look: Partial<Look>) => mutate((id) => saveLook(id, look)), [mutate]);
  const patchBase = useCallback((base: Partial<Base>) => mutate((id) => saveBase(id, base)), [mutate]);
  const patchItem = useCallback((itemId: string, patch: Partial<Item>) => mutate((id) => updateItem(id, itemId, patch)), [mutate]);
  const dropItem = useCallback((itemId: string) => mutate((id) => deleteItem(id, itemId)), [mutate]);

  const add = useCallback(async (kind: string, near?: Item): Promise<string> => {
    if (!activeId) return '';
    return guard(async () => {
      const made = await addItem(activeId, { kind, x: (near?.x ?? 0) + 1, z: (near?.z ?? 0) + 1, rot: near?.rot ?? 0 });
      await reload(activeId);
      return made.id;
    }, '');
  }, [activeId, guard, reload]);

  const remove = useCallback(async (id: string) => {
    await guard(() => removeDiorama(id), undefined);
    if (id === activeId) close();
    await refreshLibrary();
  }, [activeId, close, guard, refreshLibrary]);

  return { catalog, library, current, loadedOnce, busy, error, building, open, close, create, refine, remove, patchLook, patchBase, add, patchItem, dropItem };
}
