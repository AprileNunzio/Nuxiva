export interface NowPlaying {
  readonly title?: string;
  readonly artist?: string;
  readonly album?: string;
  readonly [key: string]: unknown;
}

export interface MusicOverview {
  readonly enabled: boolean;
  readonly installed: boolean;
  readonly now_playing: NowPlaying;
  readonly history: readonly { readonly title: string; readonly artist: string | null; readonly at: number }[];
  readonly step: { readonly status: string | null; readonly error: string };
}
