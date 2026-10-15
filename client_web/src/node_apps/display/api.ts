import { DisplayConfig } from './types';

export async function fetchDisplayConfig(nodeId: string): Promise<DisplayConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/display`);
  if (!res.ok) throw new Error('Failed to load display config');
  return res.json();
}

export async function updateDisplayConfig(nodeId: string, settings: Record<string, any>): Promise<DisplayConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/display/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Failed to save display config');
  return res.json();
}
