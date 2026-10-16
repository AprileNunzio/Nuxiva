import React from 'react';
import { History, Music2 } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, List, Loading, Panel, Pill, Row, Stat, StatRow, Toggle, Unreachable, formatTime } from '../shared/kit';
import { useAction, useResource } from '../shared/useResource';
import { setRecognition } from './api';
import { MusicOverview } from './types';

export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('core_apps/music');
  const { data, error, loading, reload } = useResource<MusicOverview>('/api/music', 8000);
  const { busy, run } = useAction(reload);

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const playing = data.now_playing;
  const hasTrack = Boolean(playing && playing.title);

  return (
    <AppFrame
      title={t('title')}
      description={t('description')}
      onReload={reload}
      actions={<Toggle checked={data.enabled} disabled={busy} onChange={(value) => void run(() => setRecognition(value), 'music_toggle_failed')} label={t('recognition')} />}
    >
      <StatRow>
        <Stat label={t('stat_recognition')} value={data.enabled ? t('on') : t('off')} tone={data.enabled ? 'emerald' : 'slate'} />
        <Stat label={t('stat_engine')} value={data.installed ? t('installed') : t('missing')} tone={data.installed ? 'emerald' : 'amber'} />
        <Stat label={t('stat_history')} value={data.history.length} />
      </StatRow>
      {data.step.error ? <Pill tone="rose">{data.step.error}</Pill> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={t('now_title')} icon={<Music2 className="h-4 w-4 text-emerald-300" aria-hidden="true" />}>
          {hasTrack ? (
            <div className="flex flex-col gap-1">
              <p className="text-2xl font-black text-white">{playing.title}</p>
              <p className="text-sm text-slate-300">{playing.artist ?? t('unknown_artist')}</p>
              {playing.album ? <p className="text-xs text-slate-500">{playing.album}</p> : null}
            </div>
          ) : (
            <Empty>{data.enabled ? t('now_empty') : t('now_off')}</Empty>
          )}
          {!data.enabled ? (
            <div className="mt-3">
              <Btn busy={busy} onClick={() => void run(() => setRecognition(true), 'music_toggle_failed')}>
                {t('enable')}
              </Btn>
            </div>
          ) : null}
        </Panel>
        <Panel title={t('history_title')} icon={<History className="h-4 w-4 text-cyan-300" aria-hidden="true" />}>
          {data.history.length === 0 ? (
            <Empty>{t('history_empty')}</Empty>
          ) : (
            <List>
              {data.history.map((entry) => (
                <Row key={`${entry.at}-${entry.title}`} actions={<span className="text-[11px] text-slate-500">{formatTime(entry.at, lang)}</span>}>
                  <b>{entry.title}</b>
                  <span className="ml-2 text-xs text-slate-400">{entry.artist ?? ''}</span>
                </Row>
              ))}
            </List>
          )}
        </Panel>
      </div>
    </AppFrame>
  );
};

export default View;
