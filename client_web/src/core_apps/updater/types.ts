export type UpdaterPhase = 'BOOTING' | 'READY' | 'UPDATING' | 'ERROR' | string;

export interface UpdatePolicy {
  readonly auto_update: boolean;
  readonly window: string;
  readonly interval_minutes: number;
  readonly sync_nodes: boolean;
  readonly require_ci: boolean;
}

export interface RolloutNode {
  readonly id: string;
  readonly name: string;
  readonly type: string | null;
  readonly room: string | null;
  readonly online: boolean;
  readonly version: string | null;
  readonly last_seen: number | null;
  readonly update_queued: boolean;
}

export interface PendingUpdate {
  readonly from: string;
  readonly to: string;
  readonly at: number;
}

export interface UpdaterStatus {
  readonly version: string | null;
  readonly local_rev: string | null;
  readonly remote_rev: string | null;
  readonly target_rev: string | null;
  readonly available: boolean;
  readonly changelog: readonly string[];
  readonly last_check: string | null;
  readonly last_result: string | null;
  readonly ci_note: string | null;
  readonly check_error?: string | null;
  readonly phase: UpdaterPhase;
  readonly message: string | null;
  readonly pending: PendingUpdate | null;
  readonly policy: UpdatePolicy;
  readonly next_window: string | null;
  readonly nodes: readonly RolloutNode[];
}

export type CheckStatus = 'PASS' | 'WARN' | 'FAIL';

export interface CollaudoCheck {
  readonly id: string;
  readonly status: CheckStatus;
  readonly metric: string;
  readonly detail: string;
}

export interface CollaudoResult {
  readonly timestamp: number;
  readonly all_passed: boolean;
  readonly tests: readonly CollaudoCheck[];
}

export interface HistoryEvent {
  readonly ts: string;
  readonly level: string;
  readonly msg: string;
}

export interface CommitDetail {
  readonly sha: string;
  readonly short_sha: string;
  readonly author: string;
  readonly timestamp: number;
  readonly date_iso: string;
  readonly title: string;
  readonly body: string;
}

export type UpdateRecordStatus = 'installed' | 'failed' | 'rollback' | string;

export interface UpdateRecord {
  readonly id: string;
  readonly status: UpdateRecordStatus;
  readonly from_rev: string | null;
  readonly to_rev: string;
  readonly from_short: string | null;
  readonly to_short: string;
  readonly installed_at: number;
  readonly installed_at_iso: string;
  readonly reason: string | null;
  readonly commits: readonly CommitDetail[];
  readonly commit_count: number;
  readonly error?: string | null;
}

export interface UpdateHistoryResponse {
  readonly records: readonly UpdateRecord[];
  readonly total: number;
  readonly limit: number;
  readonly offset: number;
  readonly events: readonly HistoryEvent[];
}

export type StageStatus = 'pending' | 'running' | 'done' | 'skipped' | 'failed';

export interface PipelineStage {
  readonly id: string;
  readonly weight: number;
  readonly status: StageStatus;
  readonly started_at: number | null;
  readonly finished_at: number | null;
}

export interface PipelineState {
  readonly stages: readonly PipelineStage[];
  readonly percent: number;
  readonly active: string | null;
  readonly outcome: 'success' | 'failed' | null;
}

export type SignatureVerdict = 'trusted' | 'valid' | 'unsigned' | 'unknown_key' | 'expired' | 'revoked' | 'bad';

export interface SignatureReport {
  readonly verdict: SignatureVerdict;
  readonly blocking: boolean;
  readonly format: string;
  readonly fingerprint: string | null;
  readonly signer: string | null;
}

export interface IntegrityReport {
  readonly algorithm: string;
  readonly checked: number;
  readonly matched: number;
  readonly skipped: number;
  readonly mismatched: readonly string[];
  readonly missing: readonly string[];
  readonly rejected: readonly string[];
  readonly fingerprint: string;
  readonly intact: boolean;
}

export interface ComponentImpact {
  readonly component: string;
  readonly added: number;
  readonly modified: number;
  readonly deleted: number;
  readonly renamed: number;
}

export interface ImpactReport {
  readonly files: number;
  readonly components: readonly ComponentImpact[];
  readonly effects: readonly string[];
  readonly error?: string;
}

export interface UpdateRun {
  readonly id: string;
  readonly from: string;
  readonly to: string;
  readonly reason: string;
  readonly started_at: number;
  readonly pipeline: PipelineState | null;
  readonly signature: SignatureReport | null;
  readonly integrity: IntegrityReport | null;
  readonly impact: ImpactReport | null;
}

export type ConsoleLevel = 'info' | 'ok' | 'warn' | 'error';

export interface ConsoleLine {
  readonly t: number;
  readonly level: ConsoleLevel;
  readonly code: string;
  readonly stage: string | null;
  readonly args: Readonly<Record<string, string | number | boolean | null>>;
}

export interface ChangeEntry {
  readonly sha: string;
  readonly kind: string;
  readonly scope: string | null;
  readonly breaking: boolean;
  readonly summary: string;
}

export interface ServiceState {
  readonly unit: string;
  readonly state: string;
}

export interface BootStep {
  readonly step: string;
  readonly title: string;
  readonly progress: number;
  readonly message: string;
  readonly detail: string;
  readonly silent_for: number | null;
}

export interface UpdaterTelemetry {
  readonly engine: { readonly name: 'rust' | 'python'; readonly version: string };
  readonly host: { readonly python: string; readonly git: string; readonly branch: string; readonly root: string };
  readonly run: UpdateRun | null;
  readonly console: readonly ConsoleLine[];
  readonly changelog: readonly ChangeEntry[];
  readonly pending: { readonly signature: SignatureReport | null; readonly impact: ImpactReport | null };
  readonly services: readonly ServiceState[];
  readonly stages: readonly string[];
  readonly boot?: BootStep | null;
}
