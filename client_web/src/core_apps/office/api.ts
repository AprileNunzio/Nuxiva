import { sendJson } from '../shared/http';

export const createDocument = (request: string) => sendJson('/api/documents', 'POST', { request });
export const fileUrl = (id: string, index: number) => `/api/documents/${encodeURIComponent(id)}/file/${index}`;
export const previewUrl = (id: string) => `/api/documents/${encodeURIComponent(id)}/preview.pdf`;
