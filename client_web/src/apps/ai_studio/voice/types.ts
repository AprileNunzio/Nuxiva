export type VoiceChannelFilter = 'voice' | '';

export type VoiceVerdict = '' | 'ok' | 'wrong';

export interface VoiceHeard {
  text: string;
  lang: string;
  speaker: string;
  score: number;
  woke: boolean;
  ms: number;
  dur: number;
  audio: boolean;
  verdict: VoiceVerdict;
  correction: string;
  note: string;
  fix_speaker: string;
  applied: boolean;
}

export interface VoiceTurn {
  id: string;
  at: number;
  device: string;
  channel: 'voice' | 'text';
  intent: string;
  agent: string;
  lang: string;
  elapsed_ms: number;
  directed: boolean;
  said: string;
  resolved: string;
  reply: string;
  speaker: string;
  score: number;
  reason: string;
  heard: VoiceHeard | null;
}

export interface VoiceStats {
  total?: number;
  pending?: number;
  ok?: number;
  wrong?: number;
  audio_mb?: number;
}

export interface VoiceTurnsPage {
  items: VoiceTurn[];
  stats: VoiceStats;
}

export interface VoiceQuery {
  channel: VoiceChannelFilter;
  q: string;
  before?: number;
  limit?: number;
}
