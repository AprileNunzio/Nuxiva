import { sendJson } from '../shared/http';

export const addPlaylist = (name: string, url: string, text: string) => sendJson('/api/tv/playlists', 'POST', { name, url, text });
export const refreshPlaylist = (id: string) => sendJson(`/api/tv/playlists/${encodeURIComponent(id)}/refresh`, 'POST');
export const removePlaylist = (id: string) => sendJson(`/api/tv/playlists/${encodeURIComponent(id)}`, 'DELETE');
export const setFavorite = (id: string, on: boolean) => sendJson(`/api/tv/favorites/${encodeURIComponent(id)}`, 'PUT', { on });
export const play = (channel: string, target: string) => sendJson<{ where: string }>('/api/tv/play', 'POST', { channel, target });
export const stop = () => sendJson('/api/tv/stop', 'POST');
