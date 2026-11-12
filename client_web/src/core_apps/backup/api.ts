import { adminPath } from '../../shared/http/basePath';
import { sendJson } from '../shared/http';
import { VerifyResult } from './types';

const enc = encodeURIComponent;

export const createBackup = () => sendJson('/api/backup', 'POST');
export const verifyBackup = (id: string) => sendJson<VerifyResult>(`/api/backup/${enc(id)}/verify`, 'POST');
export const deleteBackup = (id: string) => sendJson(`/api/backup/${enc(id)}`, 'DELETE');
export const downloadUrl = (id: string) => adminPath(`/api/backup/${enc(id)}/download`);
