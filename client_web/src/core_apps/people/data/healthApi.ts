import { NodeModuleError, asRecord, asString, requestJson } from '../../../node_apps/shared/data/http';
import { saveSettings } from '../../shared/featureApi';
import { SLUG } from './peopleApi';

export const HEALTH_GROUPS = ['heart', 'breath', 'body', 'move', 'rest'] as const;
export type HealthGroup = (typeof HEALTH_GROUPS)[number];
const METRIC = /^[a-z0-9_]{2,24}$/;
const KINDS = ['cloud', 'ble', 'push', 'phone', 'camera'] as const;
export const CAMERA_STATES = ['off', 'band', 'busy', 'idle', 'measuring', 'streaming'] as const;
export type CameraVitalsState = (typeof CAMERA_STATES)[number];
const CAMERA_SETTING = 'NUXIVA_RPPG';

export interface HealthValue {
  readonly metric: string;
  readonly value: number;
  readonly unit: string;
  readonly age: number;
  readonly kind: string;
  readonly group: HealthGroup;
}

export interface TrendPoint {
  readonly day: string;
  readonly value: number | null;
}

export interface HealthSignal {
  readonly metric: string;
  readonly code: string;
  readonly level: 'warn' | 'alert';
}

export interface HealthRing {
  readonly metric: string;
  readonly value: number;
  readonly goal: number;
  readonly pct: number;
}

export interface HealthDevice {
  readonly id: string;
  readonly label: string;
  readonly kind: string;
  readonly state: string;
}

export interface CameraVitals {
  readonly enabled: boolean;
  readonly state: CameraVitalsState;
  readonly progress: number;
}

export interface HealthState {
  readonly values: readonly HealthValue[];
  readonly pulse: readonly number[];
  readonly trends: Readonly<Record<string, readonly TrendPoint[]>>;
  readonly recovery: { readonly score: number; readonly band: 'high' | 'mid' | 'low' } | null;
  readonly rings: readonly HealthRing[];
  readonly signals: readonly HealthSignal[];
  readonly cloud: { readonly health: boolean; readonly activity: boolean; readonly state: string; readonly at: number };
  readonly devices: readonly HealthDevice[];
  readonly camera: CameraVitals;
}

const num = (v: unknown): number | null => {
  const n = typeof v === 'string' && v.trim() ? Number(v) : v;
  return typeof n === 'number' && Number.isFinite(n) ? n : null;
};
const list = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
const slugOf = (slug: string): string => {
  if (!SLUG.test(slug)) {
    throw new NodeModuleError('invalid_person', 400);
  }
  return encodeURIComponent(slug);
};

export function parseHealth(input: unknown): HealthState {
  const raw = asRecord(input);
  const groups = asRecord(raw.groups);
  const groupOf = (metric: string): HealthGroup => {
    const g = String(groups[metric] ?? '');
    return (HEALTH_GROUPS as readonly string[]).includes(g) ? (g as HealthGroup) : 'body';
  };
  const values = Object.entries(asRecord(raw.values)).flatMap(([metric, entry]) => {
    const v = asRecord(entry);
    const value = num(v.value);
    const kind = String(v.kind ?? '');
    return METRIC.test(metric) && value !== null
      ? [{ metric, value, unit: asString(v.unit, 12) ?? '', age: Math.max(0, num(v.age) ?? 0), kind: (KINDS as readonly string[]).includes(kind) ? kind : 'push', group: groupOf(metric) }]
      : [];
  });
  const trends: Record<string, TrendPoint[]> = {};
  Object.entries(asRecord(raw.trends)).forEach(([metric, rows]) => {
    if (METRIC.test(metric)) {
      trends[metric] = list(rows).slice(0, 31).map((r) => ({ day: asString(asRecord(r).day, 10) ?? '', value: num(asRecord(r).value) }));
    }
  });
  const recovery = asRecord(raw.recovery);
  const score = num(recovery.score);
  const band = String(recovery.band ?? '');
  const cloud = asRecord(raw.cloud);
  const cam = asRecord(raw.camera);
  const camState = String(cam.state ?? '');
  return {
    values,
    pulse: list(raw.pulse).slice(-120).flatMap((p) => {
      const v = num(Array.isArray(p) ? p[1] : null);
      return v === null ? [] : [v];
    }),
    trends,
    recovery: score !== null && ['high', 'mid', 'low'].includes(band) ? { score: Math.max(0, Math.min(100, score)), band: band as 'high' | 'mid' | 'low' } : null,
    rings: Object.entries(asRecord(raw.goals)).flatMap(([metric, ring]) => {
      const r = asRecord(ring);
      const value = num(r.value), goal = num(r.goal), pct = num(r.pct);
      return METRIC.test(metric) && value !== null && goal && pct !== null ? [{ metric, value, goal, pct }] : [];
    }),
    signals: list(raw.signals).slice(0, 6).flatMap((s) => {
      const r = asRecord(s);
      const metric = String(r.metric ?? ''), code = String(r.code ?? ''), level = r.level === 'alert' ? 'alert' : 'warn';
      return METRIC.test(metric) && METRIC.test(code) ? [{ metric, code, level } as HealthSignal] : [];
    }),
    cloud: { health: cloud.health === true, activity: cloud.activity === true, state: asString(cloud.state, 16) ?? 'idle', at: num(cloud.at) ?? 0 },
    devices: list(raw.devices).slice(0, 8).map(asRecord).flatMap((d) => {
      const id = asString(d.id, 24) ?? '';
      return /^[a-f0-9]{4,24}$/.test(id) ? [{ id, label: asString(d.label, 40) ?? '', kind: asString(d.kind, 8) ?? '', state: asString(d.state, 16) ?? '' }] : [];
    }),
    camera: {
      enabled: cam.enabled === true,
      state: (CAMERA_STATES as readonly string[]).includes(camState) ? (camState as CameraVitalsState) : 'off',
      progress: Math.max(0, Math.min(1, num(cam.progress) ?? 0)),
    },
  };
}

export async function fetchHealth(slug: string, days: number, signal?: AbortSignal): Promise<HealthState> {
  const span = Math.max(7, Math.min(30, Math.round(days)));
  return parseHealth(await requestJson<unknown>(`/api/people/${slugOf(slug)}/health?days=${span}`, { signal }));
}

export async function syncHealth(slug: string): Promise<void> {
  await requestJson<unknown>(`/api/people/${slugOf(slug)}/health/sync`, { method: 'POST' });
}

export async function setCameraVitals(enabled: boolean): Promise<void> {
  await saveSettings('people', { [CAMERA_SETTING]: enabled ? '1' : '0' });
}
