import { requestJson } from '../../node_apps/shared/data/http';

export interface StudioEQ {
  bass: number;
  low_mid: number;
  mid: number;
  presence: number;
  air: number;
}

export interface StudioFX {
  pitch: number;
  speed: number;
  deesser: number;
  reverb: number;
  compressor: number;
}

export interface StudioVoice {
  id: string;
  name: string;
  language: string;
  kind?: string;
  eq?: Partial<StudioEQ>;
  fx?: Partial<StudioFX>;
  base_voice?: string;
}

export interface StudioStatus {
  enabled: boolean;
  online: boolean;
  where: string;
  engine?: string;
  error: string;
  install: { status?: string; progress?: number; message?: string; error?: string };
  voices: StudioVoice[];
  nuxiva_voice: string;
  sentences: Record<string, string>;
  choices: Record<string, { value: string; title: string; icon: string }[]>;
  presets?: Record<string, Partial<StudioEQ & StudioFX>>;
}

export const fetchStudio = (signal?: AbortSignal) => requestJson<StudioStatus>('/api/voicestudio', { signal });
export const designVoice = (body: Record<string, any>) => requestJson('/api/voicestudio/design', { method: 'POST', body: JSON.stringify(body) });
export const useVoice = (voice: string) => requestJson('/api/voicestudio/use', { method: 'PUT', body: JSON.stringify({ voice }) });
export const deleteVoice = (voice: string) => requestJson(`/api/voicestudio/voices/${encodeURIComponent(voice)}`, { method: 'DELETE' });
export const retryStudio = () => requestJson('/api/voicestudio/retry', { method: 'POST' });
export const saveVoiceSettings = (voice: string, eq: StudioEQ, fx: StudioFX) =>
  requestJson(`/api/voicestudio/voices/${encodeURIComponent(voice)}/settings`, {
    method: 'PUT',
    body: JSON.stringify({ eq, fx }),
  });

async function audioRequest(path: string, init: RequestInit): Promise<Response> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(typeof data.detail === 'string' ? data.detail : `HTTP ${response.status}`);
  }
  return response;
}

export async function previewVoice(
  voice: string,
  language: string,
  options?: {
    text?: string;
    speed?: number;
    eq?: Partial<StudioEQ>;
    fx?: Partial<StudioFX>;
  }
): Promise<Blob> {
  const response = await audioRequest('/api/voicestudio/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      voice,
      language,
      text: options?.text,
      speed: options?.speed ?? 1.0,
      eq: options?.eq,
      fx: options?.fx,
    }),
  });
  return response.blob();
}

export async function cloneVoice(name: string, language: string, audio: Blob | File, filename?: string): Promise<void> {
  const form = new FormData();
  form.append('name', name);
  form.append('language', language);
  form.append('consent', '1');
  const fname = filename || (audio instanceof File ? audio.name : 'recording.webm');
  form.append('audio', audio, fname);
  await audioRequest('/api/voicestudio/clone', { method: 'POST', body: form });
}
