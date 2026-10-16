export interface BackupItem {
  readonly id: string;
  readonly created: number;
  readonly size: number;
  readonly sha256: string;
  readonly kind: string;
}

export interface BackupStatus {
  readonly enabled: boolean;
  readonly interval_hours: number;
  readonly keep: number;
  readonly items: readonly BackupItem[];
  readonly total_size: number;
  readonly next: number | null;
}

export interface VerifyResult {
  readonly id: string;
  readonly ok: boolean;
}
