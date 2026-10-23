export type Role = 'drums' | 'bass' | 'chords' | 'pad' | 'lead' | 'arp' | 'vocal' | 'fx';

export interface Note {
  readonly t: number;
  readonly d: number;
  readonly p: number;
  readonly v: number;
}

export interface Vocal {
  readonly text: string;
  readonly lang: string;
  readonly voice: string;
  readonly speed: number;
  readonly pitch: number;
  readonly asset: string;
}

export interface Clip {
  readonly id: string;
  readonly name: string;
  readonly start: number;
  readonly length: number;
  readonly notes: readonly Note[];
  readonly vocal?: Vocal;
}

export interface Effect {
  readonly id: string;
  readonly type: string;
  readonly on: boolean;
  readonly params: Readonly<Record<string, number>>;
}

export interface Track {
  readonly id: string;
  readonly name: string;
  readonly role: Role;
  readonly instrument: string;
  readonly color: string;
  readonly volume: number;
  readonly pan: number;
  readonly mute: boolean;
  readonly solo: boolean;
  readonly effects: readonly Effect[];
  readonly clips: readonly Clip[];
}

export interface Section {
  readonly name: string;
  readonly start: number;
  readonly bars: number;
}

export interface Chord {
  readonly bar: number;
  readonly root: number;
  readonly quality: string;
}

export interface Lyrics {
  readonly lang: string;
  readonly text: string;
  readonly translations: Readonly<Record<string, string>>;
}

export interface Job {
  readonly state: 'idle' | 'building' | 'done' | 'error';
  readonly stage: string;
  readonly notice: string;
  readonly error: string;
}

export interface Project {
  readonly id: string;
  readonly title: string;
  readonly prompt: string;
  readonly created: number;
  readonly revision: number;
  readonly tempo: number;
  readonly beats: number;
  readonly swing: number;
  readonly key: { readonly root: number; readonly mode: string };
  readonly genre: string;
  readonly bars: number;
  readonly harmony: readonly Chord[];
  readonly structure: readonly Section[];
  readonly lyrics: Lyrics;
  readonly tracks: readonly Track[];
  readonly master: { readonly volume: number; readonly effects: readonly Effect[] };
  readonly job: Job;
}

export interface Summary {
  readonly id: string;
  readonly title: string;
  readonly genre: string;
  readonly tempo: number;
  readonly bars: number;
  readonly created: number;
  readonly tracks: number;
}

export type VoiceParams = Record<string, unknown>;

export interface Instrument {
  readonly id: string;
  readonly name: string;
  readonly role: Role;
  readonly color: string;
  readonly voice: VoiceParams;
  readonly tags: readonly string[];
}

export interface Knob {
  readonly min: number;
  readonly max: number;
  readonly default: number;
  readonly unit: string;
}

export interface EffectInfo {
  readonly id: string;
  readonly name: string;
  readonly knobs: Readonly<Record<string, Knob>>;
}

export interface Catalog {
  readonly roles: readonly Role[];
  readonly modes: readonly string[];
  readonly genres: readonly string[];
  readonly notes: readonly string[];
  readonly lanes: Readonly<Record<string, number>>;
  readonly instruments: readonly Instrument[];
  readonly effects: readonly EffectInfo[];
  readonly languages: Readonly<Record<string, string>>;
}

export interface Genre {
  readonly id: string;
  readonly name: string;
  readonly family: string;
  readonly tempo: readonly [number, number];
}

export interface VoiceChoice {
  readonly id: string;
  readonly name: string;
  readonly lang: string;
  readonly gender: string;
  readonly engine: string;
  readonly preferred: boolean;
}

export interface CastDevice {
  readonly id: string;
  readonly kind: string;
  readonly name: string;
  readonly active: boolean;
}

export interface ChatTurn {
  readonly who: 'you' | 'ai';
  readonly text: string;
}
