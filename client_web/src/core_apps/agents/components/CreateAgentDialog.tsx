import React, { FormEvent, useState } from 'react';
import { Loader2, Plus } from 'lucide-react';
import { CATEGORIES, NEW_AGENT_ID, createAgent } from '../data/teamApi';
import { TeamHandle } from '../hooks/useTeam';
import { fieldClass, primaryClass, useAgentsI18n } from '../scope';
import { Dialog } from './Dialog';

const slug = (text: string) => text.normalize('NFKD').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40);

export const CreateAgentDialog: React.FC<{ readonly handle: TeamHandle; readonly onClose: (id?: string) => void }> = ({ handle, onClose }) => {
  const { t } = useAgentsI18n();
  const [name, setName] = useState('');
  const [id, setId] = useState('');
  const [icon, setIcon] = useState('🤖');
  const [category, setCategory] = useState<string>('assistente');
  const [description, setDescription] = useState('');
  const [capabilities, setCapabilities] = useState('');
  const [instructions, setInstructions] = useState('');
  const [priority, setPriority] = useState(45);
  const finalId = id || slug(name);
  const valid = name.trim().length > 1 && NEW_AGENT_ID.test(finalId);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!valid) {
      return;
    }
    const ok = await handle.run(
      'create',
      () =>
        createAgent({
          id: finalId,
          name: name.trim(),
          icon: icon.trim().slice(0, 4),
          category,
          description: description.trim(),
          capabilities: capabilities.split('\n').map((c) => c.trim()).filter(Boolean).slice(0, 12),
          instructions: instructions.trim(),
          priority,
        }),
      'team_create_failed',
    );
    if (ok) {
      onClose(finalId);
    }
  };

  return (
    <Dialog title={t('new_agent')} closeLabel={t('cancel')} onClose={() => onClose()}>
      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-[5rem_minmax(0,1fr)]">
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('icon')}
          <input maxLength={4} value={icon} onChange={(event) => setIcon(event.target.value)} className={`${fieldClass} text-center text-lg`} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('name')}
          <input required maxLength={60} value={name} onChange={(event) => setName(event.target.value)} className={fieldClass} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400 sm:col-span-2">
          {t('agent_id')}
          <input
            maxLength={41}
            value={finalId}
            onChange={(event) => setId(event.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ''))}
            className={`${fieldClass} font-mono`}
            aria-invalid={!NEW_AGENT_ID.test(finalId)}
          />
          <span className="text-[11px] text-slate-500">{t('agent_id_hint')}</span>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400 sm:col-span-2">
          {t('category')}
          <select value={category} onChange={(event) => setCategory(event.target.value)} className={fieldClass}>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {t(`category_${c}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400 sm:col-span-2">
          {t('agent_description')}
          <textarea rows={2} maxLength={400} value={description} onChange={(event) => setDescription(event.target.value)} className={`${fieldClass} resize-y`} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400 sm:col-span-2">
          {t('capabilities')}
          <textarea rows={3} maxLength={2400} value={capabilities} onChange={(event) => setCapabilities(event.target.value)} placeholder={t('capabilities_hint')} className={`${fieldClass} resize-y`} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400 sm:col-span-2">
          {t('instructions')}
          <textarea rows={3} maxLength={1500} value={instructions} onChange={(event) => setInstructions(event.target.value)} placeholder={t('instructions_placeholder')} className={`${fieldClass} resize-y`} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400 sm:col-span-2">
          <span className="flex justify-between">
            {t('priority')}
            <span className="font-mono text-white">{priority}</span>
          </span>
          <input type="range" min={0} max={200} value={priority} onChange={(event) => setPriority(Number(event.target.value))} className="accent-cyan-400" />
        </label>
        <button type="submit" disabled={!valid || handle.busy !== null} className={`${primaryClass} sm:col-span-2`}>
          {handle.busy === 'create' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Plus className="h-4 w-4" aria-hidden="true" />}
          {t('create_agent')}
        </button>
      </form>
    </Dialog>
  );
};
