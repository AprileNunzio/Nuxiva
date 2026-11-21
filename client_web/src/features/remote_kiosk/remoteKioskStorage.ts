export interface RemoteKioskStoredAdvisory {
  version: string;
  timestamp: number;
  decision: boolean;
}

const STORAGE_KEY = 'nuxiva_remote_kiosk_advisory_ack';
const NUXIVA_VERSION = '2026.3.0';

export function loadRemoteKioskAdvisory(): RemoteKioskStoredAdvisory | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as RemoteKioskStoredAdvisory;
  } catch {
    return null;
  }
}

export function shouldShowRemoteKioskAdvisory(): boolean {
  const current = loadRemoteKioskAdvisory();
  if (!current) return true;
  return current.version !== NUXIVA_VERSION;
}

export function saveRemoteKioskAdvisoryAck(remoteEnabled: boolean): void {
  try {
    const payload: RemoteKioskStoredAdvisory = {
      version: NUXIVA_VERSION,
      timestamp: Date.now(),
      decision: remoteEnabled,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {}
}

export async function syncRemoteKioskBackend(remoteEnabled: boolean): Promise<boolean> {
  try {
    const res = await fetch('/api/system/display-settings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Nuxiva-Request': '1',
      },
      body: JSON.stringify({ remote_kiosk_enabled: remoteEnabled }),
    });
    return res.ok;
  } catch {
    return false;
  }
}
