import { WhiteboardConfig } from './types';

export async function fetchWhiteboardConfig(nodeId: string): Promise<WhiteboardConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/whiteboard`);
  if (!res.ok) throw new Error('Failed to load whiteboard config');
  return res.json();
}

export async function updateWhiteboardConfig(nodeId: string, settings: Record<string, any>): Promise<WhiteboardConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/whiteboard/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Failed to save whiteboard config');
  return res.json();
}
