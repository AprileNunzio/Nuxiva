export interface CortexIssue {
  readonly code: string;
  readonly message: string;
}

export interface RecentDecision {
  readonly verdict: 'fast' | 'grey' | 'slow';
  readonly reason: string | null;
  readonly neuron_id: string | null;
  readonly positive_similarity: number;
  readonly negative_similarity: number;
  readonly synaptic_weight: number;
  readonly latency_ms: number;
  readonly executed: boolean;
  readonly degraded: string | null;
}

export interface HippocampusStatus {
  readonly native: { readonly available: boolean; readonly error: CortexIssue | null };
  readonly embedding: {
    readonly model: string;
    readonly loaded: boolean;
    readonly dimension: number | null;
    readonly error: CortexIssue | null;
  };
  readonly storage: { readonly persistent: boolean; readonly error: CortexIssue | null };
  readonly neurons: number;
  readonly thresholds: Readonly<Record<string, number>>;
  readonly execution: { readonly extractor: boolean; readonly executor: boolean; readonly catalog: boolean };
  readonly telemetry: {
    readonly total: number;
    readonly executed: number;
    readonly verdicts: Readonly<Record<string, number>>;
    readonly reasons: Readonly<Record<string, number>>;
    readonly latency_ms: { readonly average: number; readonly maximum: number };
    readonly recent: readonly RecentDecision[];
  };
}
