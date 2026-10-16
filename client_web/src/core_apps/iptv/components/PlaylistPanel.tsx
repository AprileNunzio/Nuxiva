import React, { FormEvent, useState } from 'react';
import { ListVideo, RefreshCw, Trash2 } from 'lucide-react';
import { Btn, Empty, Field, List, Panel, Pill, Row, inputClass } from '../../shared/kit';
import { addPlaylist, refreshPlaylist, removePlaylist } from '../api';
import { TvPlaylist } from '../types';

interface PlaylistPanelProps {
  readonly playlists: readonly TvPlaylist[];
  readonly busy: boolean;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly run: <R>(task: () => Promise<R>, code?: string) => Promise<R | null>;
}

export const PlaylistPanel: React.FC<PlaylistPanelProps> = ({ playlists, busy, t, run }) => {
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim() || !url.trim()) {
      return;
    }
    if ((await run(() => addPlaylist(name.trim(), url.trim(), ''), 'tv_playlist_failed')) !== null) {
      setName('');
      setUrl('');
    }
  };

  return (
    <Panel title={t('playlists_title')} icon={<ListVideo className="h-4 w-4 text-emerald-300" aria-hidden="true" />}>
      {playlists.length === 0 ? (
        <Empty>{t('playlists_empty')}</Empty>
      ) : (
        <List>
          {playlists.map((playlist) => (
            <Row
              key={playlist.id}
              actions={
                <>
                  {playlist.has_url ? (
                    <Btn tone="slate" busy={busy} onClick={() => void run(() => refreshPlaylist(playlist.id), 'tv_refresh_failed')} title={t('refresh')}>
                      <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                    </Btn>
                  ) : null}
                  <Btn tone="rose" busy={busy} onClick={() => void run(() => removePlaylist(playlist.id), 'tv_remove_failed')} title={t('delete')}>
                    <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                  </Btn>
                </>
              }
            >
              <b>{playlist.name}</b>
              <Pill>{t('channels_count', { n: playlist.count })}</Pill>
            </Row>
          ))}
        </List>
      )}
      <form onSubmit={submit} className="mt-4 flex flex-col gap-3 border-t border-slate-800 pt-4">
        <Field label={t('field_name')}>
          <input className={inputClass} value={name} maxLength={60} onChange={(event) => setName(event.target.value)} required />
        </Field>
        <Field label={t('field_url')}>
          <input className={inputClass} type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://…/playlist.m3u" required />
        </Field>
        <Btn type="submit" busy={busy}>
          {t('add_playlist')}
        </Btn>
      </form>
    </Panel>
  );
};
