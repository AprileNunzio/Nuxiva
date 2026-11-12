import React from 'react';
import { OctagonX, Siren } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { FeaturePanel } from '../shared/FeaturePanel';
import { AppFrame, Btn, Loading, Panel, Pill, Stat, StatRow, Unreachable } from '../shared/kit';
import { useFeature } from '../shared/useFeature';
import { useAction, useResource } from '../shared/useResource';
import { stopAlert, testAlert } from './api';
import { RedAlertStatus } from './types';

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/emergency');
  const status = useResource<RedAlertStatus>('/api/redalert', 2000);
  const settings = useFeature('redalert');
  const reloadAll = () => {
    status.reload();
    settings.reload();
  };
  const { busy, run } = useAction(reloadAll);

  if (status.loading && !status.data) {
    return <Loading label={t('loading')} />;
  }
  if (!status.data) {
    return <Unreachable label={t(status.error ? 'unreachable' : 'loading')} />;
  }
  const { active, enabled, message, seconds } = status.data;

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={reloadAll}>
      <StatRow>
        <Stat label={t('stat_state')} value={active ? t('state_active') : t('state_idle')} tone={active ? 'rose' : 'emerald'} />
        <Stat label={t('stat_enabled')} value={enabled ? t('yes') : t('no')} tone={enabled ? 'emerald' : 'slate'} />
        <Stat label={t('stat_duration')} value={`${seconds} s`} />
      </StatRow>
      <Panel title={t('control')} icon={<Siren className="h-4 w-4 text-rose-700" aria-hidden="true" />}>
        {active ? (
          <div className="mb-3 flex flex-wrap items-center gap-2" role="alert">
            <Pill tone="rose">{t('state_active')}</Pill>
            <span className="text-sm text-slate-800">{message}</span>
          </div>
        ) : (
          <p className="mb-3 text-sm text-slate-600">{t('idle_hint')}</p>
        )}
        <div className="flex flex-wrap gap-2">
          <Btn tone="amber" busy={busy} disabled={!enabled || active} onClick={() => void run(testAlert, 'emergency_test_failed')}>
            {t('test')}
          </Btn>
          <Btn tone="rose" busy={busy} disabled={!active} onClick={() => void run(stopAlert, 'emergency_stop_failed')}>
            <OctagonX className="h-3.5 w-3.5" aria-hidden="true" />
            {t('stop')}
          </Btn>
        </div>
      </Panel>
      {settings.feature ? <FeaturePanel feature={settings.feature} busy={busy} t={t} run={run} /> : null}
    </AppFrame>
  );
};

export default View;
