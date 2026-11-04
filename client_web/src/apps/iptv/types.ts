export interface TvPlaylist {
  readonly id: string;
  readonly name: string;
  readonly source: string;
  readonly count: number;
  readonly updated?: number;
  readonly has_url: boolean;
  readonly error?: string;
}

export interface TvTuner {
  readonly id: string;
  readonly name: string;
  readonly type: 'dvb_t2' | 'sat_ip' | 'hdhomerun' | 'enigma2' | string;
  readonly device: string;
  readonly status: 'online' | 'idle' | 'tuning' | 'offline';
  readonly signal_strength: number;
  readonly signal_quality: number;
  readonly channels_count: number;
  readonly last_scan?: number;
  readonly frequency_band?: string;
  readonly auto_detected?: boolean;
}

export interface TvSettings {
  readonly vpn_required: boolean;
  readonly vpn_profile: string;
  readonly epg_url: string;
  readonly epg_auto_refresh: boolean;
  readonly buffer_size: 'low' | 'medium' | 'high';
}

export interface TvOverview {
  readonly playlists: readonly TvPlaylist[];
  readonly count: number;
  readonly groups: readonly string[];
  readonly favorites: readonly string[];
  readonly tuners?: readonly TvTuner[];
  readonly settings?: TvSettings;
}

export interface TvChannel {
  readonly id: string;
  readonly name: string;
  readonly group: string;
  readonly logo: string;
  readonly favorite: boolean;
  readonly url?: string;
  readonly tvg_id?: string;
}

export interface TvChannelPage {
  readonly channels: readonly TvChannel[];
  readonly total: number;
  readonly page: number;
  readonly pages?: number;
  readonly limit?: number;
}

export interface TvTarget {
  readonly id: string;
  readonly kind: string;
  readonly name: string;
  readonly online: boolean;
}

export interface TvEpgProgram {
  readonly id: string;
  readonly title: string;
  readonly description: string;
  readonly genre: string;
  readonly start: number;
  readonly end: number;
  readonly duration_min: number;
  readonly progress?: number;
  readonly time_remaining_min?: number;
}

export interface TvEpgData {
  readonly channel_id: string;
  readonly channel_name: string;
  readonly available?: boolean;
  readonly message?: string;
  readonly now: TvEpgProgram | null;
  readonly next: TvEpgProgram | null;
  readonly schedule: readonly TvEpgProgram[];
}
