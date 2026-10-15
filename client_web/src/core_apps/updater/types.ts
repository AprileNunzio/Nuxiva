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
