import { useCallback, useState } from 'react';
import { useOSApp } from '../shared/kit';
import { useAction, useResource } from '../shared/useResource';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { brainUrl, datasetsUrl, presetsUrl, profilesUrl, runsUrl, statusUrl } from './api';
import type { BrainInfo, BrainRole, DatasetRow, PresetRow, Profile, Run, Status } from './types';

export function useLab() {
  const os = useOSApp();
  const { t, lang } = useScopedI18n('apps/reason_lab');
  const status = useResource<Status>(statusUrl, 15000);
  const datasets = useResource<{ datasets: DatasetRow[] }>(datasetsUrl);
  const profiles = useResource<{ profiles: Profile[] }>(profilesUrl);
  const runs = useResource<{ runs: Run[] }>(runsUrl, 4000);
  const [brainRole, setBrainRole] = useState<BrainRole>('main');
  const brain = useResource<BrainInfo>(brainUrl(brainRole));
  const presets = useResource<{ presets: PresetRow[] }>(presetsUrl);
  const { busy, run } = useAction();
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [compareRun, setCompareRun] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const openResults = useCallback(
    (id: string) => {
      setSelectedRun(id);
      os.setActiveTab('results');
    },
    [os],
  );
  const time = (seconds: number | null) => (seconds ? new Date(seconds * 1000).toLocaleString(lang) : '-');
  return {
    os, t, lang, status: status.data, statusResource: status, datasets: datasets.data?.datasets ?? [], datasetsResource: datasets,
    profiles: profiles.data?.profiles ?? [], profilesResource: profiles, runs: runs.data?.runs ?? [], runsResource: runs,
    brain: brain.dataUrl === brainUrl(brainRole) ? brain.data : null, brainRole, setBrainRole, presets: presets.data?.presets ?? [],
    busy, run, selectedRun, setSelectedRun, compareRun, setCompareRun, openResults, time, notice, setNotice,
  };
}

export type LabModel = ReturnType<typeof useLab>;
