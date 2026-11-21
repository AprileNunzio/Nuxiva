import { NUXIVA_VERSION } from '../../../version';

const STORAGE_KEY = 'nuxiva_remote_kiosk_advisory';

export interface RemoteKioskAdvisoryRecord {
  acknowledged: boolean;
  version: string;
  remote_enabled: boolean;
  timestamp: number;
}

export function loadRemoteKioskAdvisory(): RemoteKioskAdvisoryRecord | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<RemoteKioskAdvisoryRecord>;
    if (typeof parsed?.acknowledged !== 'boolean' || typeof parsed?.version !== 'string') {
      return null;
    }
    return {
      acknowledged: parsed.acknowledged,
      version: parsed.version,
      remote_enabled: Boolean(parsed.remote_enabled),
      timestamp: typeof parsed.timestamp === 'number' ? parsed.timestamp : Date.now(),
    };
  } catch {
    return null;
  }
}

export function shouldShowRemoteKioskAdvisory(): boolean {
  if (typeof window === 'undefined') return false;
  const record = loadRemoteKioskAdvisory();
  if (!record || !record.acknowledged) {
    return true;
  }
  return record.version !== NUXIVA_VERSION;
}

export function saveRemoteKioskAdvisoryAck(remoteEnabled: boolean): void {
  if (typeof window === 'undefined') return;
  try {
    const record: RemoteKioskAdvisoryRecord = {
      acknowledged: true,
      version: NUXIVA_VERSION,
      remote_enabled: remoteEnabled,
      timestamp: Date.now(),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
  } catch {
  }
}
