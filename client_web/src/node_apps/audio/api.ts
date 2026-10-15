import { AudioConfig } from './types';

export async function fetchAudioConfig(nodeId: string): Promise<AudioConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/audio`);
  if (!res.ok) throw new Error('Failed to load audio config');
  return res.json();
}

export async function updateAudioConfig(nodeId: string, settings: Record<string, any>): Promise<AudioConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/audio/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Failed to save audio config');
  return res.json();
}
