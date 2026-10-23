import React from 'react';
import { Pill, Panel, Row, inputClass } from './kit';
import { setMode } from './featureApi';
import { FeatureRow } from './featureTypes';
import { SettingsEditor } from './SettingsEditor';

interface FeaturePanelProps {
  readonly feature: FeatureRow;
  readonly busy: boolean;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly run: <R>(task: () => Promise<R>, code?: string) => Promise<R | null>;
}

export const FeaturePanel: React.FC<FeaturePanelProps> = ({ feature, busy, t, run }) => (
  <Panel title={t('feature_title')}>
    <Row
      actions={
        <select
          className={`${inputClass} w-40`}
          value={feature.state.mode}
          disabled={busy}
          aria-label={t('mode')}
          onChange={(event) => void run(() => setMode(feature.id, event.target.value), 'features_mode_failed')}
        >
          <option value="auto">{t('mode_auto')}</option>
          <option value="1">{t('mode_on')}</option>
          <option value="0">{t('mode_off')}</option>
        </select>
      }
    >
      <div className="flex flex-wrap items-center gap-2">
        <b>{feature.name}</b>
        <Pill tone={feature.state.enabled ? 'emerald' : 'slate'}>{feature.state.enabled ? t('running') : t('stopped')}</Pill>
      </div>
      <p className="mt-1 text-xs text-slate-500">{feature.state.reason}</p>
    </Row>
    <p className="my-3 text-sm text-slate-700">{feature.description}</p>
    <SettingsEditor feature={feature} busy={busy} t={t} run={run} />
  </Panel>
);
