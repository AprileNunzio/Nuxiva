import React, { useState } from 'react';
import { Sliders, Grid } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { ApplicationLayout } from '../../app_shell/window_manager/ApplicationLayout';
import { ApplicationCatalog } from '../../app_shell/window_manager/ApplicationCatalog';
import { appRegistry } from '../../app_shell/window_manager/registry';
import { useOSApp } from '../../app_shell/window_manager/WindowContext';
import { useResource } from '../shared/useResource';
import { FeaturesOverview } from '../shared/featureTypes';
import { overviewUrl } from './api';
import { isApplication } from '../../app_shell/window_manager/app_scanner';
import { SystemSettingsTabs } from './components/SystemSettingsTabs';

export function View() {
  const { openApp } = useOSApp();
  const { t, lang } = useScopedI18n('core_apps/features_hub');
  const [viewMode, setViewMode] = useState<'catalog' | 'settings'>('catalog');
  const { data, error, loading, reload } = useResource<FeaturesOverview>(overviewUrl(lang), 15000);

  const findApp = (id: string) =>
    appRegistry.find((app) => (app.id === id || app.featureIds?.includes(id)) && app.target !== 'node');

  const isFolded = (id: string) => appRegistry.some((app) => app.id !== id && app.featureIds?.includes(id));

  const isExcludedFromHub = (id: string) => isApplication({ id }) || id === 'applications';

  if (!data && viewMode === 'catalog') {
    return <ApplicationLayout sections={{}} loading={loading} error={error ? t('unreachable') : undefined} onRetry={reload} />;
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-surface text-on-surface">
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 px-4 py-3">
        <div role="tablist" aria-label={t('tab_catalog')} className="flex items-center gap-1 rounded-full bg-surface-container-high p-1">
          {([
            ['catalog', Grid, t('tab_catalog')],
            ['settings', Sliders, t('tab_settings')],
          ] as const).map(([mode, Icon, label]) => (
            <button
              key={mode}
              type="button"
              role="tab"
              aria-selected={viewMode === mode}
              onClick={() => setViewMode(mode)}
              className={`md-state flex items-center gap-2 rounded-full border-0 px-4 py-1.5 text-xs font-semibold ${
                viewMode === mode ? 'bg-primary text-on-primary shadow-[var(--md-elevation-1)]' : 'bg-transparent text-on-surface-variant'
              }`}
            >
              <Icon className={`h-3.5 w-3.5 ${viewMode === mode ? 'md-pop' : ''}`} aria-hidden="true" />
              <span>{label}</span>
            </button>
          ))}
        </div>

        {viewMode === 'catalog' && (
          <button
            type="button"
            onClick={() => setViewMode('settings')}
            className="md-state flex items-center gap-1.5 rounded-full border-0 bg-tertiary-container px-4 py-1.5 text-xs font-semibold text-on-tertiary-container"
          >
            <Sliders className="h-3.5 w-3.5" aria-hidden="true" />
            <span>{t('open_settings_shortcut')}</span>
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {viewMode === 'settings' ? (
          <SystemSettingsTabs t={t} lang={lang} onBack={() => setViewMode('catalog')} />
        ) : data ? (
          <ApplicationCatalog
            lang={lang}
            labels={{
              search: t('search'),
              clearSearch: t('clear_search'),
              categories: t('navigation'),
              all: t('all_categories'),
              empty: t('empty'),
              emptyHint: t('empty_hint'),
              stateFilter: t('state_filter'),
              allStates: t('all_states'),
              on: t('running'),
              off: t('stopped'),
              reset: t('reset_filters'),
              pinToDesktop: t('pin_to_desktop'),
              unpinFromDesktop: t('unpin_from_desktop'),
              open: t('open_app')
            }}
            categories={Object.fromEntries(
              Object.entries(data.categories).map(([id, label]) => [
                id,
                t(`category_${id}`) === `category_${id}` ? label : t(`category_${id}`)
              ])
            )}
            items={data.features
              .filter((f) => !isExcludedFromHub(f.id) && !isFolded(f.id) && (f.surface ?? 'hub') === 'hub')
              .map((feature) => ({
                id: feature.id,
                label: feature.name,
                description: feature.description,
                category: feature.category,
                active: feature.state.enabled,
                icon: findApp(feature.id)?.iconUrl || feature.icon_url || undefined,
                symbol: feature.icon
              }))}
            onOpen={(id) =>
              openApp(findApp(id) ? { appId: findApp(id)!.id } : { appId: 'feature_settings', instanceKey: id })
            }
          />
        ) : null}
      </div>
    </div>
  );
}

export default View;
