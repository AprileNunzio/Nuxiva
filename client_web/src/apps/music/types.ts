export interface Track {
  readonly id: number;
  readonly title: string;
  readonly artist: string;
  readonly album_artist?: string;
  readonly album: string;
  readonly track_no?: number;
  readonly disc_no?: number;
  readonly year?: number;
  readonly genre?: string;
  readonly duration: number; // in seconds
  readonly bitrate?: number;
  readonly cover?: string | null;
  readonly album_key: string;
  readonly artist_key: string;
  readonly added?: number;
  readonly plays?: number;
  readonly last_played?: number;
  readonly liked?: boolean;
  readonly stars?: number;
  readonly path?: string;
  readonly is_video?: boolean;
}

export interface Playlist {
  readonly id: number;
  readonly name: string;
  readonly user?: string;
  readonly kind: 'manual' | 'smart';
  readonly count: number;
  readonly duration?: number;
  readonly description?: string;
  readonly tracks?: readonly Track[];
}

export interface LyricsLine {
  readonly time: number; // seconds
  readonly text: string;
}

export interface LyricsResponse {
  readonly synced?: readonly LyricsLine[];
  readonly plain?: string;
}

export interface LibraryOverview {
  readonly tracks: number;
  readonly albums: number;
  readonly artists: number;
  readonly genres: number;
  readonly duration: number;
  readonly size: number;
  readonly root: string;
  readonly service?: {
    readonly scanning?: boolean;
    readonly organizing?: boolean;
    readonly last_scan?: number;
  };
}

export interface HomeMixes {
  readonly recent?: readonly Track[];
  readonly favorites?: readonly Track[];
  readonly mixes?: readonly {
    readonly id: string;
    readonly title: string;
    readonly subtitle?: string;
    readonly tracks?: readonly Track[];
  }[];
}

export interface MusicSettings {
  readonly NUXIVA_MUSIC_SCANNER_ENABLED?: string;
  readonly NUXIVA_MUSIC_SCAN_MIN?: string;
  readonly NUXIVA_MUSIC_RECOGNITION?: string;
  readonly NUXIVA_MUSIC_IDENTIFY?: string;
  readonly NUXIVA_MUSIC_COVERS?: string;
  readonly NUXIVA_MUSIC_LYRICS?: string;
  readonly NUXIVA_MUSIC_ORGANIZE?: string;
  readonly NUXIVA_MUSIC_TRANSCODE?: string;
  readonly NUXIVA_MUSIC_TRANSCODE_KBPS?: string;
  readonly NUXIVA_MUSIC_CROSSFADE?: string;
  readonly NUXIVA_MUSIC_RADIO?: string;
  readonly NUXIVA_MUSIC_CAST?: string;
  readonly NUXIVA_MUSIC_VOICE?: string;
  readonly NUXIVA_MUSIC_TAGS?: string;
  readonly NUXIVA_MUSIC_RENAME?: string;
  readonly [key: string]: string | undefined;
}

