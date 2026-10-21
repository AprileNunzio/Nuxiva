import React, { useEffect, useState } from 'react';
import { fetchRepairProjectFolders } from '../api';
import type { RepairProjectFolder } from '../types';

export function ProjectArchivePanel({ t, busy, activeProjectId, onResume, onClose }: {
  t: (key: string) => string; busy: boolean; activeProjectId: string;
  onResume: (id: string) => Promise<void>; onClose: (id: string) => Promise<void>;
}) {
  const [folders, setFolders] = useState<RepairProjectFolder[]>([]);
  const [error, setError] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try { const list = await fetchRepairProjectFolders(true); if (!stopped) { setFolders(list); setError(false); } }
      catch { if (!stopped) setError(true); }
      if (!stopped) timer = setTimeout(() => void refresh(), 5000);
    };
    void refresh();
    return () => { stopped = true; clearTimeout(timer); };
  }, [revision, activeProjectId]);
  return <details className="rounded-xl border border-slate-800 bg-slate-900 p-3 text-xs">
    <summary className="cursor-pointer font-semibold">{t('archive_projects')}</summary>
    {error && <p role="alert">{t('archive_failed')}</p>}
    {!folders.length && <p className="py-2 text-slate-400">{t('archive_empty')}</p>}
    <div className="flex max-h-44 flex-col gap-2 overflow-auto pt-2">{folders.map((folder) => {
      const closed = ['COMPLETED', 'ARCHIVED', 'CLOSED'].includes(folder.status.toUpperCase());
      return <div key={folder.project_id} className="flex flex-wrap items-center gap-2 rounded-lg bg-slate-950 p-2">
        <span className="min-w-32 flex-1">{folder.name}</span>
        <span className="text-slate-400">{t(closed ? 'archive_closed' : 'archive_open')} · {new Date(folder.updated_at * 1000).toLocaleString()}</span>
        {!closed && <>
          <button disabled={busy || !folder.latest_session_id} onClick={() => void onResume(folder.project_id)} className="rounded bg-cyan-800 px-2 py-1 disabled:opacity-40">{t('archive_resume')}</button>
          <button disabled={busy} onClick={() => void onClose(folder.project_id).then(() => setRevision((v) => v + 1)).catch(() => setError(true))} className="rounded border border-slate-700 px-2 py-1 disabled:opacity-40">{t('archive_close')}</button>
        </>}
      </div>;
    })}</div>
  </details>;
}
