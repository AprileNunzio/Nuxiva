import React, { useState } from 'react';
import { MonitorPlay, Search, Square, Star, Tv } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, Field, List, Loading, Panel, Pill, Row, Stat, StatRow, Unreachable, inputClass } from '../shared/kit';
import { asList } from '../shared/http';
import { useAction, useResource } from '../shared/useResource';
import { play, setFavorite, stop } from './api';
import { PlaylistPanel } from './components/PlaylistPanel';
import { TvChannelPage, TvOverview, TvTarget } from './types';

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/iptv');
  const [query, setQuery] = useState('');
  const [group, setGroup] = useState('');
  const [favorites, setFavorites] = useState(false);
  const [target, setTarget] = useState('display');
  const [status, setStatus] = useState('');
  const overview = useResource<TvOverview>('/api/tv');
  const params = new URLSearchParams({ q: query.trim().slice(0, 80), group, fav: String(favorites) });
  const channels = useResource<TvChannelPage>(`/api/tv/channels?${params.toString()}`);
  const targets = useResource<{ targets: TvTarget[] }>('/api/tv/targets');
  const { busy, run } = useAction(() => {
    overview.reload();
    channels.reload();
  });

  if (overview.loading && !overview.data) {
    return <Loading label={t('loading')} />;
  }
  if (!overview.data) {
    return <Unreachable label={t(overview.error ? 'unreachable' : 'loading')} />;
  }

  const data = overview.data;
  const rows = channels.data?.channels ?? [];
  const where = asList<TvTarget>(targets.data?.targets);

  const watch = async (channel: string) => {
    const out = await run(() => play(channel, target), 'tv_play_failed');
    setStatus(out ? t('playing_on', { where: out.where }) : '');
  };

  return (
    <AppFrame
      title={t('title')}
      description={t('description')}
      onReload={overview.reload}
      actions={
        <Btn tone="rose" busy={busy} onClick={() => void run(stop, 'tv_stop_failed')}>
          <Square className="h-3.5 w-3.5" aria-hidden="true" />
          {t('stop')}
        </Btn>
      }
    >
      <StatRow>
        <Stat label={t('stat_channels')} value={data.count} />
        <Stat label={t('stat_playlists')} value={data.playlists.length} tone="emerald" />
        <Stat label={t('stat_favorites')} value={data.favorites.length} tone="amber" />
        <Stat label={t('stat_groups')} value={data.groups.length} tone="purple" />
      </StatRow>
      {status ? <Pill tone="emerald">{status}</Pill> : null}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <Panel title={t('channels_title')} icon={<Tv className="h-4 w-4 text-cyan-300" aria-hidden="true" />}>
          <div className="mb-3 grid gap-2 sm:grid-cols-4">
            <div className="relative sm:col-span-2">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
              <input className={`${inputClass} pl-9`} value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t('search')} aria-label={t('search')} />
            </div>
            <select className={inputClass} value={group} onChange={(event) => setGroup(event.target.value)} aria-label={t('group')}>
              <option value="">{t('all_groups')}</option>
              {data.groups.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <select className={inputClass} value={target} onChange={(event) => setTarget(event.target.value)} aria-label={t('target')}>
              {(where.length ? where : [{ id: 'display', kind: 'display', name: t('this_display'), online: true }]).map((item) => (
                <option key={item.id} value={item.id} disabled={!item.online}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>
          <label className="mb-3 flex items-center gap-2 text-xs text-slate-400">
            <input type="checkbox" checked={favorites} onChange={(event) => setFavorites(event.target.checked)} />
            {t('only_favorites')}
          </label>
          {rows.length === 0 ? (
            <Empty>{data.count === 0 ? t('no_channels') : t('no_match')}</Empty>
          ) : (
            <List>
              {rows.map((channel) => (
                <Row
                  key={channel.id}
                  actions={
                    <>
                      <Btn tone={channel.favorite ? 'amber' : 'slate'} busy={busy} onClick={() => void run(() => setFavorite(channel.id, !channel.favorite), 'tv_favorite_failed')} title={t('favorite')}>
                        <Star className="h-3.5 w-3.5" aria-hidden="true" />
                      </Btn>
                      <Btn tone="emerald" busy={busy} onClick={() => void watch(channel.id)}>
                        <MonitorPlay className="h-3.5 w-3.5" aria-hidden="true" />
                        {t('watch')}
                      </Btn>
                    </>
                  }
                >
                  <b>{channel.name}</b>
                  {channel.group ? <span className="ml-2 text-[11px] text-slate-500">{channel.group}</span> : null}
                </Row>
              ))}
            </List>
          )}
          {channels.data && channels.data.total > rows.length ? <p className="mt-2 text-xs text-slate-500">{t('showing', { shown: rows.length, total: channels.data.total })}</p> : null}
        </Panel>
        <PlaylistPanel playlists={data.playlists} busy={busy} t={t} run={run} />
      </div>
    </AppFrame>
  );
};

export default View;
