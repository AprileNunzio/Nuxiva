import { NodeModuleError, asRecord, asString, requestJson } from '../../../node_apps/shared/data/http';

export type ModelOrigin = 'local' | 'server' | 'cloud';
export type ModelMode = 'inherit' | 'first' | 'only';

export interface ModelChoice {
  readonly ref: string;
  readonly model: string;
  readonly provider: string;
  readonly origin: ModelOrigin;
  readonly available: boolean;
}

export interface AgentModel {
  readonly component: string;
  readonly role: string;
  readonly ref: string;
  readonly mode: ModelMode;
  readonly active: readonly ModelChoice[];
  readonly pool: readonly ModelChoice[];
}

const ORIGINS: readonly ModelOrigin[] = ['local', 'server', 'cloud'];
const MODES: readonly ModelMode[] = ['inherit', 'first', 'only'];
const AGENT_ID = /^[a-z0-9][a-z0-9_-]{0,63}$/;
const REF = /^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,159}$/;

const choice = (raw: unknown): ModelChoice | null => {
  const row = asRecord(raw);
  const ref = asString(row.ref, 160);
  const origin = row.origin as ModelOrigin;
  if (!ref || !REF.test(ref) || !ORIGINS.includes(origin)) return null;
  return { ref, model: asString(row.model, 160) ?? ref, provider: asString(row.provider, 80) ?? '', origin, available: row.available === true };
};

const list = (value: unknown): ModelChoice[] => (Array.isArray(value) ? value.map(choice).filter((item): item is ModelChoice => item !== null) : []);

const guarded = (agentId: string): string => {
  if (!AGENT_ID.test(agentId)) throw new NodeModuleError('agent_unknown', 404);
  return agentId;
};

export async function fetchAgentModel(agentId: string, signal?: AbortSignal): Promise<AgentModel> {
  const id = guarded(agentId);
  const body = asRecord(await requestJson<unknown>(`/api/brains/assignments?agents=${encodeURIComponent(id)}`, { signal }));
  const rows = Array.isArray(body.components) ? body.components : [];
  const row = rows.map(asRecord).find((item) => item.id === id || item.id === `agent:${id}`);
  if (!row || typeof row.id !== 'string') throw new NodeModuleError('agent_unknown', 404);
  const assignment = asRecord(row.assignment);
  const order = Array.isArray(assignment.order) ? assignment.order : [];
  const mode = assignment.mode as ModelMode;
  return {
    component: row.id,
    role: asString(row.role, 40) ?? 'deep',
    ref: typeof order[0] === 'string' && REF.test(order[0]) ? order[0] : '',
    mode: MODES.includes(mode) ? mode : 'inherit',
    active: list(row.chain),
    pool: list(body.pool),
  };
}

export async function saveAgentModel(component: string, ref: string, mode: ModelMode): Promise<void> {
  if (!/^[a-z0-9][a-z0-9_:-]{0,70}$/.test(component) || (ref && !REF.test(ref))) throw new NodeModuleError('model_invalid', 400);
  const update = ref ? { order: [ref], mode: mode === 'inherit' ? 'first' : mode } : null;
  await requestJson<unknown>('/api/brains/assignments', { method: 'PUT', body: JSON.stringify({ updates: { [component]: update } }) });
}
