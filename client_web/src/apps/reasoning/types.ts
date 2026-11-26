export type Mode = 'off' | 'shadow' | 'active';

export interface Gate {
  readonly min_days: number;
  readonly min_samples: number;
  readonly min_agreement_bps: number;
  readonly max_invalid_bps: number;
  readonly max_wrong_action: number;
}

export interface Config {
  readonly retrieve_limit: number;
  readonly max_corrections: number;
  readonly cache_capacity: number;
  readonly cache_ttl_ms: number;
  readonly understand_threshold_bps: number;
  readonly gate: Gate;
}

export interface GateStatus {
  readonly ready: boolean;
  readonly days: number;
  readonly samples: number;
  readonly agreement_bps: number;
  readonly invalid_bps: number;
  readonly wrong_action: number;
  readonly reasons: string[];
}

export interface Status {
  readonly native: boolean;
  readonly gate?: GateStatus;
  readonly switch?: { readonly mode: Mode; readonly forced: boolean };
  readonly capabilities?: number;
  readonly generation?: number;
  readonly cache?: { readonly size: number; readonly hits: number; readonly misses: number };
  readonly config?: Config;
  readonly inventory?: { readonly count: number; readonly inferred: number };
  readonly emergency_off?: boolean;
}

export interface Trace {
  readonly kind: 'shadow' | 'active' | 'fallback' | 'error';
  readonly at: number;
  readonly intent: string;
  readonly language: string;
  readonly stage: string;
  readonly code: string;
  readonly capabilities: string[];
  readonly missing: string[];
  readonly approvals: string[];
  readonly cached: boolean;
  readonly tokens: number;
  readonly latency_ms: number;
  readonly legacy?: string[] | null;
  readonly agreed?: boolean;
}

export const MODES: Mode[] = ['off', 'shadow', 'active'];
