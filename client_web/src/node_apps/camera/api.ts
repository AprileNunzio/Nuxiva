import { CameraConfig } from './types';

export async function fetchCameraConfig(nodeId: string): Promise<CameraConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/camera`);
  if (!res.ok) throw new Error('Failed to load camera config');
  return res.json();
}

export async function updateCameraConfig(nodeId: string, settings: Record<string, any>): Promise<CameraConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/camera/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Failed to save camera config');
  return res.json();
}
