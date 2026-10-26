export const STATES = ['active', 'paused', 'archived'] as const;
export const KINDS = ['assistant', 'sensor', 'home', 'knowledge', 'comms', 'media', 'system', 'custom'] as const;
export const CATEGORIES = ['assistente', 'percezione', 'casa', 'conoscenza', 'comunicazione', 'intrattenimento', 'sistema', 'altro'] as const;
export const ORIGINS = ['user', 'nuxiva'] as const;
export const LINK_KINDS = ['tool', 'widget'] as const;

export type AgentState = (typeof STATES)[number];
export type AgentKind = (typeof KINDS)[number];
export type AgentCategory = (typeof CATEGORIES)[number];
export type AgentOrigin = (typeof ORIGINS)[number];
export type LinkKind = (typeof LINK_KINDS)[number];

export interface FleetAgent {
  readonly id: string;
  readonly name: string;
  readonly kind: AgentKind;
  readonly category: AgentCategory;
  readonly state: AgentState;
  readonly priority: number;
  readonly origin: AgentOrigin;
  readonly description: string;
  readonly created: number;
  readonly updated: number;
  readonly tools: readonly string[];
  readonly widgets: readonly string[];
}

export interface FleetAgentDetail extends FleetAgent {
  readonly instructions: string;
  readonly missing_tools: readonly string[];
  readonly missing_widgets: readonly string[];
}

export interface FleetPage {
  readonly items: readonly FleetAgent[];
  readonly next: string;
  readonly more: boolean;
}

export interface FleetSummary {
  readonly total: number;
  readonly shards: number;
  readonly shards_used: number;
  readonly state: Readonly<Record<string, number>>;
  readonly kind: Readonly<Record<string, number>>;
  readonly category: Readonly<Record<string, number>>;
  readonly origin: Readonly<Record<string, number>>;
}

export interface FleetFilters {
  readonly q: string;
  readonly state: string;
  readonly kind: string;
  readonly category: string;
  readonly origin: string;
}

export interface CatalogItem {
  readonly id: string;
  readonly name: string;
  readonly description: string;
}

export interface AgentDraft {
  readonly name: string;
  readonly description: string;
  readonly kind: AgentKind;
  readonly category: AgentCategory;
  readonly instructions: string;
  readonly tools: readonly string[];
  readonly widgets: readonly string[];
}

export const EMPTY_FILTERS: FleetFilters = { q: '', state: '', kind: '', category: '', origin: '' };
