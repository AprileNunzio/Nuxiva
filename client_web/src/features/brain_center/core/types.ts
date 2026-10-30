export type Origin = 'local' | 'server' | 'cloud' | 'lan';

export interface BrainRef {
  readonly ref: string;
  readonly model: string;
  readonly origin: Origin;
  readonly provider: string;
  readonly available: boolean;
}

export const ROUTING = ['auto', '1', '0'] as const;
export type Routing = (typeof ROUTING)[number];

export const SCOPES = ['anywhere', 'home_first', 'home'] as const;
export type RoleScope = (typeof SCOPES)[number];

export const STRATEGIES = ['order', 'fastest'] as const;
export type RoleStrategy = (typeof STRATEGIES)[number];

export interface RoleState {
  readonly id: string;
  readonly custom: boolean;
  readonly entries: readonly BrainRef[];
  readonly effective: readonly string[];
  readonly active: BrainRef | null;
  readonly scope: RoleScope;
  readonly strategy: RoleStrategy;
}

export interface Fit {
  readonly level: 'ok' | 'slow' | 'no';
  readonly tps: number;
  readonly where: string;
}

export interface CatalogModel {
  readonly name: string;
  readonly label: string;
  readonly sizeGb: number | null;
  readonly category: string;
  readonly installed: boolean;
  readonly fit: Fit;
  readonly restricted: boolean;
}

export interface Hardware {
  readonly ramGb: number;
  readonly vramGb: number;
  readonly gpu: string | null;
}

export interface LastAnswer {
  readonly ref: BrainRef;
  readonly ms: number;
  readonly at: number;
}

export interface BrainOverview {
  readonly routing: Routing;
  readonly roles: readonly RoleState[];
  readonly catalog: readonly CatalogModel[];
  readonly hardware: Hardware;
  readonly last: LastAnswer | null;
}

export interface RouteResult {
  readonly kind: string;
  readonly models: readonly string[];
}

export interface CloudProvider {
  readonly id: string;
  readonly name: string;
  readonly baseUrl: string;
  readonly keyUrl: string | null;
  readonly needsUrl: boolean;
  readonly keyOptional: boolean;
  readonly configured: boolean;
  readonly hasKey: boolean;
  readonly keyHint: string;
  readonly enabled: boolean;
}

export interface ProviderChange {
  readonly key?: string;
  readonly base_url?: string;
  readonly enabled?: boolean;
}

export interface ProviderTest {
  readonly ok: boolean;
  readonly detail: string;
  readonly ms: number;
}

export type ServerFlavor = 'ollama' | 'openai';

export interface ModelServer {
  readonly id: string;
  readonly name: string;
  readonly flavor: ServerFlavor;
  readonly url: string;
  readonly online: boolean;
  readonly models: readonly string[];
}

export interface NewServer {
  readonly name: string;
  readonly flavor: ServerFlavor;
  readonly url: string;
  readonly key: string;
}

export interface LocalModel {
  readonly name: string;
  readonly size: number;
  readonly loaded: boolean;
}

export interface PullProgress {
  readonly name: string;
  readonly percent: number;
}

export interface UsageRow {
  readonly id: string;
  readonly tokensIn: number;
  readonly tokensOut: number;
  readonly calls: number;
  readonly budget: number | null;
}

export interface UsageSummary {
  readonly month: string;
  readonly today: number;
  readonly total: number;
  readonly cloud: number;
  readonly globalBudget: number | null;
  readonly providerBudgets: Readonly<Record<string, number>>;
  readonly providers: readonly UsageRow[];
  readonly models: readonly UsageRow[];
  readonly days: readonly { readonly date: string; readonly tokens: number }[];
}

export interface Budgets {
  readonly global: number | null;
  readonly providers: Readonly<Record<string, number | null>>;
}

export type AssignmentMode = 'inherit' | 'first' | 'only';

export interface FunctionRow {
  readonly id: string;
  readonly group: string;
  readonly side: 'supervisor' | 'core';
  readonly role: string;
  readonly defaultRole: string;
  readonly mode: AssignmentMode;
  readonly order: readonly string[];
  readonly chain: readonly BrainRef[];
}
