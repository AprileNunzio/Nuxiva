import { sendJson } from '../shared/http';
import { PeerResult, VpnDraft } from './types';

const BASE = '/api/vpn/profiles';
const enc = encodeURIComponent;

export const createProfile = (draft: VpnDraft) => sendJson(BASE, 'POST', draft);
export const patchProfile = (id: string, change: Readonly<Record<string, unknown>>) => sendJson(`${BASE}/${enc(id)}`, 'PUT', change);
export const deleteProfile = (id: string) => sendJson(`${BASE}/${enc(id)}`, 'DELETE');
export const connectProfile = (id: string) => sendJson(`${BASE}/${enc(id)}/connect`, 'POST');
export const disconnectProfile = (id: string) => sendJson(`${BASE}/${enc(id)}/disconnect`, 'POST');
export const addPeer = (id: string, name: string) => sendJson<PeerResult>(`${BASE}/${enc(id)}/peers`, 'POST', { name });
