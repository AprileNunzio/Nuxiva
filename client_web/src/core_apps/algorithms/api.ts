import { sendJson } from '../shared/http';
import { AlgorithmTest } from './types';

const enc = (key: string) => key.split('/').map(encodeURIComponent).join('/');

export const setEnabled = (key: string, enabled: boolean) => sendJson(`/api/skills/${enc(key)}`, 'PUT', { enabled });
export const removeAlgorithm = (key: string) => sendJson(`/api/skills/${enc(key)}`, 'DELETE');
export const testAlgorithm = (key: string, text: string) => sendJson<AlgorithmTest>(`/api/skills/${enc(key)}/test`, 'POST', { text });
