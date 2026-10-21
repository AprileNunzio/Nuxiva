import { asRecord, asString, requestJson } from '../../shared/data/http';
import { list, num } from './parse';

export const FREE_POOLS = ['chat', 'voice_fast', 'agent_tools', 'vision', 'deep_code'] as const;
export type FreePool = (typeof FREE_POOLS)[number];

export interface FreeModel {
  readonly id: string;
  readonly name: string;
  readonly context: number;
  readonly vision: boolean;
  readonly tools: boolean;
  readonly json: boolean;
  readonly reasoning: boolean;
  readonly pools: readonly FreePool[];
  readonly cooldownSeconds: number;
  readonly disabled: boolean;
}

export interface FreeLiveRoute {
  readonly status: string;
  readonly provider: string;
  readonly model: string;
  readonly pool: string;
  readonly failover: boolean;
  readonly previousModel: string;
  readonly timestamp: number;
}

export interface FreeMatrix {
  readonly enabled: boolean;
  readonly pools: readonly FreePool[];
  readonly updatedAt: number;
  readonly models: readonly FreeModel[];
  readonly live: FreeLiveRoute | null;
}

function parseModel(value: unknown): FreeModel | null {
  const model = asRecord(value);
  const id = asString(model.id, 200);
  if (!id || !/^[A-Za-z0-9][A-Za-z0-9._/:+-]{0,199}$/.test(id)) {
    return null;
  }
  const rate = asRecord(model.rate);
  return {
    id,
    name: asString(model.name, 120) ?? id,
    context: Math.max(0, num(model.context)),
    vision: model.vision === true,
    tools: model.tools === true,
    json: model.json === true,
    reasoning: model.reasoning === true,
    pools: list(model.pools).filter((pool): pool is FreePool => typeof pool === 'string' && FREE_POOLS.some((known) => known === pool)),
    cooldownSeconds: Math.max(0, num(rate.cooldown_seconds)),
    disabled: rate.disabled === true,
  };
}

function parseMatrix(value: unknown): FreeMatrix {
  const matrix = asRecord(value);
  const live = asRecord(matrix.live);
  const route = asRecord(live.active_route);
  const failover = asRecord(live.failover_event);
  const model = asString(route.model_short_name, 120) ?? asString(route.model_id, 200) ?? '';
  return {
    enabled: matrix.enabled === true,
    pools: list(matrix.pools).filter((pool): pool is FreePool => typeof pool === 'string' && FREE_POOLS.some((known) => known === pool)),
    updatedAt: num(matrix.updated_at),
    models: list(matrix.models).map(parseModel).filter((model): model is FreeModel => model !== null),
    live: model ? {
      status: asString(live.status, 40) ?? '',
      provider: asString(route.provider_label, 80) ?? '',
      model,
      pool: asString(route.pool, 40) ?? '',
      failover: failover.triggered === true,
      previousModel: asString(failover.previous_model, 200) ?? '',
      timestamp: num(live.timestamp),
    } : null,
  };
}

export async function fetchFreeMatrix(signal?: AbortSignal): Promise<FreeMatrix> {
  return parseMatrix(await requestJson<unknown>('/api/brains/free-matrix', { signal }));
}

export async function saveFreeMatrix(enabled: boolean, pools: readonly FreePool[]): Promise<void> {
  await requestJson('/api/brains/free-matrix', { method: 'PUT', body: JSON.stringify({ enabled, pools }) });
}

export async function refreshFreeCatalog(): Promise<void> {
  await requestJson('/api/brains/free-matrix/refresh', { method: 'POST' });
}
