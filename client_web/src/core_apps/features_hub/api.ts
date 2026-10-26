import { DisplaySettings, BackendSettings, ScannedModel } from './types';

export const overviewUrl = (language: string) => `/api/features?lang=${encodeURIComponent(language)}`;

export async function fetchDisplaySettings(): Promise<DisplaySettings> {
  const res = await fetch('/api/system/display-settings');
  if (!res.ok) throw new Error('Failed to fetch display settings');
  const data = await res.json();
  return data.settings;
}

export async function saveDisplaySettings(settings: Partial<DisplaySettings>): Promise<DisplaySettings> {
  const res = await fetch('/api/system/display-settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings)
  });
  if (!res.ok) throw new Error('Failed to save display settings');
  const data = await res.json();
  return data.settings;
}

export async function fetchBackendSettings(): Promise<BackendSettings> {
  const res = await fetch('/api/system/backend-settings');
  if (!res.ok) throw new Error('Failed to fetch backend settings');
  const data = await res.json();
  return data.settings;
}

export async function saveBackendSettings(settings: Partial<BackendSettings>): Promise<BackendSettings> {
  const res = await fetch('/api/system/backend-settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings)
  });
  if (!res.ok) throw new Error('Failed to save backend settings');
  const data = await res.json();
  return data.settings;
}

export async function scanOllamaModels(host: string): Promise<{ online: boolean; latency_ms: number; models: ScannedModel[]; error?: string }> {
  const res = await fetch('/api/v2/brain/config/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ host })
  });
  if (!res.ok) {
    return { online: false, latency_ms: 0, models: [], error: `HTTP ${res.status}` };
  }
  return res.json();
}
