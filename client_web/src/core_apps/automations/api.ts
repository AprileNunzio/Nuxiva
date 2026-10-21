import { sendJson } from '../shared/http';
import { GeneratedAutomation } from './types';

const BASE = '/api/automations';
const enc = encodeURIComponent;

export const toggleAutomation = (id: string, enabled: boolean) => sendJson(`${BASE}/${enc(id)}/toggle`, 'POST', { enabled });
export const runAutomation = (id: string) => sendJson<{ ok: boolean; message?: string }>(`${BASE}/${enc(id)}/run`, 'POST', {});
export const duplicateAutomation = (id: string) => sendJson(`${BASE}/${enc(id)}/duplicate`, 'POST');
export const deleteAutomation = (id: string) => sendJson(`${BASE}/${enc(id)}`, 'DELETE');
export const stopRun = (id: string) => sendJson(`${BASE}/runs/${enc(id)}/stop`, 'POST');
export const fromTemplate = (index: number) => sendJson(`${BASE}/templates/${index}`, 'POST');
export const generate = (text: string) => sendJson<GeneratedAutomation>(`${BASE}/generate`, 'POST', { text });
export const saveAutomation = (spec: Readonly<Record<string, unknown>>) => sendJson(BASE, 'POST', spec);
