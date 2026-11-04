import React, { useMemo, useState } from 'react';
import { SlidersHorizontal } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, Field, List, Loading, Panel, Stat, StatRow, Unreachable, inputClass } from '../shared/kit';
import { FeatureRow } from '../shared/featureTypes';
import { SettingsEditor } from '../shared/SettingsEditor';
import { useAction, useResource } from '../shared/useResource';
import { useFeature } from '../shared/useFeature';
import { downloadVoice, parseOverview, removeVoice, saveOrder, setLanguageVoice } from './api';
import { OrderList } from './components/OrderList';
import { VoiceRow } from './components/VoiceRow';
import { usePreview } from './usePreview';
import { VoiceItem } from './types';

const PAGE = 40;
const REFRESH_MS = 4000;
const ENGINES = ['', 'kokoro', 'piper', 'online'] as const;
const SETTING_KEYS = ['NUXIVA_VOICE_SPEED', 'NUXIVA_VOICE_PITCH', 'NUXIVA_VOICE_VOLUME', 'NUXIVA_VOICE_ONLINE', 'NUXIVA_VOICE_AUTO_DOWNLOAD'];

const narrow = (feature: FeatureRow): FeatureRow => ({ ...feature, settings: feature.settings.filter((setting) => SETTING_KEYS.includes(setting.key)) });

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/voice_manager');
  const [lang, setLang] = useState('');
  const [engine, setEngine] = useState('');
  const [query, setQuery] = useState('');
  const [installedOnly, setInstalledOnly] = useState(false);
  const [limit, setLimit] = useState(PAGE);
  const [showSettings, setShowSettings] = useState(false);
  const { data, error, loading, reload } = useResource<unknown>('/api/voices', REFRESH_MS);
  const { feature, reload: reloadFeature } = useFeature('voices', 0);
  const { busy, run } = useAction(reload);
  const preview = usePreview();
  const overview = useMemo(() => (data === null ? null : parseOverview(data)), [data]);

  const filtered = useMemo(() => {
    if (!overview) return [];
    const needle = query.trim().toLowerCase();
    return overview.voices.filter(
      (voice) =>
        (!lang || voice.lang === lang) &&
        (!engine || voice.engine === engine) &&
        (!installedOnly || voice.installed) &&
        (!needle || `${voice.name} ${voice.id} ${voice.locale}`.toLowerCase().includes(needle)),
    );
  }, [overview, lang, engine, installedOnly, query]);

  if (loading && !overview) return <Loading label={t('loading')} />;
  if (!overview) return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;

  const ids = overview.order.map((voice) => voice.id);
  const installed = overview.voices.filter((voice) => voice.installed).length;
  const prefer = (voice: VoiceItem) => void run(() => setLanguageVoice(voice.lang, voice.preferred ? '' : voice.id), 'voice_manager_failed');

  return (
    <AppFrame
      title={t('title')}
      description={t('description')}
      onReload={reload}
      actions={
        <Btn tone="slate" onClick={() => setShowSettings((value) => !value)}>
          <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
          {t(showSettings ? 'settings_close' : 'settings_open')}
        </Btn>
      }
    >
      <StatRow>
        <Stat label={t('stat_total')} value={overview.voices.length} tone="cyan" />
        <Stat label={t('stat_installed')} value={installed} tone="emerald" />
        <Stat label={t('stat_languages')} value={Object.keys(overview.langs).length} tone="purple" />
        <Stat label={t('stat_preferred')} value={Object.keys(overview.langPrefs).length} tone="amber" />
      </StatRow>
      <div className="mt-4 grid gap-4">
        {showSettings && feature ? (
          <Panel title={t('settings_title')}>
            <SettingsEditor
              key={feature.id}
              feature={narrow(feature)}
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
        <Panel title={t('order_title')}>
          <p className="mb-3 text-xs text-slate-500">{t('order_hint')}</p>
          <OrderList
            order={overview.order}
            fallback={overview.fallback}
            busy={busy}
            playing={preview.playing}
            t={t}
            onChange={(next) => void run(() => saveOrder(next), 'voice_manager_failed')}
            onPlay={(id) => void preview.play(id)}
          />
        </Panel>
        <Panel title={t('library_title')}>
          <div className="mb-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Field label={t('filter_language')}>
              <select className={inputClass} value={lang} onChange={(event) => { setLang(event.target.value); setLimit(PAGE); }}>
                <option value="">{t('all')}</option>
                {Object.entries(overview.langs).map(([code, label]) => (
                  <option key={code} value={code}>{label}</option>
                ))}
              </select>
            </Field>
            <Field label={t('filter_engine')}>
              <select className={inputClass} value={engine} onChange={(event) => { setEngine(event.target.value); setLimit(PAGE); }}>
                {ENGINES.map((value) => (
                  <option key={value} value={value}>{value ? t(`engine_${value}`) : t('all')}</option>
                ))}
              </select>
            </Field>
            <Field label={t('search')}>
              <input className={inputClass} value={query} maxLength={60} onChange={(event) => { setQuery(event.target.value); setLimit(PAGE); }} />
            </Field>
            <label className="flex items-end gap-2 pb-2 text-xs font-semibold text-slate-600">
              <input type="checkbox" checked={installedOnly} onChange={(event) => setInstalledOnly(event.target.checked)} />
              {t('installed_only')}
            </label>
          </div>
          {filtered.length === 0 ? (
            <Empty>{t('empty')}</Empty>
          ) : (
            <List>
              {filtered.slice(0, limit).map((voice) => (
                <VoiceRow
                  key={voice.id}
                  voice={voice}
                  inOrder={ids.includes(voice.id)}
                  busy={busy}
                  playing={preview.playing === voice.id}
                  t={t}
                  onPlay={(id) => void preview.play(id)}
                  onDownload={(id) => void run(() => downloadVoice(id), 'voice_manager_failed')}
                  onRemove={(id) => void run(() => removeVoice(id), 'voice_manager_failed')}
                  onAdd={(id) => void run(() => saveOrder([...ids, id]), 'voice_manager_failed')}
                  onPrefer={prefer}
                />
              ))}
            </List>
          )}
          {filtered.length > limit ? (
            <div className="mt-3 flex justify-center">
              <Btn tone="slate" onClick={() => setLimit((value) => value + PAGE)}>{t('more', { count: filtered.length - limit })}</Btn>
            </div>
          ) : null}
        </Panel>
      </div>
    </AppFrame>
  );
};

export default View;
