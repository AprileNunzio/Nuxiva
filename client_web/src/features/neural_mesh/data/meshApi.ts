import { MeshNeuron, MeshSnapshot, STREAM_KINDS, StreamKind, VIRTUAL_CORE_ID } from '../domain/types';
import { isRecord } from './sanitize';
import { parseTopology } from './topologyParser';

const TOPOLOGY_ENDPOINT = '/api/v5/mesh/topology';
const BIND_ENDPOINT = '/api/v5/mesh/bind_parent';
const REQUEST_TIMEOUT_MS = 10000;

export const TELEMETRY_STREAM_PATH = '/api/v5/mesh/telemetry/stream';

export class MeshApiError extends Error {
  constructor(
    readonly code: string,
    readonly status: number,
  ) {
    super(code);
    this.name = 'MeshApiError';
  }
}

const BASE_INIT: RequestInit = {
  credentials: 'same-origin',
  cache: 'no-store',
  mode: 'same-origin',
  redirect: 'error',
  referrerPolicy: 'same-origin',
};

function withTimeout(signal?: AbortSignal): AbortSignal {
  const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
  return signal && 'any' in AbortSignal ? AbortSignal.any([signal, timeout]) : signal ?? timeout;
}

export async function fetchTopology(signal: AbortSignal): Promise<MeshSnapshot> {
  const response = await fetch(TOPOLOGY_ENDPOINT, {
    ...BASE_INIT,
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal: withTimeout(signal),
  });
  if (!response.ok) {
    throw new MeshApiError('topology_unavailable', response.status);
  }
  return parseTopology(await response.json(), Date.now());
}

export interface BindParentCommand {
  readonly neuron: MeshNeuron;
  readonly parent: MeshNeuron | null;
  readonly stream: StreamKind;
}

export async function bindParent({ neuron, parent, stream }: BindParentCommand): Promise<void> {
  if (!STREAM_KINDS.includes(stream) || parent?.id === neuron.id) {
    throw new MeshApiError('bind_invalid_request', 0);
  }
  const response = await fetch(BIND_ENDPOINT, {
    ...BASE_INIT,
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-Requested-With': 'NuxivaConsole',
    },
    body: JSON.stringify({
      satellite_id: neuron.id,
      satellite_ip: neuron.ip ?? '0.0.0.0',
      parent_node_id: parent ? parent.id : VIRTUAL_CORE_ID,
      parent_ip: parent?.ip ?? '127.0.0.1',
      stream_type: stream,
    }),
    signal: withTimeout(),
  });
  if (!response.ok) {
    throw new MeshApiError('bind_failed', response.status);
  }
  const payload: unknown = await response.json();
  if (!isRecord(payload) || payload.ok !== true) {
    throw new MeshApiError('bind_failed', response.status);
  }
}
