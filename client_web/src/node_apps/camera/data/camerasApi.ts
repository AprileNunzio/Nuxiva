import { asRecord, asString, requestJson } from '../../shared/data/http';

export interface CameraOptions {
  readonly alias: string;
  readonly room: string;
  readonly rotate: number;
  readonly mirror: boolean;
  readonly motion: boolean;
  readonly sensitivity: number;
  readonly photo_on_motion: boolean;
  readonly favorite: boolean;
  readonly hidden: boolean;
}

export interface CameraSource {
  readonly id: string;
  readonly name: string;
  readonly kind: 'local' | 'infrared' | 'ip';
  readonly main: boolean;
  readonly ir: boolean;
  readonly stream: boolean;
  readonly controllable: boolean;
  readonly clientTransform: boolean;
  readonly options: CameraOptions;
  readonly photos: number;
}

export interface CameraOverview {
  readonly sources: readonly CameraSource[];
  readonly problems: readonly string[];
  readonly tools: { readonly ffmpeg: boolean; readonly v4l2: boolean; readonly recording: boolean };
}

export interface CameraControl {
  readonly name: string;
  readonly type: string;
  readonly min: number;
  readonly max: number;
  readonly step: number;
  readonly default: number;
  readonly value: number;
  readonly inactive: boolean;
  readonly menu: readonly { readonly value: number; readonly label: string }[];
}

export interface CameraPhoto {
  readonly name: string;
  readonly size: number;
  readonly at: number;
}

const SOURCE_ID = /^[A-Za-z0-9_.:-]{1,80}$/;
const PHOTO_NAME = /^photo_[A-Za-z0-9_.-]{1,80}\.jpg$/;
const ROTATIONS = new Set([0, 90, 180, 270]);

const num = (value: unknown, fallback = 0): number => (typeof value === 'number' && Number.isFinite(value) ? value : fallback);

function parseOptions(value: unknown): CameraOptions {
  const o = asRecord(value);
  const rotate = num(o.rotate);
  return {
    alias: asString(o.alias, 40) ?? '',
    room: asString(o.room, 40) ?? '',
    rotate: ROTATIONS.has(rotate) ? rotate : 0,
    mirror: o.mirror === true,
    motion: o.motion === true,
    sensitivity: Math.min(10, Math.max(1, num(o.sensitivity, 5))),
    photo_on_motion: o.photo_on_motion === true,
    favorite: o.favorite === true,
    hidden: o.hidden === true,
  };
}

function parseSource(value: unknown): CameraSource | null {
  const s = asRecord(value);
  const id = asString(s.id, 80);
  if (!id || !SOURCE_ID.test(id)) {
    return null;
  }
  const kind = s.kind === 'local' || s.kind === 'infrared' || s.kind === 'ip' ? s.kind : 'ip';
  const usage = asRecord(s.usage);
  return {
    id,
    name: asString(s.name, 80) ?? id,
    kind,
    main: s.main === true,
    ir: s.ir === true,
    stream: s.stream === true,
    controllable: s.controllable === true,
    clientTransform: s.client_transform === true,
    options: parseOptions(s.options),
    photos: num(usage.photos),
  };
}

export const sourcePath = (id: string, suffix = ''): string => `/api/cameras/source/${encodeURIComponent(id)}${suffix}`;
export const liveUrl = (id: string, stream: boolean): string =>
  `/api/cameras/live/${encodeURIComponent(id)}.${stream ? 'mjpg' : 'jpg'}`;
export const photoUrl = (id: string, name: string): string => sourcePath(id, `/photos/${encodeURIComponent(name)}`);

export async function fetchOverview(signal?: AbortSignal): Promise<CameraOverview> {
  const raw = asRecord(await requestJson<unknown>('/api/cameras/overview', { signal }));
  const tools = asRecord(raw.tools);
  return {
    sources: (Array.isArray(raw.sources) ? raw.sources : []).map(parseSource).filter((s): s is CameraSource => s !== null),
    problems: (Array.isArray(raw.problems) ? raw.problems : []).map((p) => asString(p, 200)).filter((p): p is string => p !== null),
    tools: { ffmpeg: tools.ffmpeg === true, v4l2: tools.v4l2 === true, recording: tools.recording === true },
  };
}

export async function saveOptions(id: string, options: Partial<CameraOptions>): Promise<CameraOptions> {
  return parseOptions(await requestJson<unknown>(sourcePath(id, '/options'), { method: 'PUT', body: JSON.stringify(options) }));
}

export async function fetchControls(id: string, signal?: AbortSignal): Promise<CameraControl[]> {
  const raw = asRecord(await requestJson<unknown>(sourcePath(id, '/controls'), { signal }));
  return (Array.isArray(raw.controls) ? raw.controls : []).map(asRecord).map((c) => ({
    name: asString(c.name, 64) ?? '',
    type: asString(c.type, 16) ?? 'int',
    min: num(c.min),
    max: num(c.max, 1),
    step: Math.max(1, num(c.step, 1)),
    default: num(c.default),
    value: num(c.value),
    inactive: c.inactive === true,
    menu: (Array.isArray(c.menu) ? c.menu : []).map(asRecord).map((m) => ({ value: num(m.value), label: asString(m.label, 60) ?? '' })),
  })).filter((c) => /^[a-z0-9_]{1,64}$/.test(c.name));
}

export async function setControl(id: string, name: string, value: number): Promise<void> {
  await requestJson(sourcePath(id, '/controls'), { method: 'PUT', body: JSON.stringify({ name, value: Math.round(value) }) });
}

export async function resetControls(id: string): Promise<void> {
  await requestJson(sourcePath(id, '/controls/reset'), { method: 'POST' });
}

export async function takePhoto(id: string): Promise<void> {
  await requestJson(sourcePath(id, '/photo'), { method: 'POST' });
}

export async function fetchPhotos(id: string, signal?: AbortSignal): Promise<CameraPhoto[]> {
  const raw = asRecord(await requestJson<unknown>(sourcePath(id, '/photos'), { signal }));
  return (Array.isArray(raw.photos) ? raw.photos : [])
    .map(asRecord)
    .map((p) => ({ name: asString(p.name, 100) ?? '', size: num(p.size), at: num(p.at) }))
    .filter((p) => PHOTO_NAME.test(p.name))
    .slice(0, 60);
}

export async function deletePhoto(id: string, name: string): Promise<void> {
  if (!PHOTO_NAME.test(name)) {
    throw new Error('invalid_photo');
  }
  await requestJson(sourcePath(id, `/photos/${encodeURIComponent(name)}`), { method: 'DELETE' });
}
