import { sendJson } from '../shared/http';
import { AlgorithmDraft, AlgorithmTest } from './types';

export const catalogUrl = '/api/algorithms/catalog';

const enc = (key: string) => key.split('/').map(encodeURIComponent).join('/');

export const setEnabled = (key: string, enabled: boolean) => sendJson(`/api/skills/${enc(key)}`, 'PUT', { enabled });
export const removeAlgorithm = (key: string) => sendJson(`/api/skills/${enc(key)}`, 'DELETE');
export const testAlgorithm = (key: string, text: string) => sendJson<AlgorithmTest>(`/api/skills/${enc(key)}/test`, 'POST', { text });
export const createAlgorithm = (draft: AlgorithmDraft) => sendJson<{ key: string }>('/api/skills', 'POST', draft);
export const generateAlgorithm = (description: string) => sendJson<{ key: string }>('/api/skills/generate', 'POST', { description });
export const saveAlgorithmCode = (key: string, code: string) => sendJson(`/api/skills/${enc(key)}/code`, 'PUT', { code });

export async function fetchAlgorithmCode(key: string): Promise<string> {
  const response = await fetch(`/api/skills/${enc(key)}/code`, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error('code_unavailable');
  }
  return response.text();
}
