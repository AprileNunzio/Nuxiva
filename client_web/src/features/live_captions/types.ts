export type CaptionScope = 'all' | 'addressed';
export type CaptionSize = 'small' | 'medium' | 'large';
export type CaptionPosition = 'bottom' | 'center';

export interface CaptionsConfig {
  enabled: boolean;
  scope: CaptionScope;
  speaker: boolean;
  size: CaptionSize;
  hold: number;
  position: CaptionPosition;
}

export interface CaptionWord {
  text: string;
  stable: boolean;
}

export interface CaptionLine {
  utt: string;
  speaker: string;
  speakerName: string;
  speakerHue: number;
  words: CaptionWord[];
  addressed: boolean;
  final: boolean;
  done: boolean;
}

export interface CaptionEvent {
  type: 'partial' | 'heard' | 'transcript' | 'caption_drop' | 'ready';
  utt?: string;
  seq?: number;
  text?: string;
  stable?: number;
  speaker?: string | null;
  addressed?: boolean;
  voiceprint?: boolean;
}

export type SpeakerMap = Record<string, string>;
