import { requestJson } from '../../node_apps/shared/data/http';

export interface TaskStep {
  readonly text: string;
  readonly state: 'pending' | 'running' | 'done' | 'error';
}

export interface TaskOffer {
  readonly question: string;
  readonly actions: ReadonlyArray<{ readonly id: string; readonly label: string }>;
}

export interface TaskRow {
  readonly id: string;
  readonly kind: string;
  readonly title: string;
  readonly feature: string;
  readonly state: 'queued' | 'running' | 'paused' | 'done' | 'error' | 'cancelled';
  readonly stage: string;
  readonly progress: number;
  readonly summary: string;
  readonly error: string;
  readonly updated: number;
  readonly result: { readonly app?: string; readonly payload?: Record<string, unknown> };
  readonly offer: TaskOffer | null;
  readonly answered: boolean;
  readonly steps: readonly TaskStep[];
}

export interface TaskSnapshot {
  readonly tasks: readonly TaskRow[];
  readonly active: number;
  readonly waiting: number;
}

export const loadTasks = (signal?: AbortSignal) => requestJson<TaskSnapshot>('/api/tasks', { signal });

export const answerTask = (id: string, action: string) =>
  requestJson(`/api/tasks/${encodeURIComponent(id)}/answer`, { method: 'POST', body: JSON.stringify({ action }) });

export const cancelTask = (task: Pick<TaskRow, 'id' | 'feature'>) => {
  if (task.feature === 'autonomous_worker') {
    const mid = task.id.replace(/^mission:/, '');
    return requestJson(`/api/autonomous/missions/${encodeURIComponent(mid)}/control/cancel`, { method: 'POST' });
  }
  if (task.feature === 'projects') {
    const pid = task.id.replace(/^project:/, '');
    return requestJson(`/api/projects/${encodeURIComponent(pid)}/cancel`, { method: 'POST' });
  }
  return requestJson(`/api/tasks/${encodeURIComponent(task.id)}/cancel`, { method: 'POST' });
};
