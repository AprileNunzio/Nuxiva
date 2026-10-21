import React, { FormEvent, useEffect, useState } from 'react';
import { Loader2, RotateCcw, Save, Send, Trash2 } from 'lucide-react';
import { ConfirmDialog } from '../../../shared/ui/ConfirmDialog';
import { Agent, MODES, Mode, deleteAgent, messageAgent, setAgentMode, updateAgent } from '../data/teamApi';
import { TeamHandle } from '../hooks/useTeam';
import { chipClass, fieldClass, primaryClass, useAgentsI18n } from '../scope';

export const OverviewTab: React.FC<{ readonly agent: Agent; readonly handle: TeamHandle; readonly onDeleted: () => void }> = ({ agent, handle, onDeleted }) => {
  const { t } = useAgentsI18n();
  const [priority, setPriority] = useState(agent.priority);
  const [instructions, setInstructions] = useState(agent.instructions);
  const [message, setMessage] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const busy = handle.busy !== null;
  const custom = agent.source === 'user' || agent.source === 'ai';

  useEffect(() => {
    setPriority(agent.priority);
    setInstructions(agent.instructions);
  }, [agent.id, agent.priority, agent.instructions]);

  const dirty = priority !== agent.priority || instructions.trim() !== agent.instructions;

  const send = async (event: FormEvent) => {
    event.preventDefault();
    const text = message.trim();
    if (text && (await handle.run('message', () => messageAgent(agent.id, text), 'team_message_failed'))) {
      setMessage('');
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-slate-300">{agent.description || t('no_description')}</p>
      {agent.can.length > 0 && (
        <ul className="grid gap-1.5 sm:grid-cols-2">
          {agent.can.map((c) => (
            <li key={c} className="rounded-lg border border-slate-800/80 bg-slate-950/40 px-3 py-1.5 text-xs text-slate-300">
              {c}
            </li>
          ))}
        </ul>
      )}
      <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-3">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">{t('state')}</p>
        <p className={`mt-1 text-sm ${agent.enabled ? 'text-emerald-300' : 'text-slate-400'}`}>{agent.reason || t(agent.enabled ? 'active' : 'inactive')}</p>
        {agent.toggle && !agent.fixed ? (
          <div className="mt-2 flex flex-wrap gap-1.5" role="radiogroup" aria-label={t('mode')}>
            {MODES.map((mode: Mode) => (
              <button
                key={mode}
                type="button"
                role="radio"
                aria-checked={agent.mode === mode}
                disabled={busy}
                onClick={() => void handle.run('mode', () => setAgentMode(agent.id, mode), 'team_mode_failed')}
                className={`${chipClass} ${agent.mode === mode ? 'border-cyan-400/70 bg-cyan-400/15 text-cyan-100' : 'border-slate-700 text-slate-300'}`}
              >
                {t(`mode_${mode}`)}
              </button>
            ))}
          </div>
        ) : (
          <p className="mt-1 text-[11px] text-slate-500">{t('always_on')}</p>
        )}
        {agent.doing && <p className="mt-2 text-xs text-cyan-200">{t('doing', { what: agent.doing })}</p>}
      </div>
      <div className="grid gap-3">
        <label className="flex flex-col gap-1.5 text-xs text-slate-400">
          <span className="flex items-center justify-between">
            {t('priority')}
            <span className="font-mono text-sm text-white">
              {priority}
              {priority !== agent.defaultPriority && <span className="ml-1 text-[10px] text-slate-500">({t('default_value', { value: agent.defaultPriority })})</span>}
            </span>
          </span>
          <input type="range" min={0} max={200} value={priority} onChange={(event) => setPriority(Number(event.target.value))} className="w-full accent-cyan-400" />
          <span className="text-[11px] text-slate-500">{t('priority_hint')}</span>
        </label>
        <label className="flex flex-col gap-1.5 text-xs text-slate-400">
          {t('instructions')}
          <textarea rows={4} maxLength={1500} value={instructions} onChange={(event) => setInstructions(event.target.value)} placeholder={t('instructions_placeholder')} className={`${fieldClass} resize-y`} />
          <span className="text-[11px] text-slate-500">{t('instructions_hint')}</span>
        </label>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy || !dirty}
            onClick={() => void handle.run('save', () => updateAgent(agent.id, { priority, instructions: instructions.trim() }), 'team_update_failed')}
            className={primaryClass}
          >
            {handle.busy === 'save' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="h-4 w-4" aria-hidden="true" />}
            {t('save')}
          </button>
          {priority !== agent.defaultPriority && (
            <button
              type="button"
              disabled={busy}
              onClick={() => void handle.run('save', () => updateAgent(agent.id, { priority: null }), 'team_update_failed')}
              className={`${chipClass} border-slate-700 text-slate-300`}
            >
              <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
              {t('reset_priority')}
            </button>
          )}
        </div>
      </div>
      <form onSubmit={send} className="flex flex-col gap-1.5">
        <label htmlFor="agent-task" className="text-xs text-slate-400">
          {t('task_label', { count: agent.inbox })}
        </label>
        <div className="flex gap-2">
          <input id="agent-task" maxLength={400} value={message} onChange={(event) => setMessage(event.target.value)} placeholder={t('task_placeholder')} className={`${fieldClass} min-w-0 flex-1`} />
          <button type="submit" disabled={busy || !message.trim()} aria-label={t('task_send')} className={`${chipClass} border-cyan-400/50 bg-cyan-400/10 px-3 text-cyan-100`}>
            <Send className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </form>
      {custom && (
        <button type="button" disabled={busy} onClick={() => setConfirmDelete(true)} className={`${chipClass} self-start border-rose-400/50 bg-rose-400/10 py-2 text-rose-200`}>
          <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
          {t('delete_agent')}
        </button>
      )}
      {confirmDelete && (
        <ConfirmDialog
          title={t('delete_agent_title', { name: agent.name })}
          body={t('delete_agent_body')}
          confirmLabel={t('delete_agent')}
          cancelLabel={t('cancel')}
          pending={busy}
          tone="danger"
          onConfirm={() =>
            void handle.run('delete', () => deleteAgent(agent.id), 'team_delete_failed').then((ok) => {
              setConfirmDelete(false);
              if (ok) {
                onDeleted();
              }
            })
          }
          onCancel={() => setConfirmDelete(false)}
        />
      )}
    </div>
  );
};
