import { asRecord, asString, requestJson } from './http';
import { list, num } from './parse';

export const PRIVACY_LEVELS = ['public', 'personal', 'sensitive'] as const;
export const PRIVACY_REACH = ['local', 'home', 'any'] as const;
export const PRIVACY_PROFILES = ['max', 'balanced', 'open'] as const;
export const PRIVACY_ORIGINS = ['local', 'home', 'remote'] as const;
export const PRIVACY_BUCKETS = [...PRIVACY_ORIGINS, 'blocked'] as const;

export type PrivacyLevel = (typeof PRIVACY_LEVELS)[number];
export type PrivacyReach = (typeof PRIVACY_REACH)[number];
export type PrivacyPreset = (typeof PRIVACY_PROFILES)[number];
export type PrivacyProfile = PrivacyPreset | 'custom';
export type PrivacyOrigin = (typeof PRIVACY_ORIGINS)[number];
export type PrivacyBucket = (typeof PRIVACY_BUCKETS)[number];

export interface PrivacyPolicy {
  readonly profile: PrivacyProfile;
  readonly personal: PrivacyReach;
  readonly sensitive: PrivacyReach;
}

export interface PrivacyPerson {
  readonly slug: string;
  readonly name: string;
  readonly owner: boolean;
  readonly policy: PrivacyPolicy | null;
}

export type PrivacyCounts = Readonly<Record<PrivacyLevel, Readonly<Record<PrivacyBucket, number>>>>;

export interface PrivacyOverview {
  readonly policy: PrivacyPolicy;
  readonly automatic: boolean;
  readonly suggested: PrivacyPolicy;
  readonly engine: { readonly origin: PrivacyOrigin; readonly model: string };
  readonly people: readonly PrivacyPerson[];
  readonly days: number;
  readonly total: PrivacyCounts;
  readonly today: PrivacyCounts;
}

export type PolicyChoice = PrivacyPolicy | { readonly profile: 'auto' } | { readonly profile: 'inherit' };

const SLUG = /^[a-z0-9][a-z0-9_-]{0,63}$/;
const RANK: Readonly<Record<PrivacyReach, number>> = { local: 0, home: 1, any: 2 };
const FALLBACK: PrivacyPolicy = { profile: 'max', personal: 'local', sensitive: 'local' };

const pick = <T extends string>(options: readonly T[], value: unknown): T | null => options.find((item) => item === value) ?? null;

export function parsePolicy(value: unknown): PrivacyPolicy | null {
  const raw = asRecord(value);
  const profile = raw.profile === 'custom' ? 'custom' : pick(PRIVACY_PROFILES, raw.profile);
  const personal = pick(PRIVACY_REACH, raw.personal);
  const sensitive = pick(PRIVACY_REACH, raw.sensitive);
  return profile && personal && sensitive ? { profile, personal, sensitive } : null;
}

function parseCounts(value: unknown): PrivacyCounts {
  const raw = asRecord(value);
  const row = (level: PrivacyLevel) => {
    const counts = asRecord(raw[level]);
    return Object.fromEntries(PRIVACY_BUCKETS.map((bucket) => [bucket, Math.max(0, num(counts[bucket]))])) as Record<PrivacyBucket, number>;
  };
  return { public: row('public'), personal: row('personal'), sensitive: row('sensitive') };
}

function parsePerson(value: unknown): PrivacyPerson | null {
  const raw = asRecord(value);
  const slug = asString(raw.slug, 64);
  if (!slug || !SLUG.test(slug)) {
    return null;
  }
  return { slug, name: asString(raw.name, 120) ?? slug, owner: raw.role === 'owner', policy: parsePolicy(raw.policy) };
}

export function parsePrivacy(value: unknown): PrivacyOverview {
  const raw = asRecord(value);
  const engine = asRecord(raw.engine);
  const audit = asRecord(raw.audit);
  return {
    policy: parsePolicy(raw.default) ?? FALLBACK,
    automatic: raw.automatic === true,
    suggested: parsePolicy(raw.suggested) ?? FALLBACK,
    engine: { origin: pick(PRIVACY_ORIGINS, engine.origin) ?? 'remote', model: asString(engine.model, 230) ?? '' },
    people: list(raw.people).map(parsePerson).filter((p): p is PrivacyPerson => p !== null),
    days: num(audit.days, 30),
    total: parseCounts(audit.levels),
    today: parseCounts(audit.today),
  };
}

export const presetPolicy = (profile: PrivacyPreset): PrivacyPolicy =>
  profile === 'max'
    ? { profile, personal: 'local', sensitive: 'local' }
    : profile === 'balanced'
      ? { profile, personal: 'home', sensitive: 'local' }
      : { profile, personal: 'any', sensitive: 'any' };

export const coherent = (policy: PrivacyPolicy): boolean => RANK[policy.sensitive] <= RANK[policy.personal];

function validate(choice: PolicyChoice): PolicyChoice {
  if ('personal' in choice && !coherent(choice)) {
    throw new RangeError('privacy_sensitive_looser');
  }
  return choice;
}

export async function fetchPrivacy(signal?: AbortSignal): Promise<PrivacyOverview> {
  return parsePrivacy(await requestJson<unknown>('/api/brains/privacy', { signal }));
}

export async function saveDefaultPrivacy(choice: PolicyChoice): Promise<PrivacyOverview> {
  return parsePrivacy(await requestJson<unknown>('/api/brains/privacy/default', { method: 'PUT', body: JSON.stringify(validate(choice)) }));
}

export async function savePersonPrivacy(slug: string, choice: PolicyChoice): Promise<PrivacyOverview> {
  if (!SLUG.test(slug)) {
    throw new RangeError('privacy_unknown_person');
  }
  return parsePrivacy(
    await requestJson<unknown>(`/api/brains/privacy/people/${encodeURIComponent(slug)}`, { method: 'PUT', body: JSON.stringify(validate(choice)) }),
  );
}
