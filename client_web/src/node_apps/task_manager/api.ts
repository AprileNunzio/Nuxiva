import { requestJson } from '../shared/data/http';
import { NodeCapabilities, NodeTasksSummary } from './types';

export async function fetchNodeTasks(nodeId: string): Promise<NodeTasksSummary> {
  return requestJson<NodeTasksSummary>(`/api/v5/nodes/${encodeURIComponent(nodeId)}/tasks`);
}

export async function terminateTask(
  nodeId: string,
  pid: number,
): Promise<{ readonly success: boolean; readonly pid: number }> {
  return requestJson(`/api/v5/nodes/${encodeURIComponent(nodeId)}/tasks/${pid}/terminate`, {
    method: 'POST',
    body: JSON.stringify({ pid }),
  });
}

export async function toggleNodeCapability(
  nodeId: string,
  capability: string,
  enabled: boolean,
): Promise<{
  readonly success: boolean;
  readonly capability: string;
  readonly enabled: boolean;
  readonly capabilities: NodeCapabilities;
}> {
  return requestJson(`/api/v5/nodes/${encodeURIComponent(nodeId)}/capabilities/toggle`, {
    method: 'POST',
    body: JSON.stringify({ capability, enabled }),
  });
}