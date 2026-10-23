import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Player } from './engine/player';
import { renderMix } from './engine/render';
import {
  chatWithAgent, createProject, exportMix, fetchAsset, listProjects, loadCatalog, loadProject, removeProject, saveProject,
} from './api';
import type { Catalog, ChatTurn, Project, Summary } from './types';

const SAVE_DELAY = 700;
const POLL_MS = 1500;

export type Mutator = (project: Project) => Project;

const assetsOf = (project: Project) =>
  project.tracks.flatMap((t) => t.clips.flatMap((c) => (c.vocal?.asset ? [c.vocal.asset] : [])));

export function useStudio() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [chat, setChat] = useState<ChatTurn[]>([]);
  const [published, setPublished] = useState('');
  const player = useRef<Player | null>(null);
  const saveTimer = useRef(0);
  const latest = useRef<Project | null>(null);

  const refreshList = useCallback(async () => {
    try {
      setSummaries(await listProjects());
    } catch {
      setSummaries([]);
    }
  }, []);

  useEffect(() => {
    const abort = new AbortController();
    loadCatalog(abort.signal).then(setCatalog).catch(() => setError('catalog'));
    void refreshList();
    return () => abort.abort();
  }, [refreshList]);

  useEffect(() => () => {
    window.clearTimeout(saveTimer.current);
    player.current?.dispose();
  }, []);

  const adopt = useCallback(
    async (next: Project) => {
      latest.current = next;
      setProject(next);
      if (!catalog) return;
      if (!player.current) player.current = new Player(catalog, next);
      player.current.setProject(next);
      const missing = [...new Set(assetsOf(next))].filter((name) => !player.current?.hasBuffer(name));
      await Promise.all(
        missing.map(async (name) => {
          try {
            await player.current?.decode(name, await fetchAsset(next.id, name));
          } catch {
            setError('asset');
          }
        }),
      );
    },
    [catalog],
  );

  const open = useCallback(
    async (id: string) => {
      setError('');
      setChat([]);
      setPublished('');
      player.current?.stop();
      player.current?.dispose();
      player.current = null;
      try {
        await adopt(await loadProject(id));
      } catch {
        setError('open');
      }
    },
    [adopt],
  );

  const create = useCallback(
    async (prompt: string) => {
      setBusy(true);
      setError('');
      try {
        const created = await createProject(prompt);
        player.current?.dispose();
        player.current = null;
        setChat([]);
        setPublished('');
        await adopt(created);
        await refreshList();
      } catch {
        setError('create');
      } finally {
        setBusy(false);
      }
    },
    [adopt, refreshList],
  );

  const building = project?.job.state === 'building';

  useEffect(() => {
    if (!project || !building) return;
    const timer = window.setInterval(async () => {
      try {
        await adopt(await loadProject(project.id));
        await refreshList();
      } catch {
        setError('open');
      }
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [project?.id, building, adopt, refreshList]);

  const flush = useCallback(async () => {
    const current = latest.current;
    if (!current || current.job.state === 'building') return;
    try {
      const saved = await saveProject(current);
      latest.current = { ...latest.current!, revision: saved.revision };
      setProject((p) => (p ? { ...p, revision: saved.revision } : p));
    } catch {
      setError('save');
    }
  }, []);

  const edit = useCallback(
    (mutate: Mutator) => {
      const current = latest.current;
      if (!current || current.job.state === 'building') return;
      const next = mutate(current);
      latest.current = next;
      setProject(next);
      player.current?.setProject(next);
      window.clearTimeout(saveTimer.current);
      saveTimer.current = window.setTimeout(() => void flush(), SAVE_DELAY);
    },
    [flush],
  );

  const replace = useCallback(
    async (next: Project) => {
      window.clearTimeout(saveTimer.current);
      await adopt(next);
      await refreshList();
    },
    [adopt, refreshList],
  );

  const remove = useCallback(
    async (id: string) => {
      await removeProject(id);
      if (project?.id === id) {
        player.current?.dispose();
        player.current = null;
        latest.current = null;
        setProject(null);
      }
      await refreshList();
    },
    [project?.id, refreshList],
  );

  const talk = useCallback(
    async (message: string) => {
      if (!project) return;
      const history = chat;
      setChat([...history, { who: 'you', text: message }]);
      setBusy(true);
      try {
        window.clearTimeout(saveTimer.current);
        await flush();
        const answer = await chatWithAgent(project.id, message, history);
        setChat((turns) => [...turns, { who: 'ai', text: answer.reply }]);
        await adopt(answer.project);
        await refreshList();
      } catch {
        setChat((turns) => [...turns, { who: 'ai', text: '' }]);
        setError('chat');
      } finally {
        setBusy(false);
      }
    },
    [project, chat, flush, adopt, refreshList],
  );

  const publish = useCallback(async () => {
    if (!project || !catalog || !player.current) return;
    setBusy(true);
    setError('');
    try {
      await flush();
      const wav = await renderMix(latest.current ?? project, catalog, player.current.audioBuffers);
      const result = await exportMix(project.id, wav);
      setPublished(typeof result.folder === 'string' ? result.folder : '');
    } catch {
      setError('export');
    } finally {
      setBusy(false);
    }
  }, [project, catalog, flush]);

  return useMemo(
    () => ({
      catalog, summaries, project, error, busy, chat, published, building, player,
      open, create, edit, replace, remove, talk, publish, setError, refreshList,
    }),
    [catalog, summaries, project, error, busy, chat, published, building, open, create, edit, replace, remove, talk, publish, refreshList],
  );
}

export type Studio = ReturnType<typeof useStudio>;
