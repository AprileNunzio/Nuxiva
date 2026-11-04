import React, { useEffect, useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { usePolled } from '../../../../node_apps/shared/hooks/useAction';
import { matches } from '../../core/format';
import { useBrainText, useSectionText } from '../../core/i18n';
import { fetchProviders } from '../../core/providersApi';
import { useBrain } from '../../core/useBrainStore';
import { Card, Empty, FLUID, Loading, SectionHeader, fieldClass } from '../../ui/primitives';
import { ProviderItem } from './ProviderItem';
import { ServersCard } from './ServersCard';

type Filter = 'all' | 'ready';

export const ProvidersSection: React.FC = () => {
  const { t } = useSectionText('providers');
  const base = useBrainText();
  const { version } = useBrain();
  const providers = usePolled(fetchProviders, 'brain_providers_unavailable', true, 0);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<Filter>('all');
  const { refresh } = providers;
  useEffect(() => {
    if (version > 0) refresh();
  }, [version, refresh]);

  const visible = useMemo(
    () => (providers.data ?? []).filter((p) => (filter === 'all' || p.configured) && matches(query, p.name, p.id)),
    [providers.data, filter, query],
  );
  const ready = (providers.data ?? []).filter((p) => p.configured).length;

  return (
    <>
      <SectionHeader title={t('title')} description={t('description')} />
      <Card
        title={t('cloud_title', { ready, total: providers.data?.length ?? 0 })}
        description={t('cloud_hint')}
        flush
      >
        <div className="flex flex-col gap-2 border-b border-slate-100 px-4 py-3 sm:flex-row sm:items-center sm:px-5">
          <label className="relative min-w-0 flex-1">
            <span className="sr-only">{t('search')}</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input value={query} maxLength={60} onChange={(e) => setQuery(e.target.value)} placeholder={t('search')} className={`${fieldClass} pl-9`} />
          </label>
          <div role="tablist" aria-label={t('filter')} className="flex shrink-0 rounded-lg border border-slate-200 bg-slate-100 p-0.5">
            {(['all', 'ready'] as const).map((id) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={filter === id}
                onClick={() => setFilter(id)}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${filter === id ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600 hover:text-slate-900'}`}
              >
                {t(`filter_${id}`)}
              </button>
            ))}
          </div>
        </div>
        {providers.data === null ? (
          <div className="px-5"><Loading label={base.t('loading')} /></div>
        ) : visible.length === 0 ? (
          <div className="p-4"><Empty>{t('empty')}</Empty></div>
        ) : (
          <ul className={`grid items-start ${FLUID.md}`}>
            {visible.map((provider) => (
              <ProviderItem key={provider.id} provider={provider} />
            ))}
          </ul>
        )}
      </Card>
      <ServersCard />
    </>
  );
};
