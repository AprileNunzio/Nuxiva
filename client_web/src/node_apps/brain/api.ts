import { BrainConfig } from './types';

export async function fetchBrainConfig(nodeId: string): Promise<BrainConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/brain`);
  if (!res.ok) throw new Error('Failed to load brain config');
  return res.json();
}

export async function updateBrainConfig(nodeId: string, settings: Record<string, any>): Promise<BrainConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/brain/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Failed to save brain config');
  return res.json();
}
