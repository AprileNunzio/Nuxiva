import { BluetoothConfig } from './types';

export async function fetchBluetoothConfig(nodeId: string): Promise<BluetoothConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/bluetooth`);
  if (!res.ok) throw new Error('Failed to load bluetooth config');
  return res.json();
}

export async function updateBluetoothConfig(nodeId: string, settings: Record<string, any>): Promise<BluetoothConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/bluetooth/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Failed to save bluetooth config');
  return res.json();
}
