import { getJson, sendJson } from '../shared/http';
import { GooglePreview } from './types';

const enc = encodeURIComponent;

export const authUrl = (slug: string, services: readonly string[]) => sendJson<{ url: string }>(`/api/google/${enc(slug)}/auth-url`, 'POST', { services });
export const finishLink = (slug: string, url: string) => sendJson('/api/google/finish', 'POST', { slug, url });
export const cancelLink = (slug: string) => sendJson(`/api/google/${enc(slug)}/pending`, 'DELETE');
export const unlink = (slug: string) => sendJson(`/api/google/${enc(slug)}`, 'DELETE');
export const preview = (slug: string) => getJson<GooglePreview>(`/api/google/${enc(slug)}/preview`);
