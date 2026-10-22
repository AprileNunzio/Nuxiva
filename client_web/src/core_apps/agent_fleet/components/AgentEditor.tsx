import React, { useCallback, useEffect, useState } from 'react';
import { Save, Trash2, X } from 'lucide-react';
import { Btn, Field, Loading, Panel, Pill } from '../../shared/kit';
import { attach, deleteAgent, detach, fetchDetail, updateAgent } from '../api';
import { errorKey, fieldClass, useFleetI18n } from '../scope';
import { CATEGORIES, FleetAgentDetail, KINDS, LinkKind, STATES } from '../types';
import { LinkPicker } from './LinkPicker';

interface Props {
  readonly agentId: string;
  readonly onClose: () => void;
  readonly onChanged: () => void;
}

export const AgentEditor: React.FC<Props> = ({ agentId, onClose, onChanged }) => {
  const { t } = useFleetI18n();
  const [agent, setAgent] = useState<FleetAgentDetail | null>(null);
  const [form, setForm] = useState({ name: '', description: '', instructions: '', kind: 'custom', category: 'altro', state: 'active', priority: 50 });
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState('');
  const [armed, setArmed] = useState(false);

  const adopt = useCallback((next: FleetAgentDetail) => {
    setAgent(next);
    setForm({ name: next.name, description: next.description, instructions: next.instructions, kind: next.kind, category: next.category, state: next.state, priority: next.priority });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setAgent(null);
    setProblem('');
    setArmed(false);
    fetchDetail(agentId, controller.signal)
      .then(adopt)
      .catch((cause) => (controller.signal.aborted ? undefined : setProblem(errorKey(cause))));
    return () => controller.abort();
  }, [agentId, adopt]);

  const guard = async (task: () => Promise<void>) => {
    setBusy(true);
    setProblem('');
    try {
      await task();
    } catch (cause) {
      setProblem(errorKey(cause));
    } finally {
      setBusy(false);
    }
  };

  const save = () =>
    guard(async () => {
      adopt(await updateAgent(agentId, form));
      onChanged();
    });
  const remove = () =>
    guard(async () => {
      await deleteAgent(agentId);
      onChanged();
      onClose();
    });
  const link = (kind: LinkKind, ref: string) =>
    guard(async () => {
      adopt(await attach(agentId, kind, [ref]));
      onChanged();
    });
  const unlink = (kind: LinkKind, ref: string) =>
    guard(async () => {
      adopt(await detach(agentId, kind, ref));
      onChanged();
    });

  const field = <K extends keyof typeof form>(key: K) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm({ ...form, [key]: key === 'priority' ? Number(event.target.value) : event.target.value });

  if (!agent) {
    return problem ? <p role="alert" className="text-sm text-rose-300">{t(problem)}</p> : <Loading label={t('loading')} />;
  }

  return (
    <Panel
      title={agent.name}
      actions={
        <button type="button" onClick={onClose} aria-label={t('close')} className="rounded-lg p-1.5 text-slate-400 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400">
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      }
    >
      <div className="flex flex-col gap-3">
        <p className="font-mono text-[11px] text-slate-500">{agent.id}</p>
        {problem ? <p role="alert" className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">{t(problem)}</p> : null}
        <Field label={t('field_name')}>
          <input className={fieldClass} maxLength={80} value={form.name} onChange={field('name')} />
        </Field>
        <Field label={t('field_description')}>
          <input className={fieldClass} maxLength={400} value={form.description} onChange={field('description')} />
        </Field>
        <div className="grid grid-cols-2 gap-2">
          <Field label={t('field_kind')}>
            <select className={fieldClass} value={form.kind} onChange={field('kind')}>
              {KINDS.map((kind) => <option key={kind} value={kind}>{t(`kind_${kind}`)}</option>)}
            </select>
          </Field>
          <Field label={t('field_category')}>
            <select className={fieldClass} value={form.category} onChange={field('category')}>
              {CATEGORIES.map((category) => <option key={category} value={category}>{t(`category_${category}`)}</option>)}
            </select>
          </Field>
          <Field label={t('field_state')}>
            <select className={fieldClass} value={form.state} onChange={field('state')}>
              {STATES.map((state) => <option key={state} value={state}>{t(`state_${state}`)}</option>)}
            </select>
          </Field>
          <Field label={t('field_priority')}>
            <input type="number" min={0} max={200} className={fieldClass} value={form.priority} onChange={field('priority')} />
          </Field>
        </div>
        <Field label={t('field_instructions')}>
          <textarea className={`${fieldClass} min-h-28`} maxLength={4000} value={form.instructions} onChange={field('instructions')} />
        </Field>
        <div className="flex flex-wrap items-center gap-2">
          <Btn busy={busy} onClick={() => void save()}>
            <Save className="h-3.5 w-3.5" aria-hidden="true" />
            {t('save')}
          </Btn>
          {armed ? (
            <Btn tone="rose" busy={busy} onClick={() => void remove()}>
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              {t('delete_confirm')}
            </Btn>
          ) : (
            <Btn tone="slate" onClick={() => setArmed(true)}>
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              {t('delete')}
            </Btn>
          )}
          {agent.origin === 'nuxiva' ? <Pill tone="purple">{t('origin_nuxiva')}</Pill> : null}
        </div>
        <LinkPicker kind="tool" current={agent.tools} missing={agent.missing_tools} busy={busy} onAttach={(ref) => void link('tool', ref)} onDetach={(ref) => void unlink('tool', ref)} />
        <LinkPicker kind="widget" current={agent.widgets} missing={agent.missing_widgets} busy={busy} onAttach={(ref) => void link('widget', ref)} onDetach={(ref) => void unlink('widget', ref)} />
      </div>
    </Panel>
  );
};
