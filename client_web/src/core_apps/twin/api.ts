import { sendJson } from '../shared/http';
import { SimulationResult } from './types';

export const saveRules = (rules: Readonly<Record<string, boolean>>) => sendJson('/api/twin/rules', 'PUT', rules);

export const simulate = (service: string, entities: readonly string[]) =>
  sendJson<SimulationResult>('/api/twin/simulate', 'POST', { calls: [{ service, entity_ids: entities }] });
