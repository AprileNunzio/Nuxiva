import React, { FormEvent, useState } from 'react';
import { Loader2, Plus } from 'lucide-react';
import { Agent, NEW_AGENT_ID, createWidget } from '../data/teamApi';
import { TeamHandle } from '../hooks/useTeam';
import { fieldClass, primaryClass, useAgentsI18n } from '../scope';
import { Dialog } from './Dialog';

const SIZES = ['s', 'm', 'l'] as const;

export const CreateWidgetDialog: React.FC<{ readonly agents: readonly Agent[]; readonly handle: TeamHandle; readonly onClose: () => void }> = ({ agents, handle, onClose }) => {
  const { t } = useAgentsI18n();
  const [id, setId] = useState('');
  const [name, setName] = useState('');
  const [icon, setIcon] = useState('▣');
  const [description, setDescription] = useState('');
  const [size, setSize] = useState<(typeof SIZES)[number]>('m');
  const [priority, setPriority] = useState(40);
  const [personal, setPersonal] = useState(false);
  const [agent, setAgent] = useState('forge');
  const valid = NEW_AGENT_ID.test(id) && name.trim().length > 1;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (valid && (await handle.run('create', () => createWidget({ id, name: name.trim(), icon, description: description.trim(), size, priority, personal, agent }), 'team_create_failed'))) {
      onClose();
    }
  };

  return (
    <Dialog title={t('new_widget')} closeLabel={t('cancel')} onClose={onClose}>
      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
        <p className="text-xs text-slate-400 sm:col-span-2">{t('widget_hint')}</p>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('widget_id')}
          <input required maxLength={41} value={id} onChange={(event) => setId(event.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ''))} className={`${fieldClass} font-mono`} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('name')}
          <input required maxLength={60} value={name} onChange={(event) => setName(event.target.value)} className={fieldClass} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('icon')}
          <input maxLength={4} value={icon} onChange={(event) => setIcon(event.target.value)} className={fieldClass} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('owner')}
          <select value={agent} onChange={(event) => setAgent(event.target.value)} className={fieldClass}>
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400 sm:col-span-2">
          {t('widget_description')}
          <input maxLength={300} value={description} onChange={(event) => setDescription(event.target.value)} className={fieldClass} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('size')}
          <select value={size} onChange={(event) => setSize(SIZES.find((s) => s === event.target.value) ?? 'm')} className={fieldClass}>
            {SIZES.map((s) => (
              <option key={s} value={s}>
                {t(`size_${s}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          <span className="flex justify-between">
            {t('priority')}
            <span className="font-mono text-white">{priority}</span>
          </span>
          <input type="range" min={0} max={100} value={priority} onChange={(event) => setPriority(Number(event.target.value))} className="accent-cyan-400" />
        </label>
        <label className="flex cursor-pointer items-center justify-between gap-3 rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2 text-sm text-slate-100 sm:col-span-2">
          {t('personal_data')}
          <input type="checkbox" role="switch" checked={personal} onChange={(event) => setPersonal(event.target.checked)} className="h-5 w-9 accent-cyan-400" />
        </label>
        <button type="submit" disabled={!valid || handle.busy !== null} className={`${primaryClass} sm:col-span-2`}>
          {handle.busy === 'create' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Plus className="h-4 w-4" aria-hidden="true" />}
          {t('create_widget')}
        </button>
      </form>
    </Dialog>
  );
};
