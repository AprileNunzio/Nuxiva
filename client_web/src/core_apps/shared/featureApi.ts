import { sendJson } from './http';

const enc = encodeURIComponent;

export const setMode = (id: string, mode: string) => sendJson(`/api/features/${enc(id)}`, 'PUT', { mode });
export const setPinned = (id: string, pinned: boolean) => sendJson(`/api/features/${enc(id)}`, 'PUT', { pinned });
export const saveSettings = (id: string, values: Readonly<Record<string, string>>) => sendJson(`/api/features/${enc(id)}/settings`, 'PUT', values);
export const rescan = () => sendJson('/api/features/rescan', 'POST');
