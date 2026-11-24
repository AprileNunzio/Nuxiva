export type Backend = 'ollama' | 'openai';
export type Category = 'simple' | 'composite' | 'novel' | 'adversarial';
export type Effect = 'read' | 'write' | 'send_external' | 'spend' | 'physical';
export type RunState = 'queued' | 'running' | 'completed' | 'cancelled' | 'failed' | 'interrupted';

export const CATEGORIES: readonly Category[] = ['simple', 'composite', 'novel', 'adversarial'];
export const EFFECTS: readonly Effect[] = ['read', 'write', 'send_external', 'spend', 'physical'];
export const BACKENDS: readonly Backend[] = ['ollama', 'openai'];
export const FINAL_STATES: readonly RunState[] = ['completed', 'cancelled', 'failed', 'interrupted'];

export interface Status {
  native: boolean;
  max_active: number;
  active: number;
  max_cases: number;
  max_concurrency: number;
  backends: Backend[];
}

export interface Scenario {
  id: string;
  category: Category;
  expected: { intent: string; effects: Effect[] };
  external_content?: string | null;
  texts: Record<string, string>;
}

export interface Summary {
  scenarios: number;
  cases: number;
  by_language: Record<string, number>;
  by_category: Record<string, number>;
}

export interface DatasetRow {
  id: string;
  name: string;
  updated: number;
  summary: Partial<Summary>;
}

export interface Dataset {
  id: string;
  name: string;
  scenarios: Scenario[];
  summary: Partial<Summary>;
}

export interface Profile {
  id: string;
  name: string;
  backend: Backend;
  base_url: string;
  model: string;
  timeout_seconds: number;
}

export interface Run {
  id: string;
  dataset: string;
  dataset_name: string;
  backend: Backend;
  base_url: string;
  model: string;
  state: RunState;
  total: number;
  done: number;
  failed_calls: number;
  started: number;
  finished: number | null;
  error: string | null;
  label: string;
  concurrency: number;
}

export interface Slice {
  cases: number;
  intent_match: number;
  success: number;
  wrong_actions: number;
  intent_rate: number;
  success_rate: number;
}

export interface Stats {
  n: number;
  mean: number;
  p50: number;
  p95: number;
  p99: number;
  max: number;
}

export interface Report {
  overall: Slice;
  by_language: Record<string, Slice>;
  by_category: Record<string, Slice>;
  language_gap_points: number;
  tokens: Stats;
  latency_ms: Stats;
}

export interface RunReport {
  run: Run;
  report: Report | null;
}

export interface Row {
  case_id: string;
  lang: string;
  category: Category;
  text: string;
  expected_intent: string;
  expected_effects: Effect[];
  intent: string;
  effects: Effect[];
  completed: boolean;
  intent_match: boolean;
  success: boolean;
  wrong_action: boolean;
  tokens: number;
  latency_ms: number;
}

export interface RunSpec {
  dataset: string;
  backend: Backend;
  base_url: string;
  model: string;
  key: string | null;
  label: string;
  languages: string[];
  categories: Category[];
  limit: number;
  concurrency: number;
  timeout_seconds: number;
}
