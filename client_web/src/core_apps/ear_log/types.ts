export type EntryKind = 'command' | 'heard' | 'wake';
export type Verdict = '' | 'ok' | 'wrong';

export interface EarEntry {
  readonly id: string;
  readonly ts: number;
  readonly kind: EntryKind;
  readonly lang: string;
  readonly speaker: string;
  readonly score: number;
  readonly live: boolean;
  readonly dur: number;
  readonly text: string;
  readonly audio: boolean;
  readonly verdict: Verdict;
  readonly correction: string;
  readonly fixSpeaker: string;
  readonly note: string;
  readonly applied: boolean;
}

export interface EarLive {
  readonly available: boolean;
  readonly mode: 'auto' | 'on' | 'off';
  readonly active: boolean;
  readonly reason: string;
  readonly interval: number;
  readonly decodeMs: number;
  readonly load: number;
}

export interface EarStats {
  readonly total: number;
  readonly pending: number;
  readonly wrong: number;
  readonly audioMb: number;
}

export interface EarPerson {
  readonly slug: string;
  readonly name: string;
}

export interface EarJournal {
  readonly items: readonly EarEntry[];
  readonly stats: EarStats;
  readonly live: EarLive;
  readonly people: readonly EarPerson[];
}

export interface EarFilters {
  readonly kind: '' | 'command' | 'heard';
  readonly verdict: '' | 'pending' | 'ok' | 'wrong';
  readonly speaker: string;
  readonly query: string;
  readonly limit: number;
}

export interface FeedbackInput {
  readonly verdict: Verdict;
  readonly correction: string;
  readonly speaker: string;
  readonly note: string;
}
