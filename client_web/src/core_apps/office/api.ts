import { adminPath } from '../../shared/http/basePath';
import { sendJson } from '../shared/http';

export const createDocument = (request: string) => sendJson('/api/documents', 'POST', { request });
export const fileUrl = (id: string, index: number) => adminPath(`/api/documents/${encodeURIComponent(id)}/file/${index}`);
export const previewUrl = (id: string) => adminPath(`/api/documents/${encodeURIComponent(id)}/preview.pdf`);
