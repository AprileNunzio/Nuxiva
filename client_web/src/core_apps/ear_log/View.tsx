import React, { useEffect, useMemo, useState } from 'react';
import { Mic, SlidersHorizontal, Trash2 } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, List, Loading, Panel, Stat, StatRow, Unreachable } from '../shared/kit';
import { FeatureRow } from '../shared/featureTypes';
import { SettingsEditor } from '../shared/SettingsEditor';
import { useAction, useResource } from '../shared/useResource';
import { useFeature } from '../shared/useFeature';
import { journalUrl, parseJournal, purgeJournal } from './api';
import { EntryCard } from './components/EntryCard';
import { Filters } from './components/Filters';
import { LivePanel } from './components/LivePanel';
import { EarFilters } from './types';

const PAGE = 40;
const REFRESH_MS = 6000;
const SETTING_KEYS = [
  'NUXIVA_EAR_LIVE', 'NUXIVA_EAR_LIVE_SPEAKER', 'NUXIVA_CAPTIONS', 'NUXIVA_CAPTIONS_SCOPE', 'NUXIVA_CAPTIONS_SPEAKER',
  'NUXIVA_CAPTIONS_SIZE', 'NUXIVA_CAPTIONS_POSITION', 'NUXIVA_CAPTIONS_HOLD', 'NUXIVA_EAR_JOURNAL', 'NUXIVA_EAR_JOURNAL_AUDIO',
  'NUXIVA_EAR_JOURNAL_FULL', 'NUXIVA_EAR_JOURNAL_DAYS', 'NUXIVA_EAR_JOURNAL_AUDIO_DAYS', 'NUXIVA_EAR_JOURNAL_MAX_MB',
];

const narrow = (feature: FeatureRow): FeatureRow => ({ ...feature, settings: feature.settings.filter((setting) => SETTING_KEYS.includes(setting.key)) });

export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('core_apps/ear_log');
  const [filters, setFilters] = useState<EarFilters>({ kind: '', verdict: '', speaker: '', query: '', limit: PAGE });
  const [typed, setTyped] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [confirmPurge, setConfirmPurge] = useState(false);
  const { data, error, loading, reload } = useResource<unknown>(journalUrl(filters), REFRESH_MS);
  const { feature, reload: reloadFeature } = useFeature('ear', 0);
  const { busy, run } = useAction(reload);
  const journal = useMemo(() => (data === null ? null : parseJournal(data)), [data]);

  useEffect(() => {
    const timer = window.setTimeout(() => setFilters((state) => (state.query === typed ? state : { ...state, query: typed, limit: PAGE })), 350);
    return () => window.clearTimeout(timer);
  }, [typed]);

  const change = (next: Partial<EarFilters>) => {
    if (next.query !== undefined) {
      setTyped(next.query);
      return;
    }
    setFilters((state) => ({ ...state, ...next, limit: PAGE }));
  };

  const purge = async () => {
    if (!confirmPurge) {
      setConfirmPurge(true);
      return;
    }
    setConfirmPurge(false);
    await run(purgeJournal, 'ear_log_failed');
  };

  if (loading && !journal) {
    return <Loading label={t('loading')} />;
  }
  if (!journal) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

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
        <Stat label={t('stat_total')} value={journal.stats.total} tone="cyan" />
        <Stat label={t('stat_pending')} value={journal.stats.pending} tone="amber" />
        <Stat label={t('stat_wrong')} value={journal.stats.wrong} tone="rose" />
        <Stat label={t('stat_audio')} value={journal.stats.audioMb} tone="purple" />
      </StatRow>
      <div className="mt-4 grid gap-4">
        <Panel title={t('live_title')} icon={<Mic className="h-4 w-4 text-emerald-300" aria-hidden="true" />}>
          <LivePanel live={journal.live} t={t} />
          <p className="mt-2 text-xs text-slate-500">{t('privacy_note')}</p>
        </Panel>
        {showSettings && feature ? (
          <Panel title={t('settings_title')}>
            <SettingsEditor key={feature.id} feature={narrow(feature)} busy={busy} t={t} run={async (task, code) => {
              const result = await run(task, code);
              reloadFeature();
              return result;
            }} />
          </Panel>
        ) : null}
        <Panel
          title={t('journal_title')}
          actions={
            <Btn tone="rose" busy={busy} disabled={journal.stats.total === 0} onClick={() => void purge()}>
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              {t(confirmPurge ? 'purge_confirm' : 'purge')}
            </Btn>
          }
        >
          <Filters filters={{ ...filters, query: typed }} people={journal.people} t={t} onChange={change} />
          {journal.items.length === 0 ? (
            <Empty>{t('empty')}</Empty>
          ) : (
            <List>
              {journal.items.map((entry) => (
                <EntryCard key={entry.id} entry={entry} people={journal.people} busy={busy} lang={lang} t={t} run={run} />
              ))}
            </List>
          )}
          {journal.items.length >= filters.limit && filters.limit < 200 ? (
            <div className="mt-3 flex justify-center">
              <Btn tone="slate" onClick={() => setFilters((state) => ({ ...state, limit: Math.min(200, state.limit + PAGE) }))}>
                {t('more')}
              </Btn>
            </div>
          ) : null}
        </Panel>
      </div>
    </AppFrame>
  );
};

export default View;
