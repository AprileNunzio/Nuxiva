import React from 'react';
import { ShieldCheck } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Loading, Panel, Stat, StatRow, Unreachable } from '../shared/kit';
import { SettingsEditor } from '../shared/SettingsEditor';
import { FeaturesOverview } from '../shared/featureTypes';
import { useAction, useResource } from '../shared/useResource';
import { AccessPanel } from './components/AccessPanel';
import { FoldersPanel } from './components/FoldersPanel';
import { SessionsPanel } from './components/SessionsPanel';
import { SharesOverview } from './types';

export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('core_apps/shares');
  const shares = useResource<SharesOverview>('/api/shares', 10000);
  const features = useResource<FeaturesOverview>(`/api/features?lang=${encodeURIComponent(lang)}`, 30000);
  const reload = () => {
    shares.reload();
    features.reload();
  };
  const { busy, run } = useAction(reload);
  const feature = features.data?.features.find((item) => item.id === 'shares');

  if (shares.loading && !shares.data) {
    return <Loading label={t('loading')} />;
  }
  if (!shares.data) {
    return <Unreachable label={t(shares.error ? 'unreachable' : 'loading')} />;
  }
  const data = shares.data;

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={reload}>
      <StatRow>
        <Stat label={t('stat_state')} value={data.active === 'active' ? t('service_on') : t('service_off')} tone={data.active === 'active' ? 'emerald' : 'rose'} />
        <Stat label={t('stat_sessions')} value={data.sessions.length} tone="purple" />
        <Stat label={t('stat_protocol')} value={data.settings.protocol.replace('_', '.')} />
        <Stat label={t('stat_access')} value={data.settings.readonly ? t('readonly') : t('readwrite')} tone={data.settings.readonly ? 'amber' : 'cyan'} />
      </StatRow>
      <AccessPanel data={data} t={t} onChanged={reload} />
      <div className="grid gap-4 lg:grid-cols-2">
        <SessionsPanel sessions={data.sessions} t={t} />
        <FoldersPanel folders={data.folders} root={data.root} t={t} />
      </div>
      {feature ? (
        <Panel title={t('settings_title')} icon={<ShieldCheck className="h-4 w-4 text-emerald-700" aria-hidden="true" />}>
          <p className="mb-4 text-xs text-slate-600">{t('settings_hint')}</p>
          <SettingsEditor key={feature.id} feature={feature} busy={busy} t={t} run={run} />
        </Panel>
      ) : null}
    </AppFrame>
  );
};

export default View;
