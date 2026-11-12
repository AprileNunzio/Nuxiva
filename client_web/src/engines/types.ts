export type EngineFamily = 'reasoning' | 'speech_recognition' | 'music_recognition' | 'vision';

export interface EngineOption {
  id: string;
  type: 'boolean' | 'range' | 'select' | 'string';
  default: boolean | number | string;
  label_key: string;
  desc_key: string;
  min?: number;
  max?: number;
  choices?: Array<{ value: string; label_key: string }>;
}

export interface EngineManifest {
  id: string;
  name: string;
  version: string;
  family: EngineFamily;
  author?: string;
  scope?: string;
  capabilities?: string[];
  options?: EngineOption[];
}

export interface ActiveEnginesState {
  reasoning: string;
  speech_recognition: string;
  music_recognition: string;
  vision?: string;
}
