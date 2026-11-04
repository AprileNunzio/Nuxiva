import type {
  Entity,
  Area,
  Floor,
  RoomItem,
  AutomationItem,
  EnergyData,
  AssistResult,
  HomeOverview,
} from './types';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const errorText = await res.text();
    let message = `HTTP ${res.status}`;
    try {
      const parsed = JSON.parse(errorText);
      message = parsed.detail || parsed.message || message;
    } catch {
      if (errorText) message = errorText;
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export async function getOverview(): Promise<HomeOverview> {
  return request<HomeOverview>('/api/home');
}

export async function getEntities(): Promise<{
  entities: readonly Entity[];
  areas: readonly Area[];
  floors: readonly Floor[];
  services: Record<string, readonly string[]>;
}> {
  return request('/api/home/entities');
}

export async function getRooms(): Promise<{ rooms: readonly RoomItem[] }> {
  return request('/api/home/rooms');
}

export async function getEnergy(): Promise<EnergyData> {
  return request<EnergyData>('/api/home/energy');
}

export async function getAutomations(): Promise<{ automations: readonly AutomationItem[] }> {
  return request('/api/home/automations');
}

export async function toggleAutomation(entityId: string, on: boolean): Promise<{ ok: boolean }> {
  return request(`/api/home/automations/${encodeURIComponent(entityId)}/toggle`, {
    method: 'POST',
    body: JSON.stringify({ on }),
  });
}

export async function runAutomation(entityId: string): Promise<{ ok: boolean }> {
  return request(`/api/home/automations/${encodeURIComponent(entityId)}/run`, {
    method: 'POST',
  });
}

export async function controlDevice(
  entityId: string,
  service: string,
  data?: Record<string, unknown>,
  confirm?: boolean
): Promise<{ ok: boolean; state?: string; ms?: number }> {
  return request('/api/home/control', {
    method: 'POST',
    body: JSON.stringify({
      entity_id: entityId,
      service,
      data: data || {},
      confirm: !!confirm,
    }),
  });
}

export async function askAssist(text: string, language: string = 'it'): Promise<AssistResult> {
  return request<AssistResult>('/api/home/assist', {
    method: 'POST',
    body: JSON.stringify({ text, language }),
  });
}

export async function syncHome(): Promise<HomeOverview> {
  return request<HomeOverview>('/api/home/sync', {
    method: 'POST',
  });
}

export async function importPlaces(): Promise<{ added: number }> {
  return request<{ added: number }>('/api/places/import', {
    method: 'POST',
  });
}
