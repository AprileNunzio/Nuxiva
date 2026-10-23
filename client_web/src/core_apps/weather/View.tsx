import React, { useMemo, useState } from 'react';
import { CloudSun, MapPin, SlidersHorizontal } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Empty, Loading, Panel, Unreachable } from '../shared/kit';
import { FeatureRow } from '../shared/featureTypes';
import { SettingsEditor } from '../shared/SettingsEditor';
import { useAction, useResource } from '../shared/useResource';
import { useFeature } from '../shared/useFeature';
import { overviewUrl, parseOverview } from './api';
import { PlaceList } from './components/PlaceList';
import { PlaceSearch } from './components/PlaceSearch';
import { PreviewPanel } from './components/PreviewPanel';

const REFRESH_MS = 60000;

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/weather');
  const [selected, setSelected] = useState('');
  const { data, error, loading, reload } = useResource<unknown>(overviewUrl(selected), REFRESH_MS);
  const { feature, reload: reloadFeature } = useFeature('weather', 0);
  const { busy, run } = useAction(reload);
  const overview = useMemo(() => (data === null ? null : parseOverview(data)), [data]);

  if (loading && !overview) {
    return <Loading label={t('loading')} />;
  }
  if (!overview) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const shown: FeatureRow | null = feature;

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={reload}>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={t('places_title')} icon={<MapPin className="h-4 w-4 text-rose-300" aria-hidden="true" />}>
          <div className="grid gap-4">
            <PlaceSearch t={t} onAdded={reload} />
            <PlaceList places={overview.places} defaultId={overview.defaultId} selected={selected} busy={busy} run={run} onSelect={setSelected} t={t} />
          </div>
        </Panel>
        <Panel title={t('preview_title')} icon={<CloudSun className="h-4 w-4 text-amber-300" aria-hidden="true" />}>
          {overview.preview ? <PreviewPanel preview={overview.preview} t={t} /> : <Empty>{t(overview.error === 'no_location' ? 'preview_no_location' : 'preview_unavailable')}</Empty>}
        </Panel>
        {shown ? (
          <Panel className="lg:col-span-2" title={t('settings_title')} icon={<SlidersHorizontal className="h-4 w-4 text-cyan-300" aria-hidden="true" />}>
            <SettingsEditor
              key={shown.id}
              feature={shown}
              busy={busy}
              t={t}
              run={async (task, code) => {
                const result = await run(task, code);
                reloadFeature();
                return result;
              }}
            />
          </Panel>
        ) : null}
      </div>
    </AppFrame>
  );
};
