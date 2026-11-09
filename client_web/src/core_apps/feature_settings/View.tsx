import React, { useEffect } from 'react';
import { ApplicationLayout } from '../../app_shell/window_manager/ApplicationLayout';
import { useOSApp } from '../../app_shell/window_manager/WindowContext';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { useResource, useAction } from '../shared/useResource';
import { FeaturesOverview } from '../shared/featureTypes';
import { setMode } from '../shared/featureApi';
import { SettingsEditor } from '../shared/SettingsEditor';
import { SetupGuide } from '../shared/SetupGuide';
import { inputClass, Pill } from '../shared/kit';
import { DesktopSettingsFields } from './desktop/DesktopSettingsFields';

export function View() {
  const os = useOSApp();
  const { t, lang } = useScopedI18n('core_apps/feature_settings');
  const { data, loading, error, reload } = useResource<FeaturesOverview>(`/api/features?lang=${encodeURIComponent(lang)}`, 15000);
  const { busy, run } = useAction(reload);
  const feature = data?.features.find((item) => item.id === os.instanceKey);
  useEffect(() => { if (feature) os.setTitle(feature.name); }, [os.windowId, feature?.name]);
  if (!feature) {
    return <ApplicationLayout sections={{}} loading={loading} error={t(error ? 'unreachable' : 'empty')} onRetry={reload} />;
  }
  const desktop = feature.id === 'desktop';
  const status = t(feature.state.enabled ? 'running' : 'stopped');
  return (
    <ApplicationLayout sections={{
      settings: (
        <div className="space-y-5">
          <header className={desktop ? 'rounded-3xl bg-primary-container p-4 text-on-primary-container sm:p-6' : undefined}>
            <div className="flex flex-wrap items-center gap-3">
              {desktop && feature.icon_url && <img className="size-12 object-contain" src={feature.icon_url} alt="" />}
              <h1 className="text-xl font-semibold">{feature.name}</h1>
              {desktop && <span role="status"><Pill tone={feature.state.enabled ? 'emerald' : 'slate'}>{status}</Pill></span>}
            </div>
            <p className="mt-2 max-w-3xl text-sm">{feature.description}</p>
          </header>
          <label className="flex flex-wrap items-center gap-3 text-sm font-medium">
            {t('mode')}
            <select
              className={`${inputClass} w-auto max-w-full`}
              disabled={busy}
              value={feature.state.mode}
              onChange={(event) => void run(() => setMode(feature.id, event.target.value), 'features_mode_failed')}
            >
              <option value="auto">{t('mode_auto')}</option>
              <option value="1">{t('mode_on')}</option>
              <option value="0">{t('mode_off')}</option>
            </select>
            {!desktop && <span role="status">{status}</span>}
          </label>
          <SetupGuide guide={feature.guide} />
          <SettingsEditor key={feature.id} feature={feature} busy={busy} t={t} run={run} layout={desktop ? DesktopSettingsFields : undefined} />
        </div>
      ),
      details: (
        <div>
          <h1>{feature.name}</h1>
          <p>{feature.description}</p>
          <ul className="mt-4 space-y-2">{feature.capabilities.map((capability) => <li key={capability}>{capability}</li>)}</ul>
          <p className="mt-4 text-sm text-on-surface-variant">{feature.state.reason}</p>
        </div>
      ),
    }} />
  );
}
