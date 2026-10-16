import React, { useMemo, useState } from 'react';
import { BookOpen, Pencil, Power, Trash2, Wrench } from 'lucide-react';
import { fieldClass, primaryClass } from '../../scope';
import { AssignableTool, Expert, deleteExpert, updateExpert } from '../data/expertsApi';
import { ExpertsHandle } from '../hooks/useExperts';
import { glassClass, labelClass, useExpertsI18n } from '../scope';
import { ExpertAvatar } from './ExpertAvatar';

interface ExpertProfileProps {
  readonly expert: Expert;
  readonly tools: readonly AssignableTool[];
  readonly handle: ExpertsHandle;
  readonly onDeleted: () => void;
}

export const ExpertProfile: React.FC<ExpertProfileProps> = ({ expert, tools, handle, onDeleted }) => {
  const { t } = useExpertsI18n();
  const [editing, setEditing] = useState(false);
  const [instructions, setInstructions] = useState(expert.instructions);
  const [knowledge, setKnowledge] = useState(expert.knowledge.join('\n'));
  const [chosen, setChosen] = useState<readonly string[]>(expert.tools);
  const [filter, setFilter] = useState('');
  const [arming, setArming] = useState(false);
  const descriptions = useMemo(() => new Map(tools.map((x) => [x.name, x.description])), [tools]);
  const visible = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return tools.filter((x) => !q || x.name.includes(q) || x.description.toLowerCase().includes(q)).slice(0, 60);
  }, [tools, filter]);

  const save = async () => {
    const ok = await handle.run(
      'save',
      () => updateExpert(expert.id, { instructions: instructions.trim(), knowledge: knowledge.split('\n').map((k) => k.trim()).filter(Boolean).slice(0, 16), tools: chosen }),
      'expert_update_failed',
    );
    if (ok !== null) {
      setEditing(false);
    }
  };

  const toggle = (name: string) => setChosen((prev) => (prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name].slice(0, 24)));

  const remove = async () => {
    if (!arming) {
      setArming(true);
      window.setTimeout(() => setArming(false), 4000);
      return;
    }
    if ((await handle.run('delete', () => deleteExpert(expert.id), 'expert_delete_failed')) !== null) {
      onDeleted();
    }
  };

  return (
    <section className={glassClass} aria-labelledby="expert-name">
      <div className="pointer-events-none absolute -right-16 -top-20 h-56 w-56 rounded-full blur-3xl" style={{ background: `${expert.color}22` }} aria-hidden="true" />
      <header className="relative flex flex-wrap items-start gap-4">
        <ExpertAvatar icon={expert.icon} color={expert.color} busy={Boolean(expert.doing)} size="lg" />
        <div className="min-w-0 flex-1">
          <h2 id="expert-name" className="font-['Rajdhani'] text-3xl font-bold leading-tight text-white 3xl:text-4xl">
            {expert.name}
          </h2>
          <p className="text-sm font-semibold" style={{ color: expert.color }}>
            {expert.role}
          </p>
          <p className="mt-1 text-sm text-slate-300">{expert.specialty}</p>
        </div>
        <div className="flex w-full flex-wrap gap-2 sm:w-auto">
          <button
            type="button"
            onClick={() => void handle.run('power', () => updateExpert(expert.id, { enabled: !expert.enabled }), 'expert_update_failed')}
            aria-pressed={expert.enabled}
            className={`flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
              expert.enabled ? 'border-emerald-400/50 bg-emerald-400/10 text-emerald-100' : 'border-slate-700 text-slate-400'
            }`}
          >
            <Power className="h-3.5 w-3.5" aria-hidden="true" />
            {expert.enabled ? t('on') : t('off')}
          </button>
          <button
            type="button"
            onClick={() => setEditing((v) => !v)}
            aria-expanded={editing}
            className="flex items-center gap-1.5 rounded-xl border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-cyan-400/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
            {t('edit')}
          </button>
          <button
            type="button"
            onClick={() => void remove()}
            className={`flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-400 ${
              arming ? 'border-rose-400 bg-rose-500/20 text-rose-100' : 'border-slate-700 text-slate-400 hover:text-rose-200'
            }`}
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
            {arming ? t('delete_confirm') : t('delete')}
          </button>
        </div>
      </header>

      {!editing && (
        <div className="relative mt-5 grid gap-4 xl:grid-cols-2">
          <div>
            <h3 className={labelClass}>
              <BookOpen className="h-3.5 w-3.5 text-cyan-300" aria-hidden="true" />
              {t('knowledge')}
            </h3>
            <ul className="flex flex-wrap gap-1.5">
              {expert.knowledge.map((k) => (
                <li key={k} className="rounded-lg border border-slate-700/80 bg-slate-950/50 px-2.5 py-1 text-xs text-slate-200">
                  {k}
                </li>
              ))}
              {expert.knowledge.length === 0 && <li className="text-xs text-slate-500">{t('knowledge_empty')}</li>}
            </ul>
          </div>
          <div>
            <h3 className={labelClass}>
              <Wrench className="h-3.5 w-3.5 text-cyan-300" aria-hidden="true" />
              {t('tools')}
            </h3>
            <ul className="flex flex-wrap gap-1.5">
              {expert.tools.map((name) => (
                <li key={name} title={descriptions.get(name)} className="rounded-lg border border-cyan-400/30 bg-cyan-400/5 px-2.5 py-1 font-mono text-[0.6875rem] text-cyan-100">
                  {name}
                </li>
              ))}
              {expert.tools.length === 0 && <li className="text-xs text-slate-500">{t('tools_empty')}</li>}
            </ul>
          </div>
          {expert.instructions && (
            <p className="rounded-xl border border-indigo-400/20 bg-indigo-400/5 px-3 py-2 text-xs text-indigo-100 xl:col-span-2">{expert.instructions}</p>
          )}
        </div>
      )}

      {editing && (
        <div className="relative mt-5 grid gap-3 xl:grid-cols-2">
          <label className="grid gap-1 text-xs text-slate-400">
            {t('instructions')}
            <textarea value={instructions} maxLength={1200} rows={4} onChange={(e) => setInstructions(e.target.value)} className={fieldClass} />
          </label>
          <label className="grid gap-1 text-xs text-slate-400">
            {t('knowledge_hint')}
            <textarea value={knowledge} rows={4} onChange={(e) => setKnowledge(e.target.value)} className={fieldClass} />
          </label>
          <fieldset className="xl:col-span-2">
            <legend className="mb-2 text-xs text-slate-400">{t('tools_pick', { count: chosen.length })}</legend>
            <input type="search" value={filter} onChange={(e) => setFilter(e.target.value)} placeholder={t('tools_search')} aria-label={t('tools_search')} className={`${fieldClass} mb-2 w-full`} />
            <div className="grid max-h-64 gap-1.5 overflow-y-auto pr-1 sm:grid-cols-2 3xl:grid-cols-3">
              {visible.map((x) => (
                <label key={x.name} className="flex cursor-pointer items-start gap-2 rounded-lg border border-slate-800 bg-slate-950/50 px-2.5 py-1.5 text-xs hover:border-cyan-400/40">
                  <input type="checkbox" checked={chosen.includes(x.name)} onChange={() => toggle(x.name)} className="mt-0.5 accent-cyan-400" />
                  <span className="min-w-0">
                    <span className="block font-mono text-cyan-100">{x.name}</span>
                    <span className="block truncate text-slate-500">{x.description}</span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
          <div className="flex justify-end gap-2 xl:col-span-2">
            <button type="button" onClick={() => setEditing(false)} className="rounded-xl px-4 py-2 text-sm text-slate-300 hover:text-white">
              {t('cancel')}
            </button>
            <button type="button" disabled={handle.busy !== null} onClick={() => void save()} className={primaryClass}>
              {t('save')}
            </button>
          </div>
        </div>
      )}
    </section>
  );
};
