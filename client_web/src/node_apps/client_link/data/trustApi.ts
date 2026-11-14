import { NodeModuleError, asRecord, asString, requestJson } from '../../shared/data/http';

export const PROFILES = ['satellite', 'second_server', 'auto'] as const;
export type NodeProfile = (typeof PROFILES)[number];
export type NodeMode = 'satellite' | 'second_server';
export const ELEVATED_GRANTS = ['fs.write', 'process.exec', 'device.control'] as const;

const SCOPE = /^[a-z0-9_]{1,24}(\.[a-z0-9_]{1,24}){1,2}$/;
const NODE_ID = /^[a-z0-9][a-z0-9-]{2,47}$/;
const FINGERPRINT = /^[0-9A-F]{4}(-[0-9A-F]{4}){2}$/;

export interface NodeTrust {
  readonly profile: NodeProfile;
  readonly mode: NodeMode;
  readonly allowed: boolean;
  readonly grants: readonly string[];
  readonly effective: readonly string[];
  readonly denied: readonly string[];
  readonly rejected: readonly string[];
  readonly legacy: boolean;
  readonly fingerprint: string;
  readonly cpuCores: number;
  readonly ramMb: number;
}

export interface AuditEntry {
  readonly seq: number;
  readonly ts: number;
  readonly actor: string;
  readonly node: string;
  readonly action: string;
  readonly detail: string;
}

export interface AuditReport {
  readonly entries: readonly AuditEntry[];
  readonly intact: boolean;
  readonly brokenAt: number | null;
  readonly count: number;
}

const scopes = (value: unknown): string[] =>
  (Array.isArray(value) ? value : [])
    .slice(0, 64)
    .filter((item): item is string => typeof item === 'string' && SCOPE.test(item));

const num = (value: unknown): number => (typeof value === 'number' && Number.isFinite(value) ? value : 0);

export function parseTrust(value: unknown): NodeTrust {
  const t = asRecord(value);
  const profile = PROFILES.find((p) => p === t.profile) ?? 'satellite';
  const rejected = (Array.isArray(t.rejected) ? t.rejected : [])
    .slice(0, 64)
    .map((item) => asString(item, 48))
    .filter((item): item is string => item !== null);
  const fingerprint = asString(t.fingerprint, 14) ?? '';
  return {
    profile,
    mode: t.mode === 'second_server' ? 'second_server' : 'satellite',
    allowed: t.second_server_allowed === true,
    grants: scopes(t.grants).filter((g) => (ELEVATED_GRANTS as readonly string[]).includes(g)),
    effective: scopes(t.effective),
    denied: scopes(t.denied),
    rejected,
    legacy: t.legacy !== false,
    fingerprint: FINGERPRINT.test(fingerprint) ? fingerprint : '',
    cpuCores: num(t.cpu_cores),
    ramMb: num(t.ram_mb),
  };
}

export interface TrustChange {
  readonly profile: NodeProfile;
  readonly allow: boolean;
  readonly grants: readonly string[];
}

const guard = (id: string): string => {
  if (!NODE_ID.test(id)) {
    throw new NodeModuleError('invalid_node', 400);
  }
  return encodeURIComponent(id);
};

export async function setNodeTrust(id: string, change: TrustChange): Promise<void> {
  await requestJson(`/api/nodes/${guard(id)}/trust`, {
    method: 'PUT',
    body: JSON.stringify({ profile: change.profile, allow_second_server: change.allow, grants: change.grants }),
  });
}

function parseEntry(value: unknown): AuditEntry | null {
  const e = asRecord(value);
  const action = asString(e.action, 48);
  return action && typeof e.seq === 'number'
    ? { seq: e.seq, ts: num(e.ts), actor: asString(e.actor, 64) ?? '', node: asString(e.node, 64) ?? '', action, detail: asString(e.detail, 512) ?? '' }
    : null;
}

export async function fetchAudit(signal?: AbortSignal): Promise<AuditReport> {
  const raw = asRecord(await requestJson<unknown>('/api/nodes/audit?limit=50', { signal }));
  const verify = asRecord(raw.verify);
  return {
    entries: (Array.isArray(raw.entries) ? raw.entries : []).slice(0, 50).map(parseEntry).filter((e): e is AuditEntry => e !== null),
    intact: verify.ok === true,
    brokenAt: typeof verify.broken_at === 'number' ? verify.broken_at : null,
    count: num(verify.entries),
  };
}
