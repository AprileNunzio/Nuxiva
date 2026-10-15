import { PrintersConfig } from './types';

export async function fetchPrintersConfig(nodeId: string): Promise<PrintersConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/printers`);
  if (!res.ok) throw new Error('Failed to load printers config');
  return res.json();
}

export async function updatePrintersConfig(nodeId: string, settings: Record<string, any>): Promise<PrintersConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/printers/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Failed to save printers config');
  return res.json();
}
