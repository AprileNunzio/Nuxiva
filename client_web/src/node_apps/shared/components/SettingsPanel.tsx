import React from 'react';
import { Loader2, RotateCcw, Save } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { SettingSpec } from '../data/schema';
import { NodeSettingsState } from '../hooks/useNodeSettings';
import { Panel } from './ModuleFrame';

type Translate = (key: string, params?: Record<string, string | number>) => string;

interface SettingsPanelProps {
  readonly title: string;
  readonly specs: readonly SettingSpec[];
  readonly state: NodeSettingsState;
  readonly t: Translate;
}

const inputBase = 'rounded-lg border border-slate-700 bg-slate-950 text-sm text-white focus:border-cyan-400 focus:outline-none';

const Field: React.FC<{ readonly spec: SettingSpec; readonly state: NodeSettingsState; readonly t: Translate }> = ({ spec, state, t }) => {
  const shared = useScopedI18n('node_apps/shared');
  const value = state.values[spec.key];
  const label = t(`setting_${spec.key}`);
  const id = `setting-${spec.key}`;
  return (
    <div className="flex flex-col gap-1.5 rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2.5">
      <div className="flex items-center justify-between gap-3">
        <label htmlFor={id} className="text-sm font-medium text-slate-100">
          {label}
          {state.inherited.has(spec.key) && (
            <span className="ml-2 rounded-full border border-slate-700 px-1.5 py-0.5 text-[10px] text-slate-400">{shared.t('inherited')}</span>
          )}
        </label>
        {spec.kind === 'toggle' && (
          <input
            id={id}
            type="checkbox"
            role="switch"
            checked={Boolean(value)}
            onChange={(event) => state.change(spec.key, event.target.checked)}
            className="h-5 w-9 cursor-pointer accent-cyan-400"
          />
        )}
        {spec.kind === 'range' && (
          <span className="font-mono text-xs text-cyan-200">
            {String(value)}
            {spec.unit ?? ''}
          </span>
        )}
        {spec.kind === 'choice' && (
          <select
            id={id}
            value={String(value)}
            onChange={(event) => spec.options.includes(event.target.value) && state.change(spec.key, event.target.value)}
            className={`${inputBase} px-2 py-1.5`}
          >
            {spec.options.map((option) => (
              <option key={option} value={option}>
                {t(`option_${spec.key}_${option}`)}
              </option>
            ))}
          </select>
        )}
      </div>
      {spec.kind === 'range' && (
        <input
          id={id}
          type="range"
          min={spec.min}
          max={spec.max}
          step={spec.step}
          value={Number(value)}
          onChange={(event) => state.change(spec.key, Number(event.target.value))}
          className="w-full cursor-pointer accent-cyan-400"
          aria-valuetext={`${value}${spec.unit ?? ''}`}
        />
      )}
      <p className="text-xs text-slate-500">{t(`setting_${spec.key}_hint`)}</p>
    </div>
  );
};

export const SettingsPanel: React.FC<SettingsPanelProps> = ({ title, specs, state, t }) => {
  const shared = useScopedI18n('node_apps/shared');
  if (state.loading) {
    return (
      <Panel title={title}>
        <Loader2 className="h-5 w-5 animate-spin text-cyan-300" aria-label={shared.t('loading')} />
      </Panel>
    );
  }
  if (state.unavailable) {
    return (
      <Panel title={title}>
        <p className="text-sm text-slate-500">{shared.t('settings_unavailable')}</p>
      </Panel>
    );
  }
  return (
    <Panel
      title={title}
      action={
        state.dirty ? (
          <button
            type="button"
            onClick={state.reset}
            className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-400 transition hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            {shared.t('reset')}
          </button>
        ) : undefined
      }
    >
      <div className="flex flex-col gap-2">
        {specs.map((spec) => (
          <Field key={spec.key} spec={spec} state={state} t={t} />
        ))}
        <button
          type="button"
          onClick={() => void state.save()}
          disabled={!state.dirty || state.saving}
          className="mt-1 flex items-center justify-center gap-2 rounded-xl border border-cyan-400/40 bg-cyan-400/10 px-4 py-2.5 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/20 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          {state.saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="h-4 w-4" aria-hidden="true" />}
          {shared.t(state.saved && !state.dirty ? 'saved' : 'save')}
        </button>
      </div>
    </Panel>
  );
};
