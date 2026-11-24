import React, { useEffect } from 'react';
import { AppViewFrame } from '../shared/kit';
import { DatasetsTab } from './DatasetsTab';
import { ModelsTab } from './ModelsTab';
import { ResultsTab } from './ResultsTab';
import { RunsTab } from './RunsTab';
import { useLab } from './useLab';

export function View() {
  const model = useLab();
  const { os, runs, runsResource, t } = model;
  useEffect(() => os.setStatus({ itemCount: runs.length, connected: !runsResource.error }), [runs.length, runsResource.error, os.setStatus]);
  return (
    <AppViewFrame footer={<small className="text-xs text-on-surface-variant">{t('scope_hint')}</small>} sections={{
      runs: <RunsTab model={model} />,
      datasets: <DatasetsTab model={model} />,
      models: <ModelsTab model={model} />,
      results: <ResultsTab model={model} />,
    }} />
  );
}
