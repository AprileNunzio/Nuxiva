import React from 'react';
import { Wrench } from 'lucide-react';
import { Btn, Panel, Pill, panelClass } from '../../shared/kit';
import { SettingsEditor } from '../../shared/SettingsEditor';
import { setMode } from '../../shared/featureApi';
import { useAction } from '../../shared/useResource';
import type { FeatureRow } from '../../shared/featureTypes';

interface AgentSectionProps {
  readonly feature: FeatureRow;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly onChanged: () => void;
}

export const AgentSection: React.FC<AgentSectionProps> = ({ feature, t, onChanged }) => {
  const { busy, run } = useAction(onChanged);
  const enabled = feature.state.enabled;

  return (
    <div className="flex flex-col gap-4">
      <Panel title={t('agent_title')} icon={<Wrench className="h-4 w-4 text-blue-700" aria-hidden="true" />} actions={<Pill tone={enabled ? 'emerald' : 'slate'}>{enabled ? t('on') : t('off')}</Pill>}>
        <p className="mb-4 text-sm text-slate-600">{t('agent_intro')}</p>
        <label className="flex flex-wrap items-center gap-3 text-xs font-semibold text-slate-600">
          {t('mode')}
          <select
            className="rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900"
            disabled={busy}
            value={feature.state.mode}
            onChange={(event) => void run(() => setMode(feature.id, event.target.value), 'features_mode_failed')}
          >
            <option value="auto">{t('mode_auto')}</option>
            <option value="1">{t('mode_on')}</option>
            <option value="0">{t('mode_off')}</option>
          </select>
        </label>
        <div className="mt-4">
          <SettingsEditor key={feature.id} feature={feature} busy={busy} t={t} run={run} />
        </div>
      </Panel>
      <section className={panelClass} aria-label={t('agent_capabilities')}>
        <h2 className="mb-3 text-sm font-bold text-slate-900">{t('agent_capabilities')}</h2>
        <ul className="grid gap-2 text-xs text-slate-700 lg:grid-cols-2">
          {feature.capabilities.map((capability) => (
            <li key={capability} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
              {capability}
            </li>
          ))}
        </ul>
        <div className="mt-3">
          <Btn tone="slate" onClick={onChanged}>
            {t('refresh')}
          </Btn>
        </div>
      </section>
    </div>
  );
};
