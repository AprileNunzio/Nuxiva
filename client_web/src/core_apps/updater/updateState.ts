import type { UpdaterStatus } from './types';

export function updateSettled(status: UpdaterStatus, fromRev: string | null, previousResult: string | null): boolean {
  if (status.phase === 'ERROR') return true;
  if (status.pending || status.phase !== 'READY') return false;
  return (!!status.local_rev && status.local_rev !== fromRev) || status.last_result !== previousResult;
}
