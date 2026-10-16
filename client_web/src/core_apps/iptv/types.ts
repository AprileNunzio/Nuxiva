export interface TvPlaylist {
  readonly id: string;
  readonly name: string;
  readonly source: string;
  readonly count: number;
  readonly updated?: number;
  readonly has_url: boolean;
}

export interface TvOverview {
  readonly playlists: readonly TvPlaylist[];
  readonly count: number;
  readonly groups: readonly string[];
  readonly favorites: readonly string[];
}

export interface TvChannel {
  readonly id: string;
  readonly name: string;
  readonly group: string;
  readonly logo: string;
  readonly favorite: boolean;
}

export interface TvChannelPage {
  readonly channels: readonly TvChannel[];
  readonly total: number;
  readonly page: number;
}

export interface TvTarget {
  readonly id: string;
  readonly kind: string;
  readonly name: string;
  readonly online: boolean;
}
