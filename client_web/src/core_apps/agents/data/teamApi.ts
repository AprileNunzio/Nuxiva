import { NodeModuleError, asRecord, asString, asStringList, requestJson } from '../../../node_apps/shared/data/http';

export const AGENT_ID = /^[a-z0-9][a-z0-9_-]{1,40}$/;
export const NEW_AGENT_ID = /^[a-z][a-z0-9_-]{2,40}$/;
export const TOOL_NAME = /^[a-z][a-z0-9_]{2,40}$/;
export const PARAM_NAME = /^[a-z][a-z0-9_]{0,30}$/;
export const MODES = ['auto', '1', '0'] as const;
export const CATEGORIES = ['assistente', 'percezione', 'casa', 'conoscenza', 'comunicazione', 'intrattenimento', 'sistema', 'altro'] as const;
export type Mode = (typeof MODES)[number];

export interface AgentSetting {
  readonly key: string;
  readonly label: string;
  readonly type: string;
  readonly value: string;
  readonly options: readonly string[];
}

export interface ToolInfo {
  readonly name: string;
  readonly description: string;
  readonly args: Readonly<Record<string, string>>;
  readonly confirm: boolean;
  readonly conditionalConfirm: boolean;
  readonly alwaysConfirm: boolean;
  readonly enabled: boolean;
  readonly owner: string;
  readonly defaultOwner: string;
  readonly custom: boolean;
}

export interface WidgetInfo {
  readonly id: string;
  readonly name: string;
  readonly icon: string;
  readonly source: string;
  readonly agent: string;
  readonly defaultAgent: string;
  readonly people: readonly string[];
  readonly enabled: boolean;
  readonly personal: boolean;
}

export interface Agent {
  readonly id: string;
  readonly name: string;
  readonly icon: string;
  readonly category: string;
  readonly source: string;
  readonly priority: number;
  readonly defaultPriority: number;
  readonly enabled: boolean;
  readonly reason: string;
  readonly toggle: boolean;
  readonly mode: string;
  readonly fixed: boolean;
  readonly description: string;
  readonly can: readonly string[];
  readonly settings: readonly AgentSetting[];
  readonly instructions: string;
  readonly doing: string;
  readonly inbox: number;
}

export interface BoardMessage {
  readonly at: number;
  readonly from: string;
  readonly to: string;
  readonly text: string;
  readonly kind: string;
}

export interface Person {
  readonly slug: string;
  readonly name: string;
}

export interface TeamOverview {
  readonly agents: readonly Agent[];
  readonly tools: readonly ToolInfo[];
  readonly widgets: readonly WidgetInfo[];
  readonly people: readonly Person[];
  readonly messages: readonly BoardMessage[];
}

const num = (value: unknown, fallback = 0): number => (typeof value === 'number' && Number.isFinite(value) ? value : fallback);
const list = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);

function parseArgs(value: unknown): Record<string, string> {
  const raw = asRecord(value);
  return Object.fromEntries(
    Object.entries(raw)
      .filter(([k]) => PARAM_NAME.test(k))
      .slice(0, 16)
      .map(([k, v]) => [k, typeof v === 'string' ? v.slice(0, 200) : '']),
  );
}

function parseTool(value: unknown): ToolInfo | null {
  const t = asRecord(value);
  const name = asString(t.name, 61);
  if (!name || !/^[a-z][a-z0-9_]{1,60}$/.test(name)) {
    return null;
  }
  return {
    name,
    description: asString(t.description, 600) ?? '',
    args: parseArgs(t.args),
    confirm: t.confirm === true,
    conditionalConfirm: t.conditional_confirm === true,
    alwaysConfirm: t.always_confirm === true,
    enabled: t.enabled !== false,
    owner: asString(t.owner, 41) ?? 'agent',
    defaultOwner: asString(t.default_owner, 41) ?? 'agent',
    custom: t.custom === true,
  };
}

function parseWidget(value: unknown): WidgetInfo | null {
  const w = asRecord(value);
  const id = asString(w.id, 41);
  if (!id) {
    return null;
  }
  return {
    id,
    name: asString(w.name, 60) ?? id,
    icon: asString(w.icon, 8) ?? '',
    source: asString(w.source, 10) ?? 'system',
    agent: asString(w.agent, 41) ?? 'desktop',
    defaultAgent: asString(w.default_agent, 41) ?? 'desktop',
    people: asStringList(w.people),
    enabled: w.enabled !== false,
    personal: w.personal === true,
  };
}

function parseSetting(value: unknown): AgentSetting | null {
  const s = asRecord(value);
  const key = asString(s.key, 80);
  return key
    ? {
        key,
        label: asString(s.label, 160) ?? key,
        type: asString(s.type, 12) ?? 'text',
        value: typeof s.value === 'string' ? s.value.slice(0, 500) : '',
        options: list(s.options).map((o) => String(o ?? '').slice(0, 80)).slice(0, 40),
      }
    : null;
}

export function parseAgent(value: unknown): Agent | null {
  const a = asRecord(value);
  const id = asString(a.id, 41);
  if (!id || !AGENT_ID.test(id)) {
    return null;
  }
  return {
    id,
    name: asString(a.name, 60) ?? id,
    icon: asString(a.icon, 8) ?? '',
    category: asString(a.category, 20) ?? 'altro',
    source: asString(a.source, 10) ?? 'system',
    priority: num(a.priority, 45),
    defaultPriority: num(a.default_priority, 45),
    enabled: a.enabled === true,
    reason: asString(a.reason, 200) ?? '',
    toggle: a.toggle === true,
    mode: asString(a.mode, 4) ?? '',
    fixed: a.fixed === true,
    description: asString(a.description, 600) ?? '',
    can: asStringList(a.can, 20),
    settings: list(a.settings).map(parseSetting).filter((s): s is AgentSetting => s !== null),
    instructions: typeof a.instructions === 'string' ? a.instructions.slice(0, 1500) : '',
    doing: asString(a.doing, 200) ?? '',
    inbox: num(a.inbox),
  };
}

function parseMessage(value: unknown): BoardMessage {
  const m = asRecord(value);
  return {
    at: num(m.at),
    from: asString(m.from, 41) ?? '?',
    to: asString(m.to, 41) ?? '?',
    text: asString(m.text, 400) ?? '',
    kind: asString(m.kind, 20) ?? '',
  };
}

export async function fetchTeam(signal?: AbortSignal): Promise<TeamOverview> {
  const raw = asRecord(await requestJson<unknown>('/api/team', { signal }));
  return {
    agents: list(raw.agents).map(parseAgent).filter((a): a is Agent => a !== null),
    tools: list(raw.tools).map(parseTool).filter((t): t is ToolInfo => t !== null),
    widgets: list(raw.widgets).map(parseWidget).filter((w): w is WidgetInfo => w !== null),
    people: list(raw.people)
      .map(asRecord)
      .flatMap((p) => {
        const slug = asString(p.slug, 64);
        return slug ? [{ slug, name: asString(p.name, 80) ?? slug }] : [];
      }),
    messages: list(raw.messages).map(parseMessage).slice(-40),
  };
}

const guard = (id: string, pattern: RegExp): string => {
  if (!pattern.test(id)) {
    throw new NodeModuleError('invalid_id', 400);
  }
  return encodeURIComponent(id);
};

const send = (url: string, method: string, body?: unknown) =>
  requestJson<unknown>(url, { method, body: body === undefined ? undefined : JSON.stringify(body) });

export const updateAgent = (id: string, change: { priority?: number | null; instructions?: string }) =>
  send(`/api/team/${guard(id, AGENT_ID)}`, 'PUT', change);
export const setAgentMode = (id: string, mode: Mode) => send(`/api/features/${guard(id, AGENT_ID)}`, 'PUT', { mode });
export const saveAgentSettings = (id: string, values: Record<string, string>) =>
  send(`/api/features/${guard(id, AGENT_ID)}/settings`, 'PUT', values);
export const messageAgent = (id: string, text: string) => send(`/api/team/${guard(id, AGENT_ID)}/message`, 'POST', { text });
export const updateTool = (name: string, change: { agent?: string; enabled?: boolean; always_confirm?: boolean }) =>
  send(`/api/team/tools/${guard(name, /^[a-z][a-z0-9_]{1,60}$/)}`, 'PUT', change);
export const updateWidget = (id: string, change: { agent?: string; people?: readonly string[] }) =>
  send(`/api/team/widgets/${guard(id, /^[a-z0-9][a-z0-9_-]{1,40}$/)}`, 'PUT', change);

export interface NewAgent {
  readonly id: string;
  readonly name: string;
  readonly icon: string;
  readonly category: string;
  readonly description: string;
  readonly capabilities: readonly string[];
  readonly instructions: string;
  readonly priority: number;
}

export const createAgent = (agent: NewAgent) => send('/api/team/agents', 'POST', agent);
export const deleteAgent = (id: string) => send(`/api/team/agents/${guard(id, AGENT_ID)}`, 'DELETE');

export interface ToolStep {
  readonly tool: string;
  readonly args: Readonly<Record<string, unknown>>;
}

export interface NewTool {
  readonly name: string;
  readonly description: string;
  readonly agent: string;
  readonly params: Readonly<Record<string, string>>;
  readonly steps: readonly ToolStep[];
}

export const createTool = (tool: NewTool) => send('/api/team/tools', 'POST', tool);
export const deleteTool = (name: string) => send(`/api/team/tools/${guard(name, TOOL_NAME)}`, 'DELETE');

export interface NewWidget {
  readonly id: string;
  readonly name: string;
  readonly icon: string;
  readonly description: string;
  readonly size: 's' | 'm' | 'l';
  readonly priority: number;
  readonly personal: boolean;
  readonly agent: string;
}

export const createWidget = (widget: NewWidget) => send('/api/team/widgets', 'POST', widget);
export const deleteWidget = (id: string) => send(`/api/team/widgets/${guard(id, NEW_AGENT_ID)}`, 'DELETE');
