export type EntryKind = 'skill' | 'tool' | 'connector';

export interface CatalogEntry {
  readonly key: string;
  readonly ref: string;
  readonly kind: EntryKind;
  readonly name: string;
  readonly description: string;
  readonly group: string;
  readonly source: string;
  readonly manageable: boolean;
  readonly editable: boolean;
  readonly enabled: boolean;
  readonly uses?: number;
  readonly fails?: number;
  readonly examples?: readonly string[];
  readonly patterns?: readonly string[];
  readonly confirm?: boolean;
  readonly arguments?: readonly string[];
  readonly declares_requests?: boolean;
}

export interface Catalog {
  readonly entries: readonly CatalogEntry[];
  readonly counts: Readonly<Record<EntryKind, number>>;
  readonly categories: Readonly<Record<string, string>>;
  readonly errors: readonly unknown[];
  readonly generate: boolean;
}

export interface AlgorithmTest {
  readonly ok: boolean;
  readonly result?: unknown;
  readonly speech?: string;
  readonly error?: string;
  readonly matches: boolean;
  readonly total_ms: number;
}

export interface AlgorithmDraft {
  readonly name: string;
  readonly category: string;
  readonly description: string;
  readonly patterns: readonly string[];
  readonly examples: readonly string[];
  readonly code: string;
  readonly probe: string;
}
