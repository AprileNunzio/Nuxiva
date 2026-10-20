import { sendJson } from '../shared/http';

export const saveDraft = (picks: Readonly<Record<string, string>>, template = '') => sendJson('/api/flows/draft', 'PUT', { picks, template });
export const discardDraft = () => sendJson('/api/flows/draft', 'DELETE');
export const publish = (password: string) => sendJson('/api/flows/publish', 'POST', { password });
export const rollback = (version: number, password: string) => sendJson(`/api/flows/rollback/${version}`, 'POST', { password });
