export interface TwinConflict {
  readonly rule: string;
  readonly severity: string;
  readonly culprits: readonly string[];
  readonly subjects: readonly string[];
}

export interface TwinVerdict {
  readonly conflicts: readonly TwinConflict[];
  readonly dropped: readonly unknown[];
  readonly blocked: boolean;
  readonly empty: boolean;
  readonly at?: number;
  readonly source?: string;
  readonly text?: string;
}

export interface TwinOverview {
  readonly mode: string;
  readonly rules: Readonly<Record<string, boolean>>;
  readonly available: readonly string[];
  readonly history: readonly TwinVerdict[];
}

export type SimulationResult = TwinVerdict;
