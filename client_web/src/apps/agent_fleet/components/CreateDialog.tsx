import React, { FormEvent, useState } from 'react';
import { Plus, Wand2 } from 'lucide-react';
import { Btn, Field } from '../../shared/kit';
import { createAgent, suggest } from '../api';
import { errorKey, fieldClass, useFleetI18n } from '../scope';
import { AgentKind, CATEGORIES, KINDS } from '../types';
import { Dialog } from './Dialog';

interface Props {
  readonly onClose: () => void;
  readonly onCreated: (id: string) => void;
}

export const CreateDialog: React.FC<Props> = ({ onClose, onCreated }) => {
  const { t } = useFleetI18n();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [kind, setKind] = useState<AgentKind>('custom');
  const [category, setCategory] = useState<string>('altro');
  const [instructions, setInstructions] = useState('');
  const [tools, setTools] = useState<readonly string[]>([]);
  const [widgets, setWidgets] = useState<readonly string[]>([]);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState('');

  const guess = async () => {
    setBusy(true);
    setProblem('');
    try {
      const found = await suggest(description || name);
      setTools(found.tools);
      setWidgets(found.widgets);
    } catch (cause) {
      setProblem(errorKey(cause));
    } finally {
      setBusy(false);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (name.trim().length < 3) {
      setProblem('error_invalid_name');
      return;
    }
    setBusy(true);
    setProblem('');
    try {
      const created = await createAgent({ name: name.trim(), description: description.trim(), kind, category: category as (typeof CATEGORIES)[number], instructions: instructions.trim(), tools, widgets });
      onCreated(created.id);
      onClose();
    } catch (cause) {
      setProblem(errorKey(cause));
      setBusy(false);
    }
  };

  return (
    <Dialog title={t('new_agent')} closeLabel={t('close')} onClose={onClose}>
      <form onSubmit={(event) => void submit(event)} className="flex flex-col gap-3">
        {problem ? <p role="alert" className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">{t(problem)}</p> : null}
        <Field label={t('field_name')}>
          <input className={fieldClass} maxLength={80} value={name} onChange={(event) => setName(event.target.value)} required />
        </Field>
        <Field label={t('field_description')}>
          <input className={fieldClass} maxLength={400} value={description} onChange={(event) => setDescription(event.target.value)} />
        </Field>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <Field label={t('field_kind')}>
            <select className={fieldClass} value={kind} onChange={(event) => setKind(event.target.value as AgentKind)}>
              {KINDS.map((option) => <option key={option} value={option}>{t(`kind_${option}`)}</option>)}
            </select>
          </Field>
          <Field label={t('field_category')}>
            <select className={fieldClass} value={category} onChange={(event) => setCategory(event.target.value)}>
              {CATEGORIES.map((option) => <option key={option} value={option}>{t(`category_${option}`)}</option>)}
            </select>
          </Field>
        </div>
        <Field label={t('field_instructions')}>
          <textarea className={`${fieldClass} min-h-24`} maxLength={4000} value={instructions} onChange={(event) => setInstructions(event.target.value)} />
        </Field>
        <div className="flex flex-col gap-2 rounded-xl border border-slate-800 p-3">
          <Btn tone="purple" busy={busy} onClick={() => void guess()}>
            <Wand2 className="h-3.5 w-3.5" aria-hidden="true" />
            {t('suggest')}
          </Btn>
          <p className="text-xs text-slate-400">{t('suggested', { tools: tools.length, widgets: widgets.length })}</p>
          <p className="break-words font-mono text-[11px] text-slate-500">{[...tools, ...widgets].join(', ')}</p>
        </div>
        <div className="flex justify-end gap-2">
          <Btn tone="slate" onClick={onClose}>{t('cancel')}</Btn>
          <Btn type="submit" busy={busy}>
            <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            {t('create')}
          </Btn>
        </div>
      </form>
    </Dialog>
  );
};
