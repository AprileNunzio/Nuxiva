import { getJson, sendJson } from '../shared/http';
import { TvEpgData, TvPlaylist, TvSettings, TvTuner } from './types';

export const addPlaylist = (name: string, url: string, text: string) =>
  sendJson<TvPlaylist>('/api/tv/playlists', 'POST', { name, url, text });

export const refreshPlaylist = (id: string) =>
  sendJson<TvPlaylist>(`/api/tv/playlists/${encodeURIComponent(id)}/refresh`, 'POST');

export const removePlaylist = (id: string) =>
  sendJson<{ ok: boolean }>(`/api/tv/playlists/${encodeURIComponent(id)}`, 'DELETE');

export const uploadPlaylistFile = async (file: File): Promise<TvPlaylist> => {
  const res = await fetch(`/api/tv/upload?name=${encodeURIComponent(file.name.replace(/\.[^/.]+$/, ''))}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/octet-stream',
      'X-File-Name': encodeURIComponent(file.name),
    },
    body: file,
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || 'Errore durante il caricamento della playlist');
  }
  return res.json();
};

export const setFavorite = (id: string, on: boolean) =>
  sendJson<{ favorites: string[] }>(`/api/tv/favorites/${encodeURIComponent(id)}`, 'PUT', { on });

export const fetchTuners = () =>
  getJson<{ tuners: TvTuner[] }>('/api/tv/tuners');

export const discoverTuners = () =>
  sendJson<{ tuners: TvTuner[] }>('/api/tv/tuners/discover', 'POST');

export const addTuner = (data: { name: string; type: string; device: string; options?: { frequency_band?: string } }) =>
  sendJson<TvTuner>('/api/tv/tuners', 'POST', data);

export const removeTuner = (id: string) =>
  sendJson<{ ok: boolean }>(`/api/tv/tuners/${encodeURIComponent(id)}`, 'DELETE');

export const scanTuner = (id: string) =>
  sendJson<{ ok: boolean; tuner: TvTuner }>(`/api/tv/tuners/${encodeURIComponent(id)}/scan`, 'POST');

export const fetchEpg = (channelId: string) =>
  getJson<TvEpgData>(`/api/tv/epg/${encodeURIComponent(channelId)}`);

export const refreshEpg = (url: string = '') =>
  sendJson<{ ok: boolean; channels_with_epg: number; total_programs: number }>('/api/tv/epg/refresh', 'POST', { url });

export const fetchSettings = () =>
  getJson<TvSettings>('/api/tv/settings');

export const updateSettings = (settings: Partial<TvSettings>) =>
  sendJson<TvSettings>('/api/tv/settings', 'PUT', settings);

export const fetchPreview = (channelId: string) =>
  getJson<{ src: string; name: string }>(`/api/tv/preview/${encodeURIComponent(channelId)}`);

export const play = (channelId: string, target: string = 'display') =>
  sendJson<{ ok: boolean; target: string }>('/api/tv/play', 'POST', { channel: channelId, target });

export const stop = () =>
  sendJson<{ ok: boolean }>('/api/tv/stop', 'POST');

export const getLiveStreamUrl = (channelId: string): string =>
  `/api/tv/live/${encodeURIComponent(channelId)}`;

export const getLogoProxyUrl = (url?: string): string => {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return `/api/tv/proxy/logo?url=${encodeURIComponent(url)}`;
  }
  return url;
};
