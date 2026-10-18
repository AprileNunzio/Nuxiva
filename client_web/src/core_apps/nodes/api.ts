import { MeshNodeItem, UsbPort, OnboardPayload, OnboardResponse } from './types';

export async function fetchNodes(): Promise<MeshNodeItem[]> {
  const res = await fetch('/api/v5/nodes');
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function fetchUsbPorts(): Promise<UsbPort[]> {
  const res = await fetch('/api/v5/nodes/usb_ports');
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function onboardNode(payload: OnboardPayload): Promise<OnboardResponse> {
  const res = await fetch('/api/v5/nodes/onboard', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function deleteNode(nodeId: string): Promise<{ removed: boolean; status: string }> {
  const res = await fetch(`/api/v5/nodes/${encodeURIComponent(nodeId)}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  const result = await res.json();
  if (result.removed !== true) throw new Error(result.error || result.status || 'node_not_removed');
  return result;
}
