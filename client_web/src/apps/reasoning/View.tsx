import React, { useEffect } from 'react';
import { AppViewFrame } from '../shared/kit';
import { OverviewTab } from './OverviewTab';
import { SettingsTab } from './SettingsTab';
import { TracesTab } from './TracesTab';
import { useEngine } from './useEngine';

export function View() {
  const model = useEngine();
  const { os, traces, statusResource, t } = model;
  useEffect(() => os.setStatus({ itemCount: traces.length, connected: !statusResource.error }), [traces.length, statusResource.error, os.setStatus]);
  return (
    <AppViewFrame footer={<small className="text-xs text-on-surface-variant">{t('footer')}</small>} sections={{
      overview: <OverviewTab model={model} />,
      traces: <TracesTab model={model} />,
      settings: <SettingsTab model={model} />,
    }} />
  );
}
