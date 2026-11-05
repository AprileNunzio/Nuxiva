import React, { useCallback, useEffect, useRef, useState } from 'react';
import { CheckCircle2, ChevronDown, ChevronUp, Loader2, Play, MessageCircle, ExternalLink, X, AlertTriangle } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { resolveApp } from '../window_manager/registry';
import { windowStore } from '../window_manager/WindowStore';
import { answerTask, cancelTask, loadTasks, type TaskRow, type TaskSnapshot } from './taskApi';
import './task_tray.css';

const FAST = 2000;
const SLOW = 9000;
const RECENT_MS = 6 * 3600 * 1000;

const ACTION_ICON: Record<string, React.ReactNode> = {
  listen: <Play size={13} />,
  open: <ExternalLink size={13} />,
  talk: <MessageCircle size={13} />,
};

const Bar: React.FC<{ readonly value: number }> = ({ value }) => (
  <div className="os-task-progress-track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value * 100)}>
    <div className="os-task-progress-bar" style={{ width: `${Math.round(value * 100)}%` }} />
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

  const openTaskApp = (task: TaskRow) => {
    const target = task.result.app && resolveApp(task.result.app) ? task.result.app : '';
    if (target) {
      windowStore.openWindow({ appId: target, initialPayload: { ...task.result.payload } });
    }
  };

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
    <section aria-label={t('title')} className="os-task-tray-popup">
      <div className="os-task-tray-panel">
        <button type="button" onClick={() => setOpen((v) => !v)} className="os-task-tray-header" aria-expanded={open}>
          {active.length ? <Loader2 size={16} className="network-spinning" /> : <CheckCircle2 size={16} className="network-icon-online" />}
          <span className="os-task-tray-title">
            {active.length ? t('running', { n: active.length }) : waiting.length ? t('ready', { n: waiting.length }) : t('title')}
          </span>
          {open ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
        </button>
        {open && (
          <ul className="os-task-tray-list">
            {rows.map((task) => (
              <li key={task.id} className="os-task-card">
                <div className="os-task-card-main">
                  <div className="os-task-card-info">
                    <div className="os-task-card-title">{task.title}</div>
                    <div className="os-task-card-sub">
                      {task.state === 'done' ? task.summary : task.state === 'error' ? t(`error_${task.error}`) : task.stage ? task.stage : task.steps.find((s) => s.state === 'running')?.text ?? t(`state_${task.state}`)}
                    </div>
                  </div>
                  {task.result.app && (
                    <button type="button" aria-label={t('action_open')} onClick={() => openTaskApp(task)} className="os-task-action-icon-btn">
                      <ExternalLink size={13} />
                    </button>
                  )}
                  {(task.state === 'running' || task.state === 'queued' || task.state === 'paused') && (
                    <button type="button" aria-label={t('cancel')} onClick={() => void cancelTask(task).then(refresh).catch(() => undefined)} className="os-task-action-icon-btn">
                      <X size={13} />
                    </button>
                  )}
                  {task.state !== 'running' && task.state !== 'queued' && task.state !== 'paused' && task.answered && (
                    <button type="button" aria-label={t('dismiss')} onClick={() => setDismissed((s) => new Set([...s, task.id]))} className="os-task-action-icon-btn">
                      <X size={13} />
                    </button>
                  )}
                </div>
                {(task.state === 'running' || task.state === 'queued') && <div><Bar value={task.progress} /></div>}
                {task.state === 'error' && (
                  <div className="os-task-error-text"><AlertTriangle size={12} />{t('failed')}</div>
                )}
                {task.steps.length > 0 && (task.state === 'running' || task.state === 'paused') && (
                  <ul className="os-task-steps">
                    {task.steps.slice(0, 6).map((s, i) => (
                      <li key={i} className={s.state === 'running' ? 'os-task-step-running' : s.state === 'done' ? 'os-task-step-done' : ''}>{s.text}</li>
                    ))}
                  </ul>
                )}
                {task.state === 'done' && task.offer && !task.answered && (
                  <div className="os-task-offer-box">
                    <p className="os-task-offer-question">{t('question', { title: task.title })}</p>
                    <div className="os-task-offer-actions">
                      {task.offer.actions.map((a) => (
                        <button
                          key={a.id}
                          type="button"
                          onClick={() => void run(task, a.id)}
                          className="os-task-btn-primary"
                        >
                          {ACTION_ICON[a.id]}
                          {t(`action_${a.id}`)}
                        </button>
                      ))}
                      <button type="button" onClick={() => void answerTask(task.id, 'later').then(refresh)} className="os-task-btn-secondary">
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
