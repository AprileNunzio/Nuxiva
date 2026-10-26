import { asRecord, asString, requestJson } from './http';

export interface AudioDevice {
  readonly name: string;
  readonly label: string;
  readonly kind: string;
}

export interface AudioChannel {
  readonly volume: number;
  readonly muted: boolean;
  readonly device: string | null;
}

export interface LocalAudioState {
  readonly available: boolean;
  readonly error: string | null;
  readonly output: AudioChannel;
  readonly input: AudioChannel;
  readonly outputs: readonly AudioDevice[];
  readonly inputs: readonly AudioDevice[];
}

export type AudioSide = 'output' | 'input';

export interface AudioChange {
  readonly device?: string;
  readonly volume?: number;
  readonly muted?: boolean;
}

function channel(value: unknown): AudioChannel {
  const raw = asRecord(value);
  const volume = typeof raw.volume === 'number' && Number.isFinite(raw.volume) ? Math.min(150, Math.max(0, raw.volume)) : 0;
  return { volume, muted: raw.muted === true, device: asString(raw.device, 256) };
}

function devices(value: unknown): AudioDevice[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map(asRecord)
    .map((d) => ({ name: asString(d.name, 256) ?? '', label: asString(d.label, 160) ?? '', kind: asString(d.kind, 16) ?? '' }))
    .filter((d) => d.name && d.label)
    .slice(0, 64);
}

function parse(payload: unknown): LocalAudioState {
  const raw = asRecord(payload);
  return {
    available: raw.available === true,
    error: asString(raw.error),
    output: channel(raw.output),
    input: channel(raw.input),
    outputs: devices(raw.outputs),
    inputs: devices(raw.inputs),
  };
}

export async function fetchLocalAudio(signal?: AbortSignal): Promise<LocalAudioState> {
  return parse(await requestJson<unknown>('/api/audio', { signal }));
}

export async function updateLocalAudio(side: AudioSide, change: AudioChange): Promise<LocalAudioState> {
  const body: Record<string, AudioChange> = { [side]: change };
  return parse(await requestJson<unknown>('/api/audio', { method: 'PUT', body: JSON.stringify(body) }));
}
