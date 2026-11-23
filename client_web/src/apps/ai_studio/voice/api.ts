import type { VoiceQuery, VoiceTurnsPage, VoiceVerdict } from './types';

const BASE = '/api/ai_studio/voice/turns';
const ID_RE = /^[0-9a-f]{16}$/;

async function failure(res: Response): Promise<Error> {
  const body = await res.json().catch(() => ({ detail: res.statusText }));
  return new Error(typeof body.detail === 'string' ? body.detail : `HTTP ${res.status}`);
}

function turnPath(id: string, suffix = ''): string {
  if (!ID_RE.test(id)) throw new Error('invalid_turn_id');
  return `${BASE}/${id}${suffix}`;
}

export async function fetchVoiceTurns(query: VoiceQuery, signal?: AbortSignal): Promise<VoiceTurnsPage> {
  const params = new URLSearchParams({ channel: query.channel, limit: String(query.limit ?? 40) });
  if (query.q.trim()) params.set('q', query.q.trim().slice(0, 120));
  if (query.before) params.set('before', String(query.before));
  const res = await fetch(`${BASE}?${params.toString()}`, { signal, cache: 'no-store' });
  if (!res.ok) throw await failure(res);
  const data = (await res.json()) as VoiceTurnsPage;
  return { items: Array.isArray(data.items) ? data.items : [], stats: data.stats ?? {} };
}

export async function fetchVoiceAudio(id: string, signal?: AbortSignal): Promise<Blob> {
  const res = await fetch(turnPath(id, '/audio'), { signal, cache: 'no-store' });
  if (!res.ok) throw await failure(res);
  const blob = await res.blob();
  if (!blob.type.startsWith('audio/')) throw new Error('invalid_audio');
  return blob;
}

export async function sendVoiceFeedback(id: string, verdict: VoiceVerdict, correction: string, note: string): Promise<void> {
  const res = await fetch(turnPath(id, '/feedback'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ verdict, correction: correction.slice(0, 2000), note: note.slice(0, 600) }),
  });
  if (!res.ok) throw await failure(res);
}

export async function deleteVoiceTurn(id: string): Promise<void> {
  const res = await fetch(turnPath(id), { method: 'DELETE' });
  if (!res.ok) throw await failure(res);
}
