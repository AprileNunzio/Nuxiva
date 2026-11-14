import { getJson, sendJson } from '../shared/http';
import type { ControlAction, Overview, ProjectDetail, ProjectSummary, ReviewAction } from './types';

const BASE = '/api/agency';
const enc = encodeURIComponent;

export const OVERVIEW_URL = BASE;
export const detailUrl = (id: string) => `${BASE}/projects/${enc(id)}`;

export const fetchDetail = (id: string, signal?: AbortSignal) => getJson<ProjectDetail>(detailUrl(id), signal);
export const fetchOverview = (signal?: AbortSignal) => getJson<Overview>(BASE, signal);
export const createProject = (goal: string) => sendJson<{ accepted: boolean }>(`${BASE}/projects`, 'POST', { goal });
export const control = (id: string, action: ControlAction) => sendJson<ProjectDetail>(`${detailUrl(id)}/${action}`, 'POST');
export const rename = (id: string, title: string) => sendJson<ProjectDetail>(detailUrl(id), 'PATCH', { title });
export const archive = (id: string, archived: boolean) => sendJson<ProjectDetail>(`${detailUrl(id)}/${archived ? 'archive' : 'unarchive'}`, 'POST');
export const assign = (id: string, agents: readonly string[]) => sendJson<ProjectDetail>(`${detailUrl(id)}/agents`, 'PUT', { agents });
export const remove = (id: string, confirm: string) => sendJson<{ deleted: string }>(detailUrl(id), 'DELETE', { confirm });
export const review = (id: string, task: string, action: ReviewAction, feedback = '') =>
  sendJson<ProjectDetail>(`${detailUrl(id)}/tasks/${enc(task)}/${action}`, 'POST', feedback ? { feedback } : {});

export type { ProjectSummary };
