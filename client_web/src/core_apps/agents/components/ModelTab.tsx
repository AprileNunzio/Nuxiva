import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Check, Cloud, Cpu, Loader2, RotateCcw, Save, Server, Sparkles } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Agent } from '../data/teamApi';
import { AgentModel, ModelChoice, ModelOrigin, fetchAgentModel, saveAgentModel } from '../data/modelApi';
import { chipClass, primaryClass, useAgentsI18n } from '../scope';

type Source = 'default' | ModelOrigin;

const SOURCES: readonly { readonly id: Source; readonly icon: React.ReactNode }[] = [
  { id: 'default', icon: <Sparkles className="h-4 w-4" aria-hidden="true" /> },
  { id: 'local', icon: <Cpu className="h-4 w-4" aria-hidden="true" /> },
  { id: 'server', icon: <Server className="h-4 w-4" aria-hidden="true" /> },
  { id: 'cloud', icon: <Cloud className="h-4 w-4" aria-hidden="true" /> },
];

export const ModelTab: React.FC<{ readonly agent: Agent }> = ({ agent }) => {
  const { t } = useAgentsI18n();
  const [state, setState] = useState<AgentModel | null>(null);
  const [failed, setFailed] = useState(false);
  const [source, setSource] = useState<Source>('default');
  const [ref, setRef] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const load = useCallback(
    (signal?: AbortSignal) => {
      fetchAgentModel(agent.id, signal)
        .then((next) => {
          setState(next);
          setRef(next.ref);
          setSource(next.ref ? (next.pool.find((item) => item.ref === next.ref)?.origin ?? 'cloud') : 'default');
          setFailed(false);
        })
        .catch((cause: unknown) => {
          if (!signal?.aborted) {
            setFailed(true);
            reportError('agent_model_failed', cause);
          }
        });
    },
    [agent.id],
  );

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const options = useMemo(() => (state && source !== 'default' ? state.pool.filter((item) => item.origin === source) : []), [state, source]);

  if (failed) return <p className="text-sm text-rose-700">{t('model_unavailable')}</p>;
  if (!state) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-600" role="status">
        <Loader2 className="h-4 w-4 animate-spin text-cyan-700" aria-hidden="true" />
        {t('loading')}
      </div>
    );
  }

  const dirty = source === 'default' ? state.ref !== '' : ref !== state.ref;
  const canSave = !saving && (source === 'default' ? dirty : ref !== '' && dirty);

  const commit = async (target: string) => {
    setSaving(true);
    setSaved(false);
    try {
      await saveAgentModel(state.component, target, target ? 'first' : 'inherit');
      setSaved(true);
      load();
    } catch (cause) {
      reportError('agent_model_failed', cause);
    } finally {
      setSaving(false);
    }
  };

  const describe = (item: ModelChoice) => `${item.model} · ${item.provider}`;
  const current = state.active[0];

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-2xl border border-cyan-300 bg-cyan-50 p-3 text-sm text-slate-800">
        <p className="text-xs uppercase tracking-wide text-cyan-800">{t('model_in_use')}</p>
        <p className="mt-1 font-mono text-sm text-slate-950">{current ? describe(current) : t('model_none')}</p>
        <p className="mt-1 text-xs text-slate-600">{t(state.ref ? 'model_custom_hint' : 'model_default_hint')}</p>
      </div>
      <div role="radiogroup" aria-label={t('model_source')} className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {SOURCES.map((item) => (
          <button
            key={item.id}
            type="button"
            role="radio"
            aria-checked={source === item.id}
            onClick={() => {
              setSource(item.id);
              setSaved(false);
              if (item.id === 'default') setRef('');
              else if (!state.pool.some((entry) => entry.ref === ref && entry.origin === item.id)) setRef('');
            }}
            className={`flex flex-col items-start gap-1 rounded-xl border p-3 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
              source === item.id ? 'border-cyan-300 bg-cyan-50 text-slate-950' : 'border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300'
            }`}
          >
            <span className="flex items-center gap-2 text-sm font-semibold">
              {item.icon}
              {t(`model_source_${item.id}`)}
            </span>
            <span className="text-xs text-slate-600">{t(`model_source_${item.id}_hint`)}</span>
          </button>
        ))}
      </div>
      {source !== 'default' && (
        <div className="flex flex-col gap-2" role="radiogroup" aria-label={t('model_pick')}>
          {options.length === 0 ? (
            <p className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">{t(`model_empty_${source}`)}</p>
          ) : (
            options.map((item) => (
              <button
                key={item.ref}
                type="button"
                role="radio"
                aria-checked={ref === item.ref}
                disabled={!item.available}
                onClick={() => {
                  setRef(item.ref);
                  setSaved(false);
                }}
                className={`flex items-center justify-between gap-3 rounded-xl border px-3 py-2 text-left text-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 disabled:opacity-40 ${
                  ref === item.ref ? 'border-cyan-300 bg-cyan-50 text-slate-950' : 'border-slate-200 bg-slate-50 text-slate-800 hover:border-slate-300'
                }`}
              >
                <span className="min-w-0">
                  <span className="block truncate font-mono text-sm">{item.model}</span>
                  <span className="block truncate text-xs text-slate-500">{item.provider}</span>
                </span>
                {ref === item.ref && <Check className="h-4 w-4 shrink-0 text-cyan-700" aria-hidden="true" />}
              </button>
            ))
          )}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" disabled={!canSave} onClick={() => void commit(source === 'default' ? '' : ref)} className={primaryClass}>
          {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="h-4 w-4" aria-hidden="true" />}
          {t('model_save')}
        </button>
        {state.ref !== '' && (
          <button type="button" disabled={saving} onClick={() => void commit('')} className={`${chipClass} border-slate-300 text-slate-800 hover:border-slate-400`}>
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            {t('model_reset')}
          </button>
        )}
        {saved && (
          <span className="text-xs text-emerald-700" role="status">
            {t('model_saved')}
          </span>
        )}
      </div>
    </div>
  );
};
