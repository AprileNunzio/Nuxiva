export interface VoiceItem {
  readonly id: string;
  readonly name: string;
  readonly gender: string;
  readonly lang: string;
  readonly locale: string;
  readonly engine: 'kokoro' | 'piper' | 'online' | 'studio';
  readonly quality: string;
  readonly sizeMb: number | null;
  readonly installed: boolean;
  readonly downloadable: boolean;
  readonly downloading: boolean;
  readonly preferred: boolean;
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
}
