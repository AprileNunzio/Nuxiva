import { NodeModuleError } from '../../node_apps/shared/data/http';
import { asList, asObject, getJson, sendJson, text } from '../shared/http';
import type { Catalog, CastDevice, ChatTurn, Genre, Project, Summary, VoiceChoice } from './types';

const BASE = '/api/musicstudio';
const WAV_HEADERS = { 'Content-Type': 'audio/wav', Accept: 'application/json', 'X-Nuxiva-Request': '1' };

export interface SourceFile {
  readonly path: string;
  readonly name: string;
  readonly size: number;
}

export const loadCatalog = (signal?: AbortSignal) => getJson<Catalog>(`${BASE}/catalog`, signal);

export const listProjects = async (signal?: AbortSignal): Promise<Summary[]> =>
  asList<Summary>(asObject(await getJson(`${BASE}/projects`, signal)).projects);

export const loadProject = (id: string, signal?: AbortSignal) => getJson<Project>(`${BASE}/projects/${id}`, signal);

export const createProject = (prompt: string) => sendJson<Project>(`${BASE}/projects`, 'POST', { prompt });

export const saveProject = (project: Project) => sendJson<Project>(`${BASE}/projects/${project.id}`, 'PUT', project);

export const removeProject = (id: string) => sendJson(`${BASE}/projects/${id}`, 'DELETE');

export const addLayer = (id: string, role: string, instrument: string) =>
  sendJson<Project>(`${BASE}/projects/${id}/layers`, 'POST', { role, instrument });

export const addVocals = (id: string, textBody: string, lang: string, voice: string) =>
  sendJson<Project>(`${BASE}/projects/${id}/vocals`, 'POST', { text: textBody, lang, voice });

export const translateProject = (id: string, lang: string, sing: boolean, voice: string) =>
  sendJson<Project>(`${BASE}/projects/${id}/translate`, 'POST', { lang, sing, voice });

export const revoiceTrack = (id: string, track: string, voice: string, speed?: number) =>
  sendJson<Project>(`${BASE}/projects/${id}/tracks/${track}/voice`, 'POST', speed === undefined ? { voice } : { voice, speed });

export const listVoices = async (lang: string): Promise<VoiceChoice[]> =>
  asList<VoiceChoice>(asObject(await getJson(`${BASE}/voices?lang=${encodeURIComponent(lang)}`)).voices);

export const listSources = async (kind: string): Promise<SourceFile[]> =>
  asList<SourceFile>(asObject(await getJson(`${BASE}/sources/${encodeURIComponent(kind)}`)).files);

export const importAudio = (id: string, source: string, path: string) =>
  sendJson<Project>(`${BASE}/projects/${id}/imports`, 'POST', { source, path });

export const chatWithAgent = async (id: string, message: string, history: readonly ChatTurn[]) => {
  const body = asObject(await sendJson(`${BASE}/projects/${id}/chat`, 'POST', { message, history: history.slice(-12) }));
  return { reply: text(body.reply), project: body.project as Project };
};

export const listDevices = async (refresh: boolean): Promise<CastDevice[]> =>
  asList<CastDevice>(asObject(await getJson(`${BASE}/cast/devices?refresh=${refresh}`)).devices);

export const castProject = (id: string, devices: readonly string[], everyone: boolean) =>
  sendJson(`${BASE}/projects/${id}/cast`, 'POST', { devices, everyone });

export const stopCast = (devices: readonly string[], everyone: boolean) => sendJson(`${BASE}/cast/stop`, 'POST', { devices, everyone });

export const writeLyrics = async (topic: string, genre: string, lang: string) =>
  text(asObject(await sendJson(`${BASE}/lyrics`, 'POST', { topic, genre, lang })).text);

export const fetchAsset = async (id: string, name: string, signal?: AbortSignal): Promise<ArrayBuffer> => {
  const response = await fetch(`${BASE}/projects/${id}/assets/${encodeURIComponent(name)}`, { cache: 'no-store', signal });
  if (!response.ok) throw new NodeModuleError('asset_unknown', response.status);
  return response.arrayBuffer();
};

export const exportMix = async (id: string, wav: Blob) => {
  const response = await fetch(`${BASE}/projects/${id}/export`, { method: 'POST', headers: WAV_HEADERS, body: wav });
  if (!response.ok) throw new NodeModuleError('export_failed', response.status);
  return asObject(await response.json());
};

export const genreFamilies = (genres: readonly string[]): Genre[] =>
  genres.map((id) => ({ id, name: id.replace(/_/g, ' '), family: '', tempo: [60, 140] as const }));
