import type { Project, Thread, Message, MemoryFact, SmbItem, Attachment, ModelMode } from './types';

const BASE_URL = '/api/ai_studio';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorBody.detail || `Request failed with status ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchProjects(): Promise<Project[]> {
  const res = await fetch(`${BASE_URL}/projects`);
  return handleResponse<Project[]>(res);
}

export async function createProject(data: {
  name: string;
  description: string;
  instructions: string;
  smb_folder: string;
}): Promise<Project> {
  const res = await fetch(`${BASE_URL}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<Project>(res);
}

export async function deleteProject(projectId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/projects/${encodeURIComponent(projectId)}`, {
    method: 'DELETE',
  });
  await handleResponse<{ status: string }>(res);
}

export async function fetchThreads(projectId?: string | null): Promise<Thread[]> {
  const url = projectId
    ? `${BASE_URL}/threads?project_id=${encodeURIComponent(projectId)}`
    : `${BASE_URL}/threads`;
  const res = await fetch(url);
  return handleResponse<Thread[]>(res);
}

export async function createThread(data: {
  title: string;
  project_id?: string | null;
  model_mode: ModelMode;
}): Promise<Thread> {
  const res = await fetch(`${BASE_URL}/threads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<Thread>(res);
}

export async function updateThread(
  threadId: string,
  data: { title?: string; pinned?: boolean; model_mode?: ModelMode }
): Promise<Thread> {
  const res = await fetch(`${BASE_URL}/threads/${encodeURIComponent(threadId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<Thread>(res);
}

export async function deleteThread(threadId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/threads/${encodeURIComponent(threadId)}`, {
    method: 'DELETE',
  });
  await handleResponse<{ status: string }>(res);
}

export async function fetchMessages(threadId: string): Promise<Message[]> {
  const res = await fetch(`${BASE_URL}/threads/${encodeURIComponent(threadId)}/messages`);
  return handleResponse<Message[]>(res);
}

export async function sendMessage(
  threadId: string,
  content: string,
  attachments?: Attachment[],
  presetId?: string | null
): Promise<Message> {
  const res = await fetch(`${BASE_URL}/threads/${encodeURIComponent(threadId)}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, attachments, preset_id: presetId || undefined }),
  });
  return handleResponse<Message>(res);
}

export async function fetchMemoryFacts(query?: string): Promise<MemoryFact[]> {
  const url = query ? `${BASE_URL}/memory/facts?q=${encodeURIComponent(query)}` : `${BASE_URL}/memory/facts`;
  const res = await fetch(url);
  return handleResponse<MemoryFact[]>(res);
}

export async function learnMemory(data: {
  content: string;
  source?: string;
  speaker?: string;
  tags?: string[];
}): Promise<MemoryFact> {
  const res = await fetch(`${BASE_URL}/memory/learn`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<MemoryFact>(res);
}

export async function fetchSmbTree(folder: string = ''): Promise<SmbItem[]> {
  const url = folder ? `${BASE_URL}/smb/tree?folder=${encodeURIComponent(folder)}` : `${BASE_URL}/smb/tree`;
  const res = await fetch(url);
  return handleResponse<SmbItem[]>(res);
}

export async function saveSmbFile(data: {
  folder: string;
  filename: string;
  content: string;
}): Promise<{ status: string; relative_path: string; unc_path: string }> {
  const res = await fetch(`${BASE_URL}/smb/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<{ status: string; relative_path: string; unc_path: string }>(res);
}

export async function uploadFile(file: File): Promise<Attachment> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  });
  const data = await handleResponse<{ name: string; size: number; mime_type: string; path: string }>(res);
  return {
    id: `att_${Date.now()}`,
    name: data.name,
    size: data.size,
    mime_type: data.mime_type,
    kind: data.mime_type.startsWith('image/') ? 'image' : 'document',
    path: data.path,
  };
}

export interface KnowledgeDoc {
  id: string;
  project_id: string;
  name: string;
  chars: number;
  chunks: number;
  created_at: number;
}

export async function fetchKnowledge(projectId: string): Promise<KnowledgeDoc[]> {
  const res = await fetch(`${BASE_URL}/projects/${encodeURIComponent(projectId)}/knowledge`);
  return handleResponse<KnowledgeDoc[]>(res);
}

export async function addKnowledge(projectId: string, name: string, content: string): Promise<KnowledgeDoc> {
  const res = await fetch(`${BASE_URL}/projects/${encodeURIComponent(projectId)}/knowledge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, content }),
  });
  return handleResponse<KnowledgeDoc>(res);
}

export async function deleteKnowledge(projectId: string, docId: string): Promise<void> {
  const res = await fetch(
    `${BASE_URL}/projects/${encodeURIComponent(projectId)}/knowledge/${encodeURIComponent(docId)}`,
    { method: 'DELETE' },
  );
  await handleResponse<{ status: string }>(res);
}

export interface Preset {
  id: string;
  project_id: string | null;
  name: string;
  description: string;
  system_prompt: string;
  model_mode: ModelMode;
}

export async function fetchPresets(projectId?: string | null): Promise<Preset[]> {
  const url = projectId ? `${BASE_URL}/presets?project_id=${encodeURIComponent(projectId)}` : `${BASE_URL}/presets`;
  return handleResponse<Preset[]>(await fetch(url));
}

export async function createPreset(data: {
  name: string;
  description: string;
  system_prompt: string;
  model_mode: ModelMode;
  project_id?: string | null;
}): Promise<Preset> {
  const res = await fetch(`${BASE_URL}/presets`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<Preset>(res);
}

export async function deletePreset(presetId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/presets/${encodeURIComponent(presetId)}`, { method: 'DELETE' });
  await handleResponse<{ status: string }>(res);
}

export interface ExecutionResult {
  ok: boolean;
  exit_code: number;
  output: string;
  duration_ms: number;
}

export async function executeCode(code: string, language: string = 'python'): Promise<ExecutionResult> {
  const res = await fetch(`${BASE_URL}/sandbox/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, language }),
  });
  return handleResponse<ExecutionResult>(res);
}

export async function streamMessage(
  threadId: string,
  content: string,
  attachments?: Attachment[],
  presetId?: string | null,
  onToken?: (token: string) => void,
  onThoughtDelta?: (delta: string) => void,
): Promise<Message> {
  const res = await fetch(`${BASE_URL}/threads/${encodeURIComponent(threadId)}/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, attachments, preset_id: presetId || undefined }),
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorBody.detail || `Stream failed with status ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error('No readable stream available');

  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let finalMessage: Message | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || '';

    for (const chunk of lines) {
      const trimmed = chunk.trim();
      if (!trimmed.startsWith('data:')) continue;
      try {
        const payload = JSON.parse(trimmed.slice(5).trim());
        if (payload.type === 'token') {
          onToken?.(payload.token);
        } else if (payload.type === 'thought_delta') {
          onThoughtDelta?.(payload.token);
        } else if (payload.type === 'done') {
          finalMessage = payload.message as Message;
        }
      } catch {}
    }
  }

  if (!finalMessage) {
    throw new Error('Incomplete stream response from AI Studio');
  }
  return finalMessage;
}
