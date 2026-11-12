import { NodeModuleError, asRecord, asString, asStringList, requestJson } from '../../shared/data/http';

export const METRICS = ['cpu', 'ram', 'disk', 'temp'] as const;
export type MetricKey = (typeof METRICS)[number];

export const EDGE_TASKS = ['wake_word', 'vad', 'stt', 'tts', 'vision', 'llm'] as const;
export type EdgeTask = (typeof EDGE_TASKS)[number];
export type EdgeTarget = 'edge' | 'server' | 'unavailable';

export interface EdgeAccelerator {
  readonly id: string;
  readonly vendor: string;
  readonly kind: string;
  readonly ready: boolean;
}

export interface EdgeStep {
  readonly task: EdgeTask;
  readonly target: EdgeTarget;
  readonly backend: string | null;
}

export interface LinkNode {
  readonly id: string;
  readonly name: string;
  readonly type: string;
  readonly room: string | null;
  readonly ip: string | null;
  readonly hostname: string | null;
  readonly version: string | null;
  readonly online: boolean;
  readonly lastSeen: number;
  readonly pairedAt: number;
  readonly capabilities: readonly string[];
  readonly metrics: Readonly<Partial<Record<MetricKey, number>>>;
  readonly uptime: number | null;
  readonly queued: readonly string[];
  readonly soc: string | null;
  readonly accelerators: readonly EdgeAccelerator[];
  readonly offload: readonly EdgeStep[];
}

export interface PendingRequest {
  readonly id: string;
  readonly name: string;
  readonly type: string;
  readonly room: string | null;
  readonly ip: string | null;
  readonly fingerprint: string;
  readonly expires: number;
}

export interface FoundBeacon {
  readonly id: string;
  readonly ip: string | null;
  readonly version: string | null;
  readonly at: number;
}

export interface LinkOverview {
  readonly nodes: readonly LinkNode[];
  readonly pending: readonly PendingRequest[];
  readonly found: readonly FoundBeacon[];
}

export interface PairingCode {
  readonly code: string;
  readonly expiresAt: number;
  readonly fingerprint: string;
}

export const NODE_ID = /^[a-z0-9][a-z0-9-]{2,47}$/;
const IP = /^[0-9a-fA-F:.]{2,45}$/;

const TOKEN = /^[a-z0-9_-]{1,32}$/;
const TARGETS: readonly EdgeTarget[] = ['edge', 'server', 'unavailable'];

const token = (value: unknown): string | null => {
  const text = asString(value, 32);
  return text && TOKEN.test(text) ? text : null;
};

function parseAccelerators(value: unknown): EdgeAccelerator[] {
  return (Array.isArray(value) ? value : []).slice(0, 8).flatMap((item) => {
    const a = asRecord(item);
    const id = token(a.id);
    return id ? [{ id, vendor: asString(a.vendor, 40) ?? id, kind: token(a.kind) ?? 'npu', ready: a.ready === true }] : [];
  });
}

function parseOffload(value: unknown): EdgeStep[] {
  const raw = asRecord(value);
  return EDGE_TASKS.flatMap((task) => {
    const step = asRecord(raw[task]);
    const target = TARGETS.find((candidate) => candidate === step.target);
    return target ? [{ task, target, backend: target === 'edge' ? token(step.backend) : null }] : [];
  });
}

function parseSoc(value: unknown): string | null {
  const soc = asRecord(asRecord(value).soc);
  const label = [asString(soc.vendor, 40), asString(soc.family, 40)].filter(Boolean).join(' ');
  return asString(soc.model, 80) ?? (label || null);
}

const num = (value: unknown): number => (typeof value === 'number' && Number.isFinite(value) ? value : 0);
const ip = (value: unknown): string | null => {
  const text = asString(value, 45);
  return text && IP.test(text) ? text : null;
};

function parseNode(value: unknown): LinkNode | null {
  const n = asRecord(value);
  const id = asString(n.id, 48);
  if (!id || !NODE_ID.test(id)) {
    return null;
  }
  const m = asRecord(n.metrics);
  const metrics: Partial<Record<MetricKey, number>> = {};
  METRICS.forEach((key) => {
    if (typeof m[key] === 'number' && Number.isFinite(m[key])) {
      metrics[key] = m[key] as number;
    }
  });
  return {
    id,
    name: asString(n.name, 60) ?? id,
    type: asString(n.type, 20) ?? 'other',
    room: asString(n.room, 60),
    ip: ip(n.ip),
    hostname: asString(n.hostname, 60),
    version: asString(n.version, 40),
    online: n.online === true,
    lastSeen: num(n.last_seen),
    pairedAt: num(n.paired_at),
    capabilities: asStringList(n.capabilities, 12),
    metrics,
    uptime: typeof m.uptime === 'number' ? m.uptime : null,
    queued: asStringList(n.commands, 5),
    soc: parseSoc(n.hardware),
    accelerators: parseAccelerators(asRecord(n.hardware).accelerators),
    offload: parseOffload(n.offload),
  };
}

function parsePending(value: unknown): PendingRequest | null {
  const r = asRecord(value);
  const id = asString(r.id, 48);
  if (!id || !NODE_ID.test(id)) {
    return null;
  }
  return {
    id,
    name: asString(r.name, 60) ?? id,
    type: asString(r.type, 20) ?? 'other',
    room: asString(r.room, 60),
    ip: ip(r.ip),
    fingerprint: asString(r.fingerprint, 40) ?? '',
    expires: num(r.expires),
  };
}

function parseFound(value: unknown): FoundBeacon | null {
  const f = asRecord(value);
  const id = asString(f.id, 48);
  return id && NODE_ID.test(id) ? { id, ip: ip(f.ip), version: asString(f.version, 20), at: num(f.at) } : null;
}

const list = <T,>(value: unknown, parse: (item: unknown) => T | null): T[] =>
  (Array.isArray(value) ? value : []).slice(0, 64).map(parse).filter((item): item is T => item !== null);

export async function fetchLinks(signal?: AbortSignal): Promise<LinkOverview> {
  const raw = asRecord(await requestJson<unknown>('/api/nodes', { signal }));
  return { nodes: list(raw.nodes, parseNode), pending: list(raw.pending, parsePending), found: list(raw.found, parseFound) };
}

export async function createPairingCode(): Promise<PairingCode> {
  const raw = asRecord(await requestJson<unknown>('/api/nodes/pairing-code', { method: 'POST' }));
  const code = asString(raw.code, 6);
  if (!code || !/^\d{6}$/.test(code)) {
    throw new NodeModuleError('invalid_code', 502);
  }
  return { code, expiresAt: Date.now() + num(raw.expires_in) * 1000, fingerprint: asString(raw.ca_fingerprint, 80) ?? '' };
}

const guard = (id: string): string => {
  if (!NODE_ID.test(id)) {
    throw new NodeModuleError('invalid_node', 400);
  }
  return encodeURIComponent(id);
};

export async function approveRequest(id: string): Promise<void> {
  await requestJson(`/api/nodes/requests/${guard(id)}/approve`, { method: 'POST' });
}

export async function rejectRequest(id: string): Promise<void> {
  await requestJson(`/api/nodes/requests/${guard(id)}`, { method: 'DELETE' });
}

export async function unpairNode(id: string): Promise<void> {
  await requestJson(`/api/nodes/${guard(id)}`, { method: 'DELETE' });
}

export async function downloadSatelliteEnrollment(): Promise<void> {
  const raw = asRecord(await requestJson<unknown>('/api/nodes/satellite-enrollment', { method: 'POST' }));
  const server = asString(raw.server, 300);
  const secret = asString(raw.token, 128);
  const pin = asString(raw.pin, 64);
  if (!server?.startsWith('https://') || !secret || !pin || !/^[0-9a-f]{64}$/.test(pin) || typeof raw.expires !== 'number') {
    throw new NodeModuleError('invalid_enrollment', 502);
  }
  const blob = new Blob([JSON.stringify({ server, token: secret, pin, expires: raw.expires })], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'nuxiva-satellite-enroll.json';
  anchor.rel = 'noopener';
  anchor.click();
  URL.revokeObjectURL(url);
}
