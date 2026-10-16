import { sendJson } from '../shared/http';
import { CameraDraft } from './types';

export const addCamera = (draft: CameraDraft) => sendJson('/api/cameras', 'POST', draft);
export const patchCamera = (id: string, change: Readonly<Record<string, unknown>>) => sendJson(`/api/cameras/${encodeURIComponent(id)}`, 'PUT', change);
export const deleteCamera = (id: string) => sendJson(`/api/cameras/${encodeURIComponent(id)}`, 'DELETE');
