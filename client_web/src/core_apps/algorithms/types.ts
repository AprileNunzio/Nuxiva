export interface Algorithm {
  readonly key: string;
  readonly id: string;
  readonly name: string;
  readonly category: string;
  readonly category_label: string;
  readonly description: string;
  readonly examples: readonly string[];
  readonly source: string;
  readonly priority: number;
  readonly stats: { readonly uses: number; readonly fails: number; readonly enabled: boolean; readonly avg_ms?: number };
}

export interface AlgorithmsOverview {
  readonly skills: readonly Algorithm[];
  readonly errors: readonly unknown[];
  readonly categories: Readonly<Record<string, string>>;
  readonly enabled: boolean;
  readonly generate: boolean;
}

export interface AlgorithmTest {
  readonly ok: boolean;
  readonly result?: unknown;
  readonly error?: string;
  readonly matches: boolean;
  readonly total_ms: number;
}
