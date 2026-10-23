import React, { useState } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Loading, OSFilterTabs, Stat, StatRow, Unreachable } from '../shared/kit';
import { useResource } from '../shared/useResource';
import { catalogUrl } from './api';
import { CatalogTab } from './components/CatalogTab';
import { CreateTab } from './components/CreateTab';
import { Catalog } from './types';

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/algorithms');
  const { data, error, loading, reload } = useResource<Catalog>(catalogUrl, 20000);
  const [tab, setTab] = useState('catalog');

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const skills = data.entries.filter((entry) => entry.kind === 'skill');
  const uses = skills.reduce((sum, entry) => sum + (entry.uses ?? 0), 0);

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={reload}>
      <StatRow>
        <Stat label={t('stat_total')} value={data.entries.length} />
        <Stat label={t('stat_skills')} value={data.counts.skill} tone="purple" />
        <Stat label={t('stat_tools')} value={data.counts.tool} tone="amber" />
        <Stat label={t('stat_connectors')} value={data.counts.connector} />
        <Stat label={t('stat_uses')} value={uses} tone="emerald" />
        <Stat label={t('stat_errors')} value={data.errors.length} tone={data.errors.length ? 'rose' : 'slate'} />
      </StatRow>
      <OSFilterTabs
        ariaLabel={t('title')}
        selected={tab}
        onSelect={setTab}
        options={[
          { id: 'catalog', label: t('tab_catalog') },
          { id: 'create', label: t('tab_create') }
        ]}
      />
      {tab === 'catalog' ? (
        <CatalogTab catalog={data} t={t} onChanged={reload} />
      ) : (
        <CreateTab
          categories={data.categories}
          canGenerate={data.generate}
          t={t}
          onCreated={() => {
            reload();
            setTab('catalog');
          }}
        />
      )}
    </AppFrame>
  );
};

export default View;
