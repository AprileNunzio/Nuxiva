import React, { useCallback, useEffect, useRef, useState } from 'react';
import { CheckCircle2, ChevronDown, ChevronUp, Loader2, Play, MessageCircle, ExternalLink, X, AlertTriangle } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { resolveApp } from '../window_manager/registry';
import { windowStore } from '../window_manager/WindowStore';
import { answerTask, cancelTask, loadTasks, type TaskRow, type TaskSnapshot } from './taskApi';

const FAST = 2000;
const SLOW = 9000;
const RECENT_MS = 6 * 3600 * 1000;

const ACTION_ICON: Record<string, React.ReactNode> = {
  listen: <Play size={13} />,
  open: <ExternalLink size={13} />,
  talk: <MessageCircle size={13} />,
};

const Bar: React.FC<{ readonly value: number }> = ({ value }) => (
  <div className="h-1.5 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value * 100)}>
    <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all duration-500" style={{ width: `${Math.round(value * 100)}%` }} />
  </div>
);

export const TaskTray: React.FC = () => {
  const { t } = useScopedI18n('app_shell/tasks');
  const [data, setData] = useState<TaskSnapshot | null>(null);
  const [open, setOpen] = useState(false);
  const [dismissed, setDismissed] = useState<ReadonlySet<string>>(new Set());
  const known = useRef<ReadonlySet<string>>(new Set());

  const refresh = useCallback(async () => {
    try {
      const next = await loadTasks();
      setData(next);
      const fresh = next.tasks.filter((x) => x.state === 'done' && x.offer && !x.answered && !known.current.has(x.id));
      if (fresh.length) {
        known.current = new Set([...known.current, ...fresh.map((x) => x.id)]);
        setOpen(true);
      }
    } catch {
      setData(null);
    }
  }, []);

  useEffect(() => {
    let timer = 0;
    let alive = true;
    const loop = async () => {
      await refresh();
      if (alive) timer = window.setTimeout(loop, document.hidden ? SLOW : FAST);
    };
    void loop();
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [refresh]);

  const run = async (task: TaskRow, action: string) => {
    const target = task.result.app && resolveApp(task.result.app) ? task.result.app : '';
    try {
      await answerTask(task.id, action);
    } catch {
      return;
    }
    if (target) {
      windowStore.openWindow({ appId: target, initialPayload: { ...task.result.payload, play: action === 'listen', tab: action === 'talk' ? 'chat' : undefined, talk: action === 'talk' } });
    }
    await refresh();
  };

  const now = Date.now();
  const rows = (data?.tasks ?? []).filter(
    (x) => !dismissed.has(x.id) && (x.state === 'running' || x.state === 'queued' || x.state === 'paused' || (x.state === 'done' && x.offer && !x.answered) || now - x.updated * 1000 < RECENT_MS / 6),
  );
  const active = rows.filter((x) => x.state === 'running' || x.state === 'queued');
  const waiting = rows.filter((x) => x.state === 'done' && x.offer && !x.answered);
  if (!rows.length) return null;

  return (
    <section aria-label={t('title')} className="fixed bottom-[5.5rem] right-4 z-[1000001] w-[22rem] max-w-[calc(100vw-2rem)] text-slate-800">
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white/95 shadow-2xl backdrop-blur">
        <button type="button" onClick={() => setOpen((v) => !v)} className="flex w-full items-center gap-2 px-3.5 py-2.5 text-left" aria-expanded={open}>
          {active.length ? <Loader2 size={16} className="animate-spin text-violet-600" /> : <CheckCircle2 size={16} className="text-emerald-600" />}
          <span className="flex-1 text-sm font-semibold">
            {active.length ? t('running', { n: active.length }) : waiting.length ? t('ready', { n: waiting.length }) : t('title')}
          </span>
          {open ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
        </button>
        {open && (
          <ul className="max-h-[26rem] space-y-2 overflow-y-auto border-t border-slate-100 p-2.5">
            {rows.map((task) => (
              <li key={task.id} className="rounded-xl border border-slate-200 bg-slate-50/70 p-2.5">
                <div className="flex items-start gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{task.title}</div>
                    <div className="truncate text-[11px] text-slate-500">
                      {task.state === 'done' ? task.summary : task.state === 'error' ? t(`error_${task.error}`) : task.stage ? t(`stage_${task.stage}`) : task.steps.find((s) => s.state === 'running')?.text ?? t(`state_${task.state}`)}
                    </div>
                  </div>
                  {(task.state === 'running' || task.state === 'queued') && task.feature !== 'projects' && (
                    <button type="button" aria-label={t('cancel')} onClick={() => void cancelTask(task.id).then(refresh)} className="rounded-md p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-500">
                      <X size={13} />
                    </button>
                  )}
                  {task.state !== 'running' && task.state !== 'queued' && task.state !== 'paused' && task.answered && (
                    <button type="button" aria-label={t('dismiss')} onClick={() => setDismissed((s) => new Set([...s, task.id]))} className="rounded-md p-1 text-slate-400 hover:bg-slate-100">
                      <X size={13} />
                    </button>
                  )}
                </div>
                {(task.state === 'running' || task.state === 'queued') && <div className="mt-2"><Bar value={task.progress} /></div>}
                {task.state === 'error' && (
                  <div className="mt-1.5 flex items-center gap-1 text-[11px] text-rose-600"><AlertTriangle size={12} />{t('failed')}</div>
                )}
                {task.steps.length > 0 && (task.state === 'running' || task.state === 'paused') && (
                  <ul className="mt-2 space-y-0.5 text-[11px] text-slate-500">
                    {task.steps.slice(0, 6).map((s, i) => (
                      <li key={i} className={s.state === 'running' ? 'font-medium text-violet-700' : s.state === 'done' ? 'text-slate-400 line-through' : ''}>{s.text}</li>
                    ))}
                  </ul>
                )}
                {task.state === 'done' && task.offer && !task.answered && (
                  <div className="mt-2 space-y-2">
                    <p className="text-xs leading-snug text-slate-700">{t('question', { title: task.title })}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {task.offer.actions.map((a) => (
                        <button
                          key={a.id}
                          type="button"
                          onClick={() => void run(task, a.id)}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 px-2.5 py-1.5 text-xs font-medium text-white shadow-sm hover:from-violet-500 hover:to-fuchsia-500"
                        >
                          {ACTION_ICON[a.id]}
                          {t(`action_${a.id}`)}
                        </button>
                      ))}
                      <button type="button" onClick={() => void answerTask(task.id, 'later').then(refresh)} className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-600 hover:bg-slate-50">
                        {t('later')}
                      </button>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
};
