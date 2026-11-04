import { NodeModuleError } from '../../node_apps/shared/data/http';
import { asList, asObject, num, sendJson, text } from '../shared/http';
import { ResetChallenge, ResetDomain, ResetInventory, ResetOptions, ResetReport, ResetRoot } from './types';

const DOMAIN_ID = /^[a-z_]{1,24}$/;
const TOKEN = /^[A-Za-z0-9_-]{20,128}$/;
const PHRASE = /^RESET-[A-Z0-9]{6}$/;
const BACKUP_ID = /^[0-9a-f]{12}$/;
const BASE = '/api/factory-reset';

export const inventoryUrl = (options: ResetOptions): string =>
  `${BASE}/inventory?keep_backups=${options.keepBackups}&include_shares=${options.includeShares}`;

const domain = (raw: unknown): ResetDomain | null => {
  const row = asObject(raw);
  const id = text(row.id);
  return DOMAIN_ID.test(id) ? { id, items: num(row.items), files: num(row.files), bytes: num(row.bytes) } : null;
};

const root = (raw: unknown): ResetRoot => {
  const row = asObject(raw);
  return { name: text(row.name).slice(0, 24), files: num(row.files), bytes: num(row.bytes), failed: num(row.failed) };
};

const names = (raw: unknown): string[] => asList<unknown>(raw).map((item) => text(item).slice(0, 80)).filter(Boolean);

export const parseReport = (raw: unknown): ResetReport | null => {
  const row = asObject(raw);
  const status = text(row.status);
  if (status !== 'verified' && status !== 'incomplete') return null;
  const canaries = asObject(row.canaries);
  const env = asObject(row.env);
  const services = asObject(row.services);
  const leftovers: Record<string, string[]> = {};
  for (const [key, value] of Object.entries(asObject(row.leftovers))) {
    leftovers[key.slice(0, 24)] = names(value);
  }
  return {
    id: text(row.id),
    status,
    finished: num(row.finished),
    roots: asList(row.roots).map(root),
    canariesChecked: num(canaries.checked),
    canariesSurvivors: num(canaries.survivors),
    leftovers,
    openDeleted: num(row.open_deleted),
    kept: names(row.kept),
    notStarted: names(services.not_started),
    skippedMounts: num(row.skipped_mounts),
    envKept: num(env.kept),
    envRotated: num(env.rotated),
    envRemoved: num(env.removed),
  };
};

export const parseInventory = (raw: unknown): ResetInventory => {
  const body = asObject(raw);
  return {
    domains: asList(body.domains).map(domain).filter((item): item is ResetDomain => item !== null),
    files: num(body.files),
    bytes: num(body.bytes),
    blockers: names(body.blockers),
    waitSeconds: Math.max(1, num(body.wait_seconds, 8)),
    ttl: Math.max(30, num(body.ttl, 180)),
    last: parseReport(body.last),
  };
};

export const openChallenge = async (password: string, options: ResetOptions): Promise<ResetChallenge> => {
  const body = asObject(
    await sendJson(`${BASE}/challenge`, 'POST', { password, keep_backups: options.keepBackups, include_shares: options.includeShares }),
  );
  const token = text(body.token);
  const phrase = text(body.phrase);
  if (!TOKEN.test(token) || !PHRASE.test(phrase)) throw new NodeModuleError('challenge_invalid', 502);
  return { token, phrase, waitSeconds: Math.max(1, num(body.wait_seconds, 8)), expiresIn: Math.max(30, num(body.expires_in, 180)) };
};

export const runReset = async (challenge: ResetChallenge, phrase: string, options: ResetOptions): Promise<string> => {
  const body = asObject(
    await sendJson(`${BASE}/execute`, 'POST', {
      token: challenge.token,
      phrase,
      keep_backups: options.keepBackups,
      include_shares: options.includeShares,
    }),
  );
  return text(body.id).slice(0, 32);
};

export type ProbeResult = { readonly kind: 'down' } | { readonly kind: 'signed_out' } | { readonly kind: 'report'; readonly report: ResetReport | null };

export const probe = async (): Promise<ProbeResult> => {
  try {
    const response = await fetch(`${BASE}/report`, { cache: 'no-store', headers: { Accept: 'application/json' } });
    if (response.status === 401 || response.status === 403) return { kind: 'signed_out' };
    if (response.status === 404) return { kind: 'report', report: null };
    if (!response.ok) return { kind: 'down' };
    return { kind: 'report', report: parseReport(await response.json()) };
  } catch {
    return { kind: 'down' };
  }
};

export const createBackup = async (): Promise<string> => {
  const id = text(asObject(await sendJson('/api/backup', 'POST', {})).id);
  if (!BACKUP_ID.test(id)) throw new NodeModuleError('backup_failed', 502);
  return `/api/backup/${id}/download`;
};

const KNOWN_REASONS: readonly string[] = [
  'invalid_credentials', 'too_many_attempts', 'system_busy', 'reset_running', 'challenge_invalid', 'challenge_too_early',
  'challenge_options_changed', 'phrase_mismatch', 'backup_failed',
];

export const reasonCode = (cause: unknown): string =>
  cause instanceof NodeModuleError && KNOWN_REASONS.includes(cause.code) ? cause.code : 'generic';
