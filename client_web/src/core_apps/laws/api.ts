import { sendJson } from '../shared/http';

export const addLaw = (text: string) => sendJson('/api/laws', 'POST', { text });
export const updateLaw = (id: string, text: string) => sendJson(`/api/laws/${encodeURIComponent(id)}`, 'PUT', { text });
export const deleteLaw = (id: string) => sendJson(`/api/laws/${encodeURIComponent(id)}`, 'DELETE');
export const reorderLaws = (order: readonly string[]) => sendJson('/api/laws/reorder', 'POST', { order });
