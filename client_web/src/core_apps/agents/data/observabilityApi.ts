import { asRecord, requestJson } from '../../../node_apps/shared/data/http';

export const ALERTS = ['engine_unavailable', 'decision_drift', 'engine_errors', 'memory_cold'] as const;
export type Alert = (typeof ALERTS)[number];
export const MODES = ['python', 'shadow', 'rust'] as const;
export type EngineMode = (typeof MODES)[number];

export interface Observability {
  readonly squad: { readonly agents: number; readonly workers: number; readonly tools: number; readonly busy: number };
  readonly engine: {
    readonly mode: EngineMode;
    readonly available: boolean;
    readonly compared: number;
    readonly matched: number;
    readonly mismatched: number;
    readonly errors: number;
    readonly drift: number;
  };
  readonly memory: { readonly loaded: boolean; readonly persons: number; readonly present: number; readonly version: number; readonly approxBytes: number };
  readonly alerts: readonly Alert[];
}

const count = (value: unknown): number => (typeof value === 'number' && Number.isFinite(value) && value >= 0 ? Math.min(value, 1e12) : 0);

export function parseObservability(raw: unknown): Observability {
  const doc = asRecord(raw);
  const squad = asRecord(doc.squad);
  const engine = asRecord(doc.engine);
  const memory = asRecord(doc.memory);
  const mode = MODES.find((m) => m === engine.mode) ?? 'shadow';
  return {
    squad: { agents: count(squad.agents), workers: count(squad.workers), tools: count(squad.tools), busy: count(squad.busy) },
    engine: {
      mode,
      available: engine.available === true,
      compared: count(engine.compared),
      matched: count(engine.matched),
      mismatched: count(engine.mismatched),
      errors: count(engine.errors),
      drift: Math.min(1, count(engine.drift)),
    },
    memory: {
      loaded: memory.loaded === true,
      persons: count(memory.persons),
      present: count(memory.present),
      version: count(memory.version),
      approxBytes: count(memory.approx_bytes),
    },
    alerts: (Array.isArray(doc.alerts) ? doc.alerts : []).filter((a): a is Alert => ALERTS.some((known) => known === a)),
  };
}

export async function fetchObservability(signal?: AbortSignal): Promise<Observability> {
  return parseObservability(await requestJson<unknown>('/api/team/observability', { signal }));
}
