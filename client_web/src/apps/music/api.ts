import { Track, Playlist, LyricsResponse, LibraryOverview, HomeMixes, MusicSettings } from './types';

const HEADERS = {
  Accept: 'application/json',
  'X-Nuxiva-Request': '1',
};

export async function fetchLibraryOverview(signal?: AbortSignal): Promise<LibraryOverview> {
  const res = await fetch('/api/music/library', { headers: HEADERS, signal });
  if (!res.ok) throw new Error(`music_library_${res.status}`);
  return res.json();
}

export async function fetchHome(signal?: AbortSignal): Promise<HomeMixes> {
  const res = await fetch('/api/music/home', { headers: HEADERS, signal });
  if (!res.ok) throw new Error(`music_home_${res.status}`);
  return res.json();
}

export async function fetchTracks(params: {
  sort?: string;
  limit?: number;
  offset?: number;
  genre?: string;
  liked?: boolean;
} = {}, signal?: AbortSignal): Promise<{ tracks: Track[]; total: number }> {
  const q = new URLSearchParams();
  if (params.sort) q.set('sort', params.sort);
  if (params.limit) q.set('limit', String(params.limit));
  if (params.offset) q.set('offset', String(params.offset));
  if (params.genre) q.set('genre', params.genre);
  if (params.liked) q.set('liked', 'true');
  const res = await fetch(`/api/music/tracks?${q.toString()}`, { headers: HEADERS, signal });
  if (!res.ok) throw new Error(`music_tracks_${res.status}`);
  return res.json();
}

export async function searchMusic(q: string, signal?: AbortSignal): Promise<{ tracks: Track[]; albums: unknown[]; artists: unknown[] }> {
  const res = await fetch(`/api/music/search?q=${encodeURIComponent(q)}`, { headers: HEADERS, signal });
  if (!res.ok) throw new Error(`music_search_${res.status}`);
  return res.json();
}

export async function fetchPlaylists(signal?: AbortSignal): Promise<Playlist[]> {
  const res = await fetch('/api/music/playlists', { headers: HEADERS, signal });
  if (!res.ok) throw new Error(`music_playlists_${res.status}`);
  const data = await res.json();
  return data.playlists || [];
}

export async function createPlaylist(name: string, description = ''): Promise<{ id: number }> {
  const res = await fetch('/api/music/playlists', {
    method: 'POST',
    headers: { ...HEADERS, 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description }),
  });
  if (!res.ok) throw new Error(`create_playlist_${res.status}`);
  return res.json();
}

export async function fetchPlaylistDetails(id: number, signal?: AbortSignal): Promise<Playlist> {
  const res = await fetch(`/api/music/playlists/${id}`, { headers: HEADERS, signal });
  if (!res.ok) throw new Error(`playlist_detail_${res.status}`);
  return res.json();
}

export async function addTrackToPlaylist(playlistId: number, trackId: number): Promise<void> {
  const res = await fetch(`/api/music/playlists/${playlistId}/tracks`, {
    method: 'POST',
    headers: { ...HEADERS, 'Content-Type': 'application/json' },
    body: JSON.stringify({ tracks: [trackId] }),
  });
  if (!res.ok) throw new Error(`add_to_playlist_${res.status}`);
}

export async function fetchLyrics(trackId: number, signal?: AbortSignal): Promise<LyricsResponse> {
  const res = await fetch(`/api/music/lyrics/${trackId}`, { headers: HEADERS, signal });
  if (!res.ok) return {};
  return res.json();
}

export async function toggleLike(trackId: number, on: boolean): Promise<{ liked: boolean }> {
  const res = await fetch(`/api/music/tracks/${trackId}/like`, {
    method: 'POST',
    headers: { ...HEADERS, 'Content-Type': 'application/json' },
    body: JSON.stringify({ on }),
  });
  if (!res.ok) throw new Error(`like_track_${res.status}`);
  return res.json();
}

export async function reportPlayed(trackId: number, seconds: number, done = false): Promise<void> {
  try {
    await fetch(`/api/music/tracks/${trackId}/played`, {
      method: 'POST',
      headers: { ...HEADERS, 'Content-Type': 'application/json' },
      body: JSON.stringify({ seconds, done, source: 'nexus_player' }),
    });
  } catch {
    // best-effort telemetry
  }
}

export async function uploadMediaFile(file: File): Promise<{ ok: boolean }> {
  const res = await fetch(`/api/music/upload?name=${encodeURIComponent(file.name)}`, {
    method: 'PUT',
    headers: {
      'X-Nuxiva-Request': '1',
      'Content-Type': file.type || 'application/octet-stream',
      'Content-Length': String(file.size),
    },
    body: file,
  });
  if (!res.ok) {
    throw new Error(`upload_failed_${res.status}`);
  }
  return res.json();
}

export async function triggerLibraryScan(): Promise<void> {
  const res = await fetch('/api/music/scan', {
    method: 'POST',
    headers: { ...HEADERS, 'Content-Type': 'application/json' },
    body: JSON.stringify({ full: false }),
  });
  if (!res.ok) throw new Error(`scan_failed_${res.status}`);
}

export function getStreamUrl(trackId: number): string {
  return `/api/music/stream/${trackId}`;
}

export function getCoverUrl(albumKey: string): string {
  return `/api/music/cover/${albumKey}`;
}

export async function askMusicMCP(query: string): Promise<string> {
  const res = await fetch('/mcp', {
    method: 'POST',
    headers: { ...HEADERS, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: `music-mcp-${Date.now()}`,
      method: 'tools/call',
      params: {
        name: 'music_search',
        arguments: { query },
      },
    }),
  });
  if (!res.ok) return 'Assistente non disponibile al momento.';
  const data = await res.json();
  const text = data?.result?.content?.[0]?.text;
  return text || 'Nessun risultato trovato per la richiesta musicale.';
}

export async function fetchMusicSettings(signal?: AbortSignal): Promise<MusicSettings> {
  const res = await fetch('/api/music/settings', { headers: HEADERS, signal });
  if (res.ok) {
    const data = await res.json();
    return data.values || {};
  }
  const fallback = await fetch('/api/features/music/settings', { headers: HEADERS, signal });
  if (fallback.ok) {
    const data = await fallback.json();
    return data.values || {};
  }
  return {};
}

export async function saveMusicSettings(settings: Record<string, string>): Promise<{ ok: boolean }> {
  let res = await fetch('/api/music/settings', {
    method: 'PUT',
    headers: { ...HEADERS, 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) {
    res = await fetch('/api/features/music/settings', {
      method: 'PUT',
      headers: { ...HEADERS, 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
  }
  if (!res.ok) throw new Error(`save_settings_${res.status}`);
  return res.json();
}

