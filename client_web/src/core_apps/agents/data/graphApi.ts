import { asRecord, asString, requestJson } from '../../../node_apps/shared/data/http';

export const EXPLORE_MODES = ['neighbors', 'impact', 'locate', 'path'] as const;
export type ExploreMode = (typeof EXPLORE_MODES)[number];

export interface GraphOverview {
  readonly available: boolean;
  readonly files: number;
  readonly packages: number;
  readonly symbols: number;
  readonly sections: number;
  readonly edges: number;
  readonly skipped: number;
}

export interface PlanStep {
  readonly id: string;
  readonly agent: string;
  readonly intent: string;
  readonly goal: string;
  readonly outcome: string;
}

export interface Consultation {
  readonly at: number;
  readonly who: string;
  readonly tool: string;
  readonly target: string;
  readonly ok: boolean;
  readonly ms: number;
}

export interface ShadowGate {
  readonly observedDays: number;
  readonly cleanDays: number;
  readonly windowMismatches: number;
  readonly streak: number;
  readonly ready: boolean;
}

export interface GraphSnapshot {
  readonly graph: GraphOverview;
  readonly plan: { readonly at: number; readonly steps: readonly PlanStep[]; readonly done: number } | null;
  readonly consultations: readonly Consultation[];
  readonly shadow: {
    readonly persistent: boolean;
    readonly compared: number;
    readonly mismatched: number;
    readonly errors: number;
    readonly gate: ShadowGate;
  };
}

export interface ExploreItem {
  readonly name: string;
  readonly kind: string;
  readonly path: string;
  readonly line: number;
  readonly depth: number;
  readonly via: string;
}

export interface ExploreResult {
  readonly ok: boolean;
  readonly error: string;
  readonly items: readonly ExploreItem[];
  readonly truncated: boolean;
}

const MAX_ROWS = 200;
const count = (value: unknown): number => (typeof value === 'number' && Number.isFinite(value) && value >= 0 ? Math.min(value, 1e12) : 0);
const list = (value: unknown): unknown[] => (Array.isArray(value) ? value.slice(0, MAX_ROWS) : []);
const text = (value: unknown, max = 160): string => asString(value, max) ?? '';

export function parseGraph(raw: unknown): GraphSnapshot {
  const doc = asRecord(raw);
  const graph = asRecord(doc.graph);
  const shadow = asRecord(doc.shadow);
  const totals = asRecord(shadow.totals);
  const gate = asRecord(shadow.gate);
  const plan = doc.plan === null || doc.plan === undefined ? null : asRecord(doc.plan);
  return {
    graph: {
      available: graph.available === true,
      files: count(graph.files),
      packages: count(graph.packages),
      symbols: count(graph.symbols),
      sections: count(graph.sections),
      edges: count(graph.edges),
      skipped: count(graph.skipped),
    },
    plan: plan
      ? {
          at: count(plan.at),
          done: count(plan.done),
          steps: list(plan.steps).map((row) => {
            const step = asRecord(row);
            return { id: text(step.id, 40), agent: text(step.agent, 60), intent: text(step.intent), goal: text(step.goal), outcome: text(step.outcome, 80) };
          }),
        }
      : null,
    consultations: list(doc.consultations).map((row) => {
      const item = asRecord(row);
      return { at: count(item.at), who: text(item.who, 40), tool: text(item.tool, 40), target: text(item.target, 120), ok: item.ok === true, ms: count(item.ms) };
    }),
    shadow: {
      persistent: shadow.persistent === true,
      compared: count(totals.compared),
      mismatched: count(totals.mismatched),
      errors: count(totals.errors),
      gate: {
        observedDays: count(gate.observed_days),
        cleanDays: count(gate.clean_days),
        windowMismatches: count(gate.window_mismatches),
        streak: count(gate.streak),
        ready: gate.ready === true,
      },
    },
  };
}

export function parseExplore(raw: unknown): ExploreResult {
  const doc = asRecord(raw);
  return {
    ok: doc.ok === true,
    error: text(doc.error, 80),
    truncated: doc.truncated === true,
    items: list(doc.items).map((row) => {
      const item = asRecord(row);
      return { name: text(item.name, 120), kind: text(item.kind, 24), path: text(item.path, 240), line: count(item.line), depth: count(item.depth), via: text(item.via, 24) };
    }),
  };
}

export async function fetchGraph(signal?: AbortSignal): Promise<GraphSnapshot> {
  return parseGraph(await requestJson<unknown>('/api/team/graph', { signal }));
}

export async function exploreGraph(mode: ExploreMode, target: string, depth: number, other: string, signal?: AbortSignal): Promise<ExploreResult> {
  const query = new URLSearchParams({ mode, target, depth: String(depth), other });
  return parseExplore(await requestJson<unknown>(`/api/team/graph/explore?${query.toString()}`, { signal }));
}
