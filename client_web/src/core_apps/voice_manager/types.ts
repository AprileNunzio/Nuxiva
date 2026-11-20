export type EngineKind = 'kokoro' | 'piper' | 'online' | 'studio' | 'elevenlabs';
export type EngineMode = 'local' | 'elevenlabs' | 'hybrid';

export interface VoiceItem {
  readonly id: string;
  readonly name: string;
  readonly gender: string;
  readonly lang: string;
  readonly locale: string;
  readonly engine: EngineKind;
  readonly quality: string;
  readonly sizeMb: number | null;
  readonly installed: boolean;
  readonly downloadable: boolean;
  readonly downloading: boolean;
  readonly preferred: boolean;
}

export interface AudioVaultStats {
  readonly total_clips: number;
  readonly total_hits: number;
  readonly total_chars_saved: number;
  readonly equivalent_free_plans_saved: number;
  readonly total_size_mb: number;
  readonly common_phrases_count: number;
}

export interface AudioVaultClip {
  readonly id: string;
  readonly text: string;
  readonly voice_id: string;
  readonly engine: string;
  readonly char_count: number;
  readonly hit_count: number;
  readonly chars_saved: number;
  readonly created_at: string;
  readonly last_used_at: string;
  readonly pinned: boolean;
  readonly file_size?: number;
}

export interface ElevenLabsSubscription {
  readonly configured: boolean;
  readonly tier: string;
  readonly character_count: number;
  readonly character_limit: number;
  readonly remaining_characters: number;
  readonly percent_used: number;
  readonly next_reset_days: number;
  readonly status: string;
  readonly message?: string;
}

export interface ElevenLabsVoice {
  readonly id: string;
  readonly name: string;
  readonly category: string;
  readonly preview_url: string;
  readonly gender: string;
  readonly accent: string;
  readonly description: string;
}

export interface EngineSettings {
  readonly engine_mode: EngineMode;
  readonly elevenlabs_voice_id: string;
  readonly fallback_local: string;
  readonly elevenlabs_configured: boolean;
  readonly speed: number;
  readonly pitch: number;
  readonly volume: number;
  readonly stability: number;
  readonly similarity_boost: number;
}

export interface VoiceOverview {
  readonly order: VoiceItem[];
  readonly custom: boolean;
  readonly voices: VoiceItem[];
  readonly langs: Record<string, string>;
  readonly langPrefs: Record<string, string>;
  readonly fallback: string;
  readonly onlineEnabled: boolean;
  readonly autoDownload: boolean;
  readonly engine_mode?: EngineMode;
  readonly elevenlabs_configured?: boolean;
  readonly vault_stats?: AudioVaultStats;
}
