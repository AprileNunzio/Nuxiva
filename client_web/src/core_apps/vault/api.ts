import { sendJson } from '../shared/http';

export interface SyncResult {
  readonly imported: readonly string[];
  readonly written: number;
}

export const syncVault = () => sendJson<SyncResult>('/api/vault/sync', 'POST');
