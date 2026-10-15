import { UpdateStatus, CollaudoResult } from './types';

export async function fetchUpdateStatus(): Promise<UpdateStatus> {
  const res = await fetch('/api/v5/updater/status');
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function checkForUpdates(): Promise<UpdateStatus> {
  const res = await fetch('/api/v5/updater/check', { method: 'POST' });
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function saveSchedulePolicy(data: {
  scheduled_time: string;
  synchronized: boolean;
  auto_rollback: boolean;
  channel: string;
}): Promise<UpdateStatus> {
  const res = await fetch('/api/v5/updater/schedule', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function runCollaudoDiagnostics(): Promise<CollaudoResult> {
  const res = await fetch('/api/v5/updater/collaudo', { method: 'POST' });
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function triggerClusterUpdate(immediate = true): Promise<UpdateStatus> {
  const res = await fetch('/api/v5/updater/trigger', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ immediate, channel: 'stable' }),
  });
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}
