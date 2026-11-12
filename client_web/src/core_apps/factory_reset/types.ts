export interface ResetOptions {
  readonly keepBackups: boolean;
  readonly includeShares: boolean;
}

export interface ResetDomain {
  readonly id: string;
  readonly items: number;
  readonly files: number;
  readonly bytes: number;
}

export interface ResetRoot {
  readonly name: string;
  readonly files: number;
  readonly bytes: number;
  readonly failed: number;
}

export interface ResetReport {
  readonly id: string;
  readonly status: 'verified' | 'incomplete';
  readonly finished: number;
  readonly roots: readonly ResetRoot[];
  readonly canariesChecked: number;
  readonly canariesSurvivors: number;
  readonly leftovers: Readonly<Record<string, readonly string[]>>;
  readonly openDeleted: number;
  readonly kept: readonly string[];
  readonly notStarted: readonly string[];
  readonly skippedMounts: number;
  readonly envKept: number;
  readonly envRotated: number;
  readonly envRemoved: number;
}

export interface ResetInventory {
  readonly domains: readonly ResetDomain[];
  readonly files: number;
  readonly bytes: number;
  readonly blockers: readonly string[];
  readonly waitSeconds: number;
  readonly ttl: number;
  readonly last: ResetReport | null;
}

export interface ResetChallenge {
  readonly token: string;
  readonly phrase: string;
  readonly waitSeconds: number;
  readonly expiresIn: number;
}

export type ResetStage = 'review' | 'identity' | 'confirm' | 'running' | 'done';

export type Translate = (key: string, params?: Record<string, string | number>) => string;
