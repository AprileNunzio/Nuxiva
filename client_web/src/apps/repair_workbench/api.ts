import { requestJson } from '../../node_apps/shared/data/http';
import { adminPath } from '../../shared/http/basePath';
import type {
  CameraSourceItem,
  ProjectSummaryItem,
  WorkbenchLaunchItem,
  WorkbenchSession,
  RepairTeamState,
  RepairProjectFolder,
} from './types';

const CONTROL_CHARS = /[\u0000-\u001f\u007f<>`]/g;
const getJson = <T,>(url: string) => requestJson<T>(url);
const sendJson = <T,>(url: string, method: 'POST', body: unknown) => requestJson<T>(url, {
  method, headers: { 'X-Nuxiva-Request': '1' }, body: JSON.stringify(body),
});

export function sanitizeField(raw: string, maxLen = 160): string {
  return raw.replace(CONTROL_CHARS, '').trim().slice(0, maxLen);
}

export async function fetchCamerasList(): Promise<CameraSourceItem[]> {
  const res = await getJson<{ sources?: CameraSourceItem[] }>(adminPath('/api/cameras/sources'));
  return Array.isArray(res.sources) ? res.sources : [];
}

export async function fetchProjectsList(): Promise<ProjectSummaryItem[]> {
  const res = await getJson<{ projects?: ProjectSummaryItem[] }>('/api/v1/repair-workbench/projects');
  return Array.isArray(res.projects) ? res.projects : [];
}

export async function createRepairProject(name: string, goal: string): Promise<ProjectSummaryItem> {
  const res = await sendJson<{ project: ProjectSummaryItem }>('/api/v1/repair-workbench/projects', 'POST', {
    name: sanitizeField(name, 80),
    goal: sanitizeField(goal, 400),
    autonomous_247: false,
  });
  return res.project;
}

export async function startWorkbenchSession(payload: {
  project_id: string;
  camera_id?: string;
  camera_name: string;
  language: string;
}): Promise<WorkbenchSession> {
  const res = await sendJson<{ session: WorkbenchSession }>(
    '/api/v1/repair-workbench/sessions',
    'POST',
    {
      project_id: sanitizeField(payload.project_id, 64),
      camera_id: payload.camera_id ? sanitizeField(payload.camera_id, 128) : undefined,
      camera_name: sanitizeField(payload.camera_name, 80),
      language: sanitizeField(payload.language, 12),
    }
  );
  return res.session;
}

export async function getWorkbenchSession(sessionId: string): Promise<WorkbenchSession> {
  const safeId = encodeURIComponent(sanitizeField(sessionId, 64));
  const res = await getJson<{ session: WorkbenchSession }>(
    `/api/v1/repair-workbench/sessions/${safeId}`
  );
  return res.session;
}

export async function analyzeWorkbenchFrame(
  sessionId: string,
  frameBase64: string,
  grid: number[]
): Promise<{ analyzed: boolean; session: WorkbenchSession }> {
  const safeId = encodeURIComponent(sanitizeField(sessionId, 64));
  return sendJson<{ analyzed: boolean; session: WorkbenchSession }>(
    `/api/v1/repair-workbench/sessions/${safeId}/analyze-frame`,
    'POST',
    { frame_base64: frameBase64, grid: grid.slice(0, 4096) }
  );
}

export async function teachWorkbenchComponent(
  sessionId: string,
  trackId: number,
  label: string,
  value: string
): Promise<WorkbenchSession> {
  const safeId = encodeURIComponent(sanitizeField(sessionId, 64));
  const res = await sendJson<{ session: WorkbenchSession }>(
    `/api/v1/repair-workbench/sessions/${safeId}/teach-component`,
    'POST',
    {
      track_id: Math.max(1, Math.floor(trackId)),
      label: sanitizeField(label, 80),
      value: sanitizeField(value, 80),
    }
  );
  return res.session;
}

export async function sendWorkbenchChat(
  sessionId: string,
  message: string,
  agentId?: string
): Promise<{ agent_id: string; agent_name: string }> {
  const safeId = encodeURIComponent(sanitizeField(sessionId, 64));
  return sendJson<{ agent_id: string; agent_name: string }>(
    `/api/v1/repair-workbench/sessions/${safeId}/chat`,
    'POST',
    {
      message: sanitizeField(message, 1000),
      agent_id: agentId ? sanitizeField(agentId, 64) : undefined,
    }
  );
}

export async function escalateWorkbenchSpecialist(
  sessionId: string,
  requesterAgentId: string,
  specialty: string,
  justification: string
): Promise<{ specialist_id: string; forged: boolean }> {
  const safeId = encodeURIComponent(sanitizeField(sessionId, 64));
  const res = await sendJson<{ result: { specialist_id: string; forged: boolean } }>(
    `/api/v1/repair-workbench/sessions/${safeId}/escalate`,
    'POST',
    {
      requester_agent_id: sanitizeField(requesterAgentId, 64),
      specialty: sanitizeField(specialty, 80),
      justification: sanitizeField(justification, 800),
    }
  );
  return res.result;
}

export async function fetchPendingWorkbenchLaunches(
  since: number
): Promise<WorkbenchLaunchItem[]> {
  const res = await getJson<{ requests?: WorkbenchLaunchItem[] }>(
    `/api/v1/repair-workbench/launch-requests?since=${encodeURIComponent(String(since))}`
  );
  return Array.isArray(res.requests) ? res.requests : [];
}

export async function fetchRepairTeam(sessionId: string): Promise<RepairTeamState> {
  const safeId = encodeURIComponent(sanitizeField(sessionId, 64));
  const res = await getJson<{ team: RepairTeamState }>(`/api/v1/repair-workbench/sessions/${safeId}/team`);
  return res.team;
}

export async function reportRepairIssue(sessionId: string, title: string, severity: 'low' | 'medium' | 'high'): Promise<void> {
  const safeId = encodeURIComponent(sanitizeField(sessionId, 64));
  await sendJson(`/api/v1/repair-workbench/sessions/${safeId}/issues`, 'POST', {
    title: sanitizeField(title, 1000), severity, source: 'operator',
  });
}

export async function runRepairTeam(sessionId: string): Promise<void> {
  const safeId = encodeURIComponent(sanitizeField(sessionId, 64));
  await sendJson(`/api/v1/repair-workbench/sessions/${safeId}/team/run`, 'POST', {});
}

export async function fetchRepairProjectFolders(includeClosed = false): Promise<RepairProjectFolder[]> {
  const res = await getJson<{ projects: RepairProjectFolder[] }>(`/api/v1/repair-workbench/projects/archive${includeClosed ? '?include_closed=true' : ''}`);
  return res.projects;
}

export async function resumeRepairProject(projectId: string): Promise<WorkbenchSession> {
  const safeId = encodeURIComponent(sanitizeField(projectId, 64));
  const res = await sendJson<{ session: WorkbenchSession }>(`/api/v1/repair-workbench/projects/${safeId}/resume`, 'POST', {});
  return res.session;
}

export async function closeRepairProject(projectId: string): Promise<void> {
  const safeId = encodeURIComponent(sanitizeField(projectId, 64));
  await sendJson(`/api/v1/repair-workbench/projects/${safeId}/close`, 'POST', {});
}
