import { MicConfig } from './types';

export async function fetchMicConfig(nodeId: string): Promise<MicConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/mic`);
  if (!res.ok) throw new Error('Failed to load mic config');
  return res.json();
}

export async function updateMicConfig(nodeId: string, settings: Record<string, any>): Promise<MicConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/mic/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Failed to save mic config');
  return res.json();
}
