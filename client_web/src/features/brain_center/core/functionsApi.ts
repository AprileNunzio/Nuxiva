import { asRecord, asString, requestJson } from './http';
import { MAX_CHAIN, REF, list, refs, strings } from './parse';
import { AssignmentMode, FunctionRow } from './types';

const COMPONENT_ID = /^[a-z0-9_]{1,64}$/;
const MODES: readonly AssignmentMode[] = ['inherit', 'first', 'only'];

function parseFunction(value: unknown): FunctionRow | null {
  const row = asRecord(value);
  const id = asString(row.id, 64);
  if (!id || !COMPONENT_ID.test(id)) {
    return null;
  }
  const assignment = asRecord(row.assignment);
  return {
    id,
    group: asString(row.group, 60) ?? '',
    side: row.side === 'core' ? 'core' : 'supervisor',
    role: asString(row.role, 40) ?? '',
    defaultRole: asString(row.default_role, 40) ?? '',
    mode: MODES.find((m) => m === assignment.mode) ?? 'inherit',
    order: strings(assignment.order, MAX_CHAIN, 230).filter((m) => REF.test(m)),
    chain: refs(row.chain),
  };
}

const parseAll = (value: unknown): FunctionRow[] =>
  list(asRecord(value).components)
    .map(parseFunction)
    .filter((r): r is FunctionRow => r !== null);

export async function fetchFunctions(signal?: AbortSignal): Promise<FunctionRow[]> {
  return parseAll(await requestJson<unknown>('/api/brains/assignments', { signal }));
}

export async function saveFunction(id: string, mode: AssignmentMode, order: readonly string[]): Promise<FunctionRow[]> {
  if (!COMPONENT_ID.test(id) || order.length > MAX_CHAIN || !order.every((m) => REF.test(m))) {
    throw new RangeError('invalid_assignment');
  }
  const value = mode === 'inherit' || order.length === 0 ? null : { mode, order };
  return parseAll(await requestJson<unknown>('/api/brains/assignments', { method: 'PUT', body: JSON.stringify({ updates: { [id]: value } }) }));
}
