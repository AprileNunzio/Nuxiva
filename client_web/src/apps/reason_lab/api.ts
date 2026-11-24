import { download } from '../../shared/http/download';
import { getJson, sendJson } from '../shared/http';
import type { BrainRole, Dataset, Profile, Row, Run, RunReport, RunSpec, Scenario, Summary } from './types';

export const BASE = '/api/v5/reason-lab';
export const statusUrl = `${BASE}/status`;
export const datasetsUrl = `${BASE}/datasets`;
export const profilesUrl = `${BASE}/profiles`;
export const presetsUrl = `${BASE}/presets`;
export const brainUrl = (role: BrainRole) => `${BASE}/brain?role=${role}`;
export const runsUrl = `${BASE}/runs`;
export const reportUrl = (id: string) => `${runsUrl}/${encodeURIComponent(id)}/report`;
export const rowsUrl = (id: string, only: string, lang: string, offset: number, limit: number) =>
  `${runsUrl}/${encodeURIComponent(id)}/rows?${new URLSearchParams({ only, lang, offset: String(offset), limit: String(limit) })}`;

export const loadDataset = (id: string) => getJson<Dataset>(`${datasetsUrl}/${encodeURIComponent(id)}`);
export const loadPreset = (id: string) =>
  sendJson<{ id: string; name: string; summary: Summary }>(`${presetsUrl}/${encodeURIComponent(id)}/load`, 'POST');
export const loadTemplate = () => getJson<{ scenarios: Scenario[] }>(`${BASE}/template`);
export const inspectDataset = (name: string, scenarios: Scenario[]) =>
  sendJson<Summary>(`${datasetsUrl}/inspect`, 'POST', { name, scenarios });
export const saveDataset = (id: string, name: string, scenarios: Scenario[]) =>
  sendJson(`${datasetsUrl}/${encodeURIComponent(id)}`, 'PUT', { name, scenarios });
export const removeDataset = (id: string) => sendJson(`${datasetsUrl}/${encodeURIComponent(id)}`, 'DELETE');
export const exportDataset = (id: string) => download(`${datasetsUrl}/${encodeURIComponent(id)}/export`, `${id}.json`);

export const saveProfile = (profile: Omit<Profile, never>) =>
  sendJson(`${profilesUrl}/${encodeURIComponent(profile.id)}`, 'PUT', {
    name: profile.name,
    backend: profile.backend,
    base_url: profile.base_url,
    model: profile.model,
    timeout_seconds: profile.timeout_seconds,
  });
export const removeProfile = (id: string) => sendJson(`${profilesUrl}/${encodeURIComponent(id)}`, 'DELETE');

export const startRun = (spec: RunSpec) => sendJson<Run>(runsUrl, 'POST', spec);
export const cancelRun = (id: string) => sendJson(`${runsUrl}/${encodeURIComponent(id)}/cancel`, 'POST');
export const removeRun = (id: string) => sendJson(`${runsUrl}/${encodeURIComponent(id)}`, 'DELETE');
export const loadReport = (id: string, signal?: AbortSignal) => getJson<RunReport>(reportUrl(id), signal);
export const loadRows = (id: string, only: string, lang: string, offset: number, limit: number, signal?: AbortSignal) =>
  getJson<{ total: number; rows: Row[] }>(rowsUrl(id, only, lang, offset, limit), signal);

const EXTENSIONS: Record<string, string> = { outcomes: 'jsonl', report: 'json', csv: 'csv' };
export const downloadRun = (id: string, kind: 'outcomes' | 'report' | 'csv') =>
  download(`${runsUrl}/${encodeURIComponent(id)}/download?kind=${kind}`, `nuxiva-lab-${id}.${EXTENSIONS[kind]}`);
