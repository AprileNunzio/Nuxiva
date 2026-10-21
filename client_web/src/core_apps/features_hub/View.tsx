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
import { SystemSettingsView } from './components/SystemSettingsView';

export function View() {
  const { openApp } = useOSApp();
  const { t, lang } = useScopedI18n('core_apps/features_hub');
  const [viewMode, setViewMode] = useState<'catalog' | 'settings'>('catalog');
  const { data, error, loading, reload } = useResource<FeaturesOverview>(overviewUrl(lang), 15000);

  const findApp = (id: string) =>
    appRegistry.find((app) => (app.id === id || app.featureIds?.includes(id)) && app.target !== 'node');

  const isExcludedFromHub = (id: string) => isApplication({ id }) || id === 'applications';

  if (!data && viewMode === 'catalog') {
    return <ApplicationLayout sections={{}} loading={loading} error={error ? t('unreachable') : undefined} onRetry={reload} />;
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-slate-950">
      <div className="flex shrink-0 items-center justify-between border-b border-slate-800/80 bg-slate-950/80 px-4 py-2 backdrop-blur-md">
        <div className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/90 p-1">
          <button
            type="button"
            onClick={() => setViewMode('catalog')}
            className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              viewMode === 'catalog'
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Grid className="h-3.5 w-3.5" />
            <span>{t('tab_catalog')}</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode('settings')}
            className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              viewMode === 'settings'
                ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-md shadow-emerald-500/20'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sliders className="h-3.5 w-3.5" />
            <span>{t('tab_settings')}</span>
          </button>
        </div>

        {viewMode === 'catalog' && (
          <button
            type="button"
            onClick={() => setViewMode('settings')}
            className="flex items-center gap-1.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-300 transition hover:bg-emerald-500/20"
          >
            <Sliders className="h-3.5 w-3.5" />
            <span>{t('open_settings_shortcut')}</span>
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {viewMode === 'settings' ? (
          <SystemSettingsView t={t} lang={lang} onBack={() => setViewMode('catalog')} />
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
              .filter((f) => !isExcludedFromHub(f.id))
              .map((feature) => ({
                id: feature.id,
                label: feature.name,
                description: feature.description,
                category: feature.category,
                active: feature.state.enabled,
                icon: feature.icon_url || findApp(feature.id)?.iconUrl,
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
