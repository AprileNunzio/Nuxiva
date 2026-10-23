import React, { FormEvent, useState } from 'react';
import { Brain, Check, Lightbulb, Play, Search, X } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, List, Loading, Panel, Pill, Row, Stat, StatRow, Toggle, Unreachable, inputClass } from '../shared/kit';
import { useAction, useResource } from '../shared/useResource';
import { acceptMention, dropMention, saveSettings, searchMemory, studyNow } from './api';
import { TopicsPanel } from './components/TopicsPanel';
import { StudyHit, StudyOverview, StudySettings } from './types';

const SWITCHES: readonly (keyof StudySettings)[] = ['auto_discover', 'auto_accept', 'web_sources', 'use_in_answers'];

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/study');
  const { data, error, loading, reload } = useResource<StudyOverview>('/api/study', 10000);
  const { busy, run } = useAction(reload);
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState<StudyHit[] | null>(null);

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const search = async (event: FormEvent) => {
    event.preventDefault();
    if (!query.trim()) {
      return;
    }
    const out = await run(() => searchMemory(query.trim()), 'study_search_failed');
    setHits(out ? out.results : null);
  };

  const minutes = Math.round(data.stats.seconds_today / 60);

  return (
    <AppFrame
      title={t('title')}
      description={t('description')}
      onReload={reload}
      actions={
        <>
          <Btn busy={busy} disabled={!data.settings.enabled} onClick={() => void run(studyNow, 'study_now_failed')}>
            <Play className="h-3.5 w-3.5" aria-hidden="true" />
            {t('study_now')}
          </Btn>
          <Toggle checked={data.settings.enabled} disabled={busy} label={t('enabled')} onChange={(value) => void run(() => saveSettings({ enabled: value }), 'study_settings_failed')} />
        </>
      }
    >
      <StatRow>
        <Stat label={t('stat_state')} value={t(`state_${data.status.state}`)} tone={data.status.state === 'studying' ? 'emerald' : 'slate'} />
        <Stat label={t('stat_today')} value={t('minutes', { n: minutes })} />
        <Stat label={t('stat_lessons')} value={data.stats.lessons} tone="purple" />
        <Stat label={t('stat_cells')} value={data.memory.cells} tone="amber" />
      </StatRow>
      <p className="text-xs text-slate-600">
        {data.status.detail}
        {data.status.topic ? ` · ${data.status.topic}` : ''}
      </p>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <TopicsPanel data={data} busy={busy} t={t} run={run} />
        <div className="flex min-w-0 flex-col gap-4">
          <Panel title={t('settings_title')} icon={<Brain className="h-4 w-4 text-cyan-700" aria-hidden="true" />}>
            <List>
              {SWITCHES.map((key) => (
                <Row key={key} actions={<Toggle checked={data.settings[key] === true} disabled={busy} label={t(`setting_${key}`)} onChange={(value) => void run(() => saveSettings({ [key]: value }), 'study_settings_failed')} />}>
                  {t(`setting_${key}`)}
                </Row>
              ))}
              <Row
                actions={
                  <input
                    className={`${inputClass} w-24`}
                    type="number"
                    min={10}
                    max={1440}
                    defaultValue={data.settings.daily_minutes}
                    aria-label={t('setting_daily_minutes')}
                    onBlur={(event) => {
                      const value = Number(event.target.value);
                      if (value >= 10 && value <= 1440 && value !== data.settings.daily_minutes) {
                        void run(() => saveSettings({ daily_minutes: value }), 'study_settings_failed');
                      }
                    }}
                  />
                }
              >
                {t('setting_daily_minutes')}
              </Row>
            </List>
          </Panel>
          <Panel title={t('mentions_title')} icon={<Lightbulb className="h-4 w-4 text-amber-700" aria-hidden="true" />}>
            {data.mentions.length === 0 ? (
              <Empty>{t('mentions_empty')}</Empty>
            ) : (
              <List>
                {data.mentions.map((mention) => (
                  <Row
                    key={mention.key ?? mention.name}
                    actions={
                      mention.key ? (
                        <>
                          <Btn tone="emerald" busy={busy} onClick={() => void run(() => acceptMention(mention.key as string), 'study_mention_failed')} title={t('accept')}>
                            <Check className="h-3.5 w-3.5" aria-hidden="true" />
                          </Btn>
                          <Btn tone="slate" busy={busy} onClick={() => void run(() => dropMention(mention.key as string), 'study_mention_failed')} title={t('dismiss')}>
                            <X className="h-3.5 w-3.5" aria-hidden="true" />
                          </Btn>
                        </>
                      ) : undefined
                    }
                  >
                    <b>{mention.name}</b>
                    <Pill>{t('mentions_count', { n: mention.count ?? 0 })}</Pill>
                  </Row>
                ))}
              </List>
            )}
          </Panel>
        </div>
      </div>
      <Panel title={t('search_title')} icon={<Search className="h-4 w-4 text-emerald-700" aria-hidden="true" />}>
        <form onSubmit={search} className="flex gap-2">
          <input className={inputClass} value={query} maxLength={300} onChange={(event) => setQuery(event.target.value)} placeholder={t('search_placeholder')} aria-label={t('search_placeholder')} />
          <Btn type="submit" busy={busy}>
            {t('search')}
          </Btn>
        </form>
        {hits ? (
          hits.length === 0 ? (
            <div className="mt-3"><Empty>{t('search_empty')}</Empty></div>
          ) : (
            <div className="mt-3">
              <List>
                {hits.map((hit, index) => (
                  <Row key={`${index}-${hit.text.slice(0, 20)}`} actions={<Pill tone="emerald">{Math.round(hit.score * 100)}%</Pill>}>
                    <p className="text-sm">{hit.text}</p>
                    <p className="text-[11px] text-slate-500">{hit.topic_name} · {hit.level}</p>
                  </Row>
                ))}
              </List>
            </div>
          )
        ) : null}
      </Panel>
    </AppFrame>
  );
};

export default View;
