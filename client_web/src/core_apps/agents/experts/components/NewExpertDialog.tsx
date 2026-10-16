import React, { FormEvent, useState } from 'react';
import { Sparkles, UserPlus } from 'lucide-react';
import { Dialog } from '../../components/Dialog';
import { fieldClass, primaryClass } from '../../scope';
import { ExpertTemplate, createExpert } from '../data/expertsApi';
import { ExpertsHandle } from '../hooks/useExperts';
import { useExpertsI18n } from '../scope';
import { ExpertAvatar } from './ExpertAvatar';

interface NewExpertDialogProps {
  readonly templates: readonly ExpertTemplate[];
  readonly handle: ExpertsHandle;
  readonly onClose: (id?: string) => void;
}

export const NewExpertDialog: React.FC<NewExpertDialogProps> = ({ templates, handle, onClose }) => {
  const { t } = useExpertsI18n();
  const [name, setName] = useState('');
  const [role, setRole] = useState('');
  const [specialty, setSpecialty] = useState('');
  const [knowledge, setKnowledge] = useState('');
  const [icon, setIcon] = useState('🧑‍💼');
  const [color, setColor] = useState('#29e0ff');
  const valid = name.trim().length > 1 && role.trim().length > 2 && specialty.trim().length > 2;

  const hire = async (template: string) => {
    const made = await handle.run('create', () => createExpert({ template }), 'expert_create_failed');
    if (made) {
      onClose(made.id);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!valid) {
      return;
    }
    const made = await handle.run(
      'create',
      () =>
        createExpert({
          name: name.trim(),
          role: role.trim(),
          specialty: specialty.trim(),
          knowledge: knowledge.split('\n').map((k) => k.trim()).filter(Boolean).slice(0, 16),
          icon: icon.trim().slice(0, 4),
          color,
        }),
      'expert_create_failed',
    );
    if (made) {
      onClose(made.id);
    }
  };

  return (
    <Dialog title={t('new_expert')} closeLabel={t('cancel')} onClose={() => onClose()}>
      <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
        <Sparkles className="h-3.5 w-3.5 text-cyan-300" aria-hidden="true" />
        {t('templates')}
      </h3>
      <div className="grid gap-2 sm:grid-cols-2">
        {templates.map((tpl) => (
          <button
            key={tpl.id}
            type="button"
            disabled={handle.busy !== null}
            onClick={() => void hire(tpl.id)}
            className="flex items-start gap-3 rounded-2xl border border-slate-700 bg-slate-950/60 p-3 text-left transition hover:border-cyan-400/60 hover:bg-cyan-400/5 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            <ExpertAvatar icon={tpl.icon} color={tpl.color} />
            <span className="min-w-0">
              <span className="block font-['Rajdhani'] text-lg font-bold text-white">{tpl.name}</span>
              <span className="block text-xs font-semibold" style={{ color: tpl.color }}>
                {tpl.role}
              </span>
              <span className="mt-1 block text-[0.6875rem] text-slate-400">{tpl.specialty}</span>
              <span className="mt-1 block font-mono text-[0.625rem] text-slate-500">{t('template_tools', { count: tpl.tools.length })}</span>
            </span>
          </button>
        ))}
      </div>
      <h3 className="mb-2 mt-5 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
        <UserPlus className="h-3.5 w-3.5 text-cyan-300" aria-hidden="true" />
        {t('custom')}
      </h3>
      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-[5rem_5rem_minmax(0,1fr)]">
        <label className="grid gap-1 text-xs text-slate-400">
          {t('icon')}
          <input value={icon} maxLength={4} onChange={(e) => setIcon(e.target.value)} className={`${fieldClass} text-center text-lg`} />
        </label>
        <label className="grid gap-1 text-xs text-slate-400">
          {t('color')}
          <input type="color" value={color} onChange={(e) => setColor(e.target.value)} className="h-10 w-full cursor-pointer rounded-xl border border-slate-700 bg-slate-950" />
        </label>
        <label className="grid gap-1 text-xs text-slate-400">
          {t('name')}
          <input value={name} maxLength={40} required onChange={(e) => setName(e.target.value)} className={fieldClass} />
        </label>
        <label className="grid gap-1 text-xs text-slate-400 sm:col-span-3">
          {t('role')}
          <input value={role} maxLength={80} required placeholder={t('role_hint')} onChange={(e) => setRole(e.target.value)} className={fieldClass} />
        </label>
        <label className="grid gap-1 text-xs text-slate-400 sm:col-span-3">
          {t('specialty')}
          <input value={specialty} maxLength={240} required onChange={(e) => setSpecialty(e.target.value)} className={fieldClass} />
        </label>
        <label className="grid gap-1 text-xs text-slate-400 sm:col-span-3">
          {t('knowledge_hint')}
          <textarea value={knowledge} rows={3} onChange={(e) => setKnowledge(e.target.value)} className={fieldClass} />
        </label>
        <p className="text-[0.6875rem] text-slate-500 sm:col-span-3">{t('custom_tools_hint')}</p>
        <div className="flex justify-end gap-2 sm:col-span-3">
          <button type="button" onClick={() => onClose()} className="rounded-xl px-4 py-2 text-sm text-slate-300 hover:text-white">
            {t('cancel')}
          </button>
          <button type="submit" disabled={!valid || handle.busy !== null} className={primaryClass}>
            {t('hire')}
          </button>
        </div>
      </form>
    </Dialog>
  );
};
