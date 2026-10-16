import { sendJson } from '../shared/http';
import { StudyHit } from './types';

const BASE = '/api/study';
const enc = encodeURIComponent;

export const saveSettings = (change: Readonly<Record<string, unknown>>) => sendJson(`${BASE}/settings`, 'PUT', change);
export const addTopic = (name: string, targetLevel: number, priority: number) => sendJson(`${BASE}/topics`, 'POST', { name, target_level: targetLevel, priority });
export const deleteTopic = (id: string) => sendJson(`${BASE}/topics/${enc(id)}`, 'DELETE');
export const resetTopic = (id: string) => sendJson(`${BASE}/topics/${enc(id)}/reset`, 'POST');
export const studyNow = () => sendJson(`${BASE}/now`, 'POST');
export const acceptMention = (key: string) => sendJson(`${BASE}/mentions/${enc(key)}`, 'POST');
export const dropMention = (key: string) => sendJson(`${BASE}/mentions/${enc(key)}`, 'DELETE');
export const searchMemory = (q: string) => sendJson<{ results: StudyHit[] }>(`${BASE}/search`, 'POST', { q });
