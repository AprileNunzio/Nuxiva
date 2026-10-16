import React, { useState } from 'react';
import { RefreshCw, Search } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, List, Loading, Panel, Stat, StatRow, Unreachable, inputClass } from '../shared/kit';
import { useAction, useResource } from '../shared/useResource';
import { rescan } from '../shared/featureApi';
import { FeatureCard } from './components/FeatureCard';
import { FeaturesOverview } from '../shared/featureTypes';

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/features_hub');
  const { data, error, loading, reload } = useResource<FeaturesOverview>('/api/features', 15000);
  const { busy, run } = useAction(reload);
  const [filter, setFilter] = useState('');
  const [category, setCategory] = useState('');

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const needle = filter.trim().toLowerCase();
  const rows = data.features.filter(
    (item) => (!category || item.category === category) && (!needle || `${item.name} ${item.description}`.toLowerCase().includes(needle)),
  );
  const groups = Object.entries(data.categories)
    .map(([key, label]) => ({ key, label, items: rows.filter((item) => item.category === key) }))
    .filter((group) => group.items.length > 0);

  return (
    <AppFrame
      title={t('title')}
      description={t('description')}
      onReload={reload}
      actions={
        <Btn busy={busy} onClick={() => void run(rescan, 'features_rescan_failed')}>
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          {t('rescan')}
        </Btn>
      }
    >
      <StatRow>
        <Stat label={t('stat_total')} value={data.features.length} />
        <Stat label={t('stat_running')} value={data.features.filter((item) => item.state.enabled).length} tone="emerald" />
        <Stat label={t('stat_stopped')} value={data.features.filter((item) => !item.state.enabled).length} tone="slate" />
        <Stat label={t('stat_errors')} value={data.errors.length} tone={data.errors.length ? 'rose' : 'slate'} />
      </StatRow>
      <div className="grid gap-2 sm:grid-cols-3">
        <div className="relative sm:col-span-2">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
          <input className={`${inputClass} pl-9`} value={filter} onChange={(event) => setFilter(event.target.value)} placeholder={t('search')} aria-label={t('search')} />
        </div>
        <select className={inputClass} value={category} onChange={(event) => setCategory(event.target.value)} aria-label={t('category')}>
          <option value="">{t('all_categories')}</option>
          {Object.entries(data.categories).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </div>
      {groups.length === 0 ? (
        <Empty>{t('empty')}</Empty>
      ) : (
        groups.map((group) => (
          <Panel key={group.key} title={`${group.label} (${group.items.length})`}>
            <List>
              {group.items.map((feature) => (
                <FeatureCard key={feature.id} feature={feature} busy={busy} t={t} run={run} />
              ))}
            </List>
          </Panel>
        ))
      )}
    </AppFrame>
  );
};

export default View;
