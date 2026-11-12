import React, { useEffect, useState } from 'react';
import { fetchRepairTeam, reportRepairIssue, runRepairTeam } from '../api';
import type { RepairTeamState } from '../types';

interface Props {
  readonly sessionId?: string;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

function evidenceUrl(raw: string): string | undefined {
  try {
    const url = new URL(raw);
    return ['https:', 'http:'].includes(url.protocol) ? url.href : undefined;
  } catch { return undefined; }
}

export const RepairTeamPanel: React.FC<Props> = ({ sessionId, t }) => {
  const [team, setTeam] = useState<RepairTeamState | null>(null);
  const [title, setTitle] = useState('');
  const [severity, setSeverity] = useState<'low' | 'medium' | 'high'>('medium');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(false);
  const [revision, setRevision] = useState(0);
  const summaryText = (summary: string) => /^team_[a-z_]+$/.test(summary) ? t(summary) : summary;

  useEffect(() => {
    setTeam(null);
    setError(false);
    if (!sessionId) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const next = await fetchRepairTeam(sessionId);
        if (!stopped) { setTeam(next); setError(false); }
      } catch { if (!stopped) setError(true); }
      if (!stopped) timer = setTimeout(() => void refresh(), 4000);
    };
    void refresh();
    return () => { stopped = true; clearTimeout(timer); };
  }, [sessionId, revision]);

  async function act(action: () => Promise<void>) {
    setPending(true);
    setError(false);
    try { await action(); setRevision((value) => value + 1); }
    catch { setError(true); }
    finally { setPending(false); }
  }

  return <section className="flex flex-col gap-3 text-xs">
    <p className="leading-relaxed text-slate-400">{t('team_explanation')}</p>
    {!sessionId && <p className="text-slate-400">{t('team_start_session')}</p>}
    <button type="button" disabled={!sessionId || pending || Boolean(team?.running)}
      onClick={() => void act(() => runRepairTeam(sessionId!))}
      className="rounded-lg bg-cyan-700 px-3 py-2 font-semibold text-white disabled:opacity-40">
      {team?.running ? t('team_running') : t('team_run')}
    </button>
    {error && <p role="alert" className="text-amber-300">{t('team_error')}</p>}
    <div className="flex flex-col gap-2" aria-live="polite">
      {team?.workers.map((worker) => <div key={worker.id} className="rounded-xl border border-slate-800 bg-slate-900 p-3">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-semibold text-slate-100">{t(`team_worker_${worker.id}`)}</h3>
          <span className={worker.status === 'blocked' || worker.status === 'failed' ? 'text-amber-300' : 'text-cyan-300'}>{t(`team_status_${worker.status}`)}</span>
        </div>
        {worker.summary && <p className="mt-1 whitespace-pre-wrap leading-relaxed text-slate-300">{summaryText(worker.summary)}</p>}
      </div>)}
    </div>
    <form className="flex flex-col gap-2 rounded-xl border border-slate-800 p-3" onSubmit={(event) => {
      event.preventDefault();
      if (sessionId && title.trim()) void act(async () => {
        await reportRepairIssue(sessionId, title, severity);
        setTitle('');
      });
    }}>
      <h3 className="font-semibold">{t('team_report_issue')}</h3>
      <textarea value={title} onChange={(event) => setTitle(event.target.value)} maxLength={1000} rows={3}
        aria-label={t('team_issue_description')} placeholder={t('team_issue_description')}
        className="rounded-lg border border-slate-700 bg-slate-950 p-2 text-slate-100" />
      <div className="flex items-center gap-2">
        <select value={severity} aria-label={t('team_severity')} onChange={(event) => setSeverity(event.target.value as typeof severity)}
          className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 p-2">
          {(['low', 'medium', 'high'] as const).map((value) => <option key={value} value={value}>{t(`team_severity_${value}`)}</option>)}
        </select>
        <button type="submit" disabled={!sessionId || !title.trim() || pending}
          className="rounded-lg bg-slate-700 px-3 py-2 disabled:opacity-40">{t('team_issue_save')}</button>
      </div>
    </form>
    <h3 className="font-semibold text-slate-100">{t('team_issues')}</h3>
    {!team?.issues.length && <p className="text-slate-400">{t('team_issues_empty')}</p>}
    {team?.issues.map((issue) => <article key={issue.id} className="rounded-lg border border-slate-800 p-2">
      <p className="whitespace-pre-wrap text-slate-200">{issue.title}</p>
      <p className="mt-1 text-slate-400">{t(`team_severity_${issue.severity}`)} · {t(`team_issue_status_${issue.status}`)}</p>
    </article>)}
    <h3 className="font-semibold text-slate-100">{t('team_task_log')}</h3>
    <p className="leading-relaxed text-slate-400">{t('team_sources_unverified')}</p>
    {!team?.tasks.length && <p className="text-slate-400">{t('team_tasks_empty')}</p>}
    {team?.tasks.slice().reverse().map((task) => <article key={task.id} className="rounded-lg border border-slate-800 p-2">
      <p className="font-medium text-slate-200">{t(`team_worker_${task.worker_id}`)} · {t(`team_status_${task.status}`)}</p>
      <p className="mt-1 whitespace-pre-wrap leading-relaxed text-slate-300">{summaryText(task.summary)}</p>
      {task.evidence.map((evidence, index) => {
        const url = evidenceUrl(evidence.url);
        return url ? <a key={index} href={url} target="_blank" rel="noopener noreferrer"
          className="mt-1 block break-words text-cyan-300 underline">{evidence.title || t('team_source')}</a> : null;
      })}
    </article>)}
  </section>;
};
