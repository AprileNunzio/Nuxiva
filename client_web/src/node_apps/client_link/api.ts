import { Client_linkConfig } from './types';

export async function fetchClient_linkConfig(nodeId: string): Promise<Client_linkConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/client_link`);
  if (!res.ok) throw new Error('Failed to load client_link config');
  return res.json();
}

export async function updateClient_linkConfig(nodeId: string, settings: Record<string, any>): Promise<Client_linkConfig> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/apps/client_link/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Failed to save client_link config');
  return res.json();
}
