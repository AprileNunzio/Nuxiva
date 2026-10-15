import React, { FormEvent, useState } from 'react';
import { Loader2, Minus, Plus } from 'lucide-react';
import { Agent, PARAM_NAME, TOOL_NAME, ToolInfo, createTool } from '../data/teamApi';
import { TeamHandle } from '../hooks/useTeam';
import { chipClass, fieldClass, primaryClass, useAgentsI18n } from '../scope';
import { Dialog } from './Dialog';

interface Row {
  readonly key: string;
  readonly value: string;
}

const MAX_STEPS = 10;
const MAX_PARAMS = 8;

function parseArgs(text: string): Record<string, unknown> | null {
  if (!text.trim()) {
    return {};
  }
  try {
    const value: unknown = JSON.parse(text);
    return typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

interface Props {
  readonly agents: readonly Agent[];
  readonly tools: readonly ToolInfo[];
  readonly handle: TeamHandle;
  readonly onClose: () => void;
}

export const CreateToolDialog: React.FC<Props> = ({ agents, tools, handle, onClose }) => {
  const { t } = useAgentsI18n();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [agent, setAgent] = useState('forge');
  const [params, setParams] = useState<readonly Row[]>([]);
  const [steps, setSteps] = useState<readonly Row[]>([{ key: '', value: '{}' }]);
  const base = tools.filter((tool) => !tool.custom && tool.enabled);
  const argsOk = steps.map((s) => parseArgs(s.value));
  const valid =
    TOOL_NAME.test(name) &&
    params.every((p) => PARAM_NAME.test(p.key)) &&
    steps.length > 0 &&
    steps.every((s, i) => s.key && argsOk[i] !== null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!valid) {
      return;
    }
    const ok = await handle.run(
      'create',
      () =>
        createTool({
          name,
          description: description.trim(),
          agent,
          params: Object.fromEntries(params.map((p) => [p.key, p.value.trim()])),
          steps: steps.map((s, i) => ({ tool: s.key, args: argsOk[i] ?? {} })),
        }),
      'team_create_failed',
    );
    if (ok) {
      onClose();
    }
  };

  const edit = (setter: React.Dispatch<React.SetStateAction<readonly Row[]>>, index: number, change: Partial<Row>) =>
    setter((rows) => rows.map((row, i) => (i === index ? { ...row, ...change } : row)));

  return (
    <Dialog title={t('new_tool')} closeLabel={t('cancel')} onClose={onClose}>
      <form onSubmit={submit} className="flex flex-col gap-3">
        <p className="text-xs text-slate-400">{t('tool_hint')}</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-xs text-slate-400">
            {t('tool_name')}
            <input required maxLength={41} value={name} onChange={(event) => setName(event.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))} className={`${fieldClass} font-mono`} />
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
        </div>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('tool_description')}
          <input maxLength={300} value={description} onChange={(event) => setDescription(event.target.value)} className={fieldClass} />
        </label>
        <fieldset className="flex flex-col gap-2 rounded-xl border border-slate-800/80 p-3">
          <legend className="px-1 text-xs font-semibold text-slate-300">{t('params')}</legend>
          {params.map((p, i) => (
            <div key={i} className="flex gap-2">
              <input aria-label={t('param_name')} placeholder={t('param_name')} maxLength={31} value={p.key} onChange={(event) => edit(setParams, i, { key: event.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '') })} className={`${fieldClass} w-36 font-mono`} />
              <input aria-label={t('param_description')} placeholder={t('param_description')} maxLength={120} value={p.value} onChange={(event) => edit(setParams, i, { value: event.target.value })} className={`${fieldClass} min-w-0 flex-1`} />
              <button type="button" aria-label={t('remove')} onClick={() => setParams((rows) => rows.filter((_, j) => j !== i))} className={`${chipClass} border-slate-700 text-slate-400`}>
                <Minus className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>
          ))}
          {params.length < MAX_PARAMS && (
            <button type="button" onClick={() => setParams((rows) => [...rows, { key: '', value: '' }])} className={`${chipClass} self-start border-slate-700 text-slate-300`}>
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
              {t('add_param')}
            </button>
          )}
        </fieldset>
        <fieldset className="flex flex-col gap-2 rounded-xl border border-slate-800/80 p-3">
          <legend className="px-1 text-xs font-semibold text-slate-300">{t('steps')}</legend>
          {steps.map((s, i) => (
            <div key={i} className="flex flex-col gap-1.5 rounded-lg border border-slate-800/60 bg-slate-950/40 p-2">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-cyan-300">s{i + 1}</span>
                <select aria-label={t('step_tool')} value={s.key} onChange={(event) => edit(setSteps, i, { key: event.target.value })} className={`${fieldClass} min-w-0 flex-1 py-1.5`}>
                  <option value="">{t('step_tool')}</option>
                  {base.map((tool) => (
                    <option key={tool.name} value={tool.name}>
                      {tool.name}
                    </option>
                  ))}
                </select>
                {steps.length > 1 && (
                  <button type="button" aria-label={t('remove')} onClick={() => setSteps((rows) => rows.filter((_, j) => j !== i))} className={`${chipClass} border-slate-700 text-slate-400`}>
                    <Minus className="h-3.5 w-3.5" aria-hidden="true" />
                  </button>
                )}
              </div>
              {s.key && <p className="font-mono text-[10px] text-slate-500">{Object.keys(base.find((x) => x.name === s.key)?.args ?? {}).join(', ') || t('no_args')}</p>}
              <textarea
                rows={2}
                aria-label={t('step_args')}
                aria-invalid={argsOk[i] === null}
                value={s.value}
                onChange={(event) => edit(setSteps, i, { value: event.target.value })}
                className={`${fieldClass} resize-y font-mono text-xs ${argsOk[i] === null ? 'border-rose-400/60' : ''}`}
              />
            </div>
          ))}
          {steps.length < MAX_STEPS && (
            <button type="button" onClick={() => setSteps((rows) => [...rows, { key: '', value: '{}' }])} className={`${chipClass} self-start border-slate-700 text-slate-300`}>
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
              {t('add_step')}
            </button>
          )}
        </fieldset>
        <button type="submit" disabled={!valid || handle.busy !== null} className={primaryClass}>
          {handle.busy === 'create' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Plus className="h-4 w-4" aria-hidden="true" />}
          {t('create_tool')}
        </button>
      </form>
    </Dialog>
  );
};
