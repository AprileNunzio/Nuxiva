import { NodeModuleError, asRecord, asString, asStringList, requestJson } from '../../../../node_apps/shared/data/http';

export const EXPERT_ID = /^[a-z][a-z0-9_-]{2,40}$/;
const TOOL_NAME = /^[a-z][a-z0-9_]{1,60}$/;
const SKILL_ID = /^[a-z][a-z0-9_]{2,40}$/;
const COLOR = /^#[0-9a-f]{6}$/i;
export const SKILL_STEP = 'skill:';
export const LIVE_KINDS = ['activity', 'debian', 'football'] as const;
export type LiveKind = (typeof LIVE_KINDS)[number];

export interface PendingAction {
  readonly tool: string;
  readonly args: Readonly<Record<string, unknown>>;
}

export interface Expert {
  readonly id: string;
  readonly role: string;
  readonly specialty: string;
  readonly icon: string;
  readonly color: string;
  readonly knowledge: readonly string[];
  readonly tools: readonly string[];
  readonly skills: readonly string[];
  readonly instructions: string;
  readonly template: string;
  readonly live: LiveKind;
  readonly enabled: boolean;
  readonly doing: string;
  readonly pending: PendingAction | null;
}

export interface ExpertTemplate {
  readonly id: string;
  readonly role: string;
  readonly specialty: string;
  readonly icon: string;
  readonly color: string;
  readonly skills: readonly string[];
  readonly tools: readonly string[];
}

export interface Skill {
  readonly id: string;
  readonly name: string;
  readonly purpose: string;
  readonly procedure: readonly string[];
  readonly rules: readonly string[];
  readonly tools: readonly string[];
}

export interface AssignableTool {
  readonly name: string;
  readonly description: string;
}

export interface ExpertsOverview {
  readonly experts: readonly Expert[];
  readonly templates: readonly ExpertTemplate[];
  readonly skills: readonly Skill[];
  readonly tools: readonly AssignableTool[];
}

export interface ChatStep {
  readonly tool: string;
  readonly ok: boolean;
}

export interface ChatTurn {
  readonly at: number;
  readonly role: 'user' | 'expert';
  readonly text: string;
  readonly steps: readonly ChatStep[];
}

export interface AskResult {
  readonly text: string;
  readonly pending: PendingAction | null;
  readonly steps: readonly ChatStep[];
}

const list = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);
const num = (value: unknown): number => (typeof value === 'number' && Number.isFinite(value) ? value : 0);
const color = (value: unknown): string => {
  const text = asString(value, 7) ?? '';
  return COLOR.test(text) ? text : '#29e0ff';
};
const tools = (value: unknown) => asStringList(value, 24).filter((t) => TOOL_NAME.test(t));
const skillIds = (value: unknown) => asStringList(value, 12).filter((s) => SKILL_ID.test(s));

function parsePending(value: unknown): PendingAction | null {
  const p = asRecord(value);
  const tool = asString(p.tool, 61);
  return tool && TOOL_NAME.test(tool) ? { tool, args: asRecord(p.args) } : null;
}

function parseExpert(value: unknown): Expert | null {
  const e = asRecord(value);
  const id = asString(e.id, 41);
  if (!id || !EXPERT_ID.test(id)) {
    return null;
  }
  const live = asString(e.live, 12) ?? 'activity';
  return {
    id,
    role: asString(e.role, 80) ?? id,
    specialty: asString(e.specialty, 240) ?? '',
    icon: asString(e.icon, 8) ?? '◆',
    color: color(e.color),
    knowledge: asStringList(e.knowledge, 16),
    tools: tools(e.tools),
    skills: skillIds(e.skills),
    instructions: typeof e.instructions === 'string' ? e.instructions.slice(0, 1200) : '',
    template: asString(e.template, 40) ?? '',
    live: (LIVE_KINDS as readonly string[]).includes(live) ? (live as LiveKind) : 'activity',
    enabled: e.enabled !== false,
    doing: asString(e.doing, 200) ?? '',
    pending: parsePending(e.pending),
  };
}

function parseTemplate(value: unknown): ExpertTemplate | null {
  const t = asRecord(value);
  const id = asString(t.id, 20);
  return id
    ? { id, role: asString(t.role, 80) ?? id, specialty: asString(t.specialty, 240) ?? '', icon: asString(t.icon, 8) ?? '◆', color: color(t.color), skills: skillIds(t.skills), tools: tools(t.tools) }
    : null;
}

function parseSkill(value: unknown): Skill | null {
  const s = asRecord(value);
  const id = asString(s.id, 41);
  if (!id || !SKILL_ID.test(id)) {
    return null;
  }
  return {
    id,
    name: asString(s.name, 80) ?? id,
    purpose: asString(s.purpose, 240) ?? '',
    procedure: asStringList(s.procedure, 12),
    rules: asStringList(s.rules, 12),
    tools: tools(s.tools),
  };
}

function parseSteps(value: unknown): ChatStep[] {
  return list(value)
    .map(asRecord)
    .flatMap((s) => {
      const tool = asString(s.tool, 61);
      return tool ? [{ tool, ok: s.ok === true || (typeof s.result === 'string' && !/^(ERRORE|NEGATO)/.test(s.result)) }] : [];
    })
    .slice(0, 12);
}

function parseTurn(value: unknown): ChatTurn | null {
  const t = asRecord(value);
  const text = typeof t.text === 'string' ? t.text.slice(0, 4000) : '';
  return text ? { at: num(t.at), role: t.role === 'user' ? 'user' : 'expert', text, steps: parseSteps(t.steps) } : null;
}

const guard = (id: string): string => {
  if (!EXPERT_ID.test(id)) {
    throw new NodeModuleError('invalid_id', 400);
  }
  return encodeURIComponent(id);
};

const send = (url: string, method: string, body?: unknown) =>
  requestJson<unknown>(url, { method, body: body === undefined ? undefined : JSON.stringify(body) });

export async function fetchExperts(signal?: AbortSignal): Promise<ExpertsOverview> {
  const raw = asRecord(await requestJson<unknown>('/api/experts', { signal }));
  return {
    experts: list(raw.experts).map(parseExpert).filter((e): e is Expert => e !== null),
    templates: list(raw.templates).map(parseTemplate).filter((t): t is ExpertTemplate => t !== null),
    skills: list(raw.skills).map(parseSkill).filter((s): s is Skill => s !== null),
    tools: list(raw.tools)
      .map(asRecord)
      .flatMap((t) => {
        const name = asString(t.name, 61);
        return name && TOOL_NAME.test(name) ? [{ name, description: asString(t.description, 240) ?? '' }] : [];
      }),
  };
}

export interface ExpertDraft {
  readonly template?: string;
  readonly role?: string;
  readonly specialty?: string;
  readonly knowledge?: readonly string[];
  readonly tools?: readonly string[];
  readonly skills?: readonly string[];
  readonly instructions?: string;
  readonly icon?: string;
  readonly color?: string;
  readonly enabled?: boolean;
}

export const createExpert = async (draft: ExpertDraft): Promise<Expert | null> => parseExpert(await send('/api/experts', 'POST', draft));
export const updateExpert = (id: string, draft: ExpertDraft) => send(`/api/experts/${guard(id)}`, 'PUT', draft);
export const deleteExpert = (id: string) => send(`/api/experts/${guard(id)}`, 'DELETE');
export const forgetChat = (id: string) => send(`/api/experts/${guard(id)}/history`, 'DELETE');

export async function fetchHistory(id: string, signal?: AbortSignal): Promise<{ turns: ChatTurn[]; pending: PendingAction | null }> {
  const raw = asRecord(await requestJson<unknown>(`/api/experts/${guard(id)}/history`, { signal }));
  return { turns: list(raw.turns).map(parseTurn).filter((t): t is ChatTurn => t !== null), pending: parsePending(raw.pending) };
}

function parseAsk(value: unknown): AskResult {
  const r = asRecord(value);
  return { text: typeof r.text === 'string' ? r.text.slice(0, 4000) : '', pending: parsePending(r.pending), steps: parseSteps(r.steps) };
}

export const askExpert = async (id: string, question: string): Promise<AskResult> =>
  parseAsk(await send(`/api/experts/${guard(id)}/ask`, 'POST', { question: question.slice(0, 2000) }));
export const confirmExpert = async (id: string, yes: boolean): Promise<AskResult> =>
  parseAsk(await send(`/api/experts/${guard(id)}/confirm`, 'POST', { yes }));

export const fetchLive = (id: string, signal?: AbortSignal) => requestJson<unknown>(`/api/experts/${guard(id)}/live`, { signal });
