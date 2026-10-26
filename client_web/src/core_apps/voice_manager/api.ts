import { asObject, getJson, num, sendJson, text } from '../shared/http';
import { VoiceItem, VoiceOverview } from './types';

const ENGINES = ['kokoro', 'piper', 'online', 'studio'] as const;

const parseVoice = (raw: unknown): VoiceItem => {
  const item = asObject(raw);
  const engine = ENGINES.find((value) => value === item.engine) ?? 'piper';
  return {
    id: text(item.id),
    name: text(item.name),
    gender: text(item.gender),
    lang: text(item.lang),
    locale: text(item.locale),
    engine,
    quality: text(item.quality),
    sizeMb: typeof item.size_mb === 'number' ? num(item.size_mb) : null,
    installed: item.installed === true,
    downloadable: item.downloadable === true,
    downloading: item.downloading === true,
    preferred: item.preferred === true,
  };
};

const list = (value: unknown): VoiceItem[] => (Array.isArray(value) ? value.map(parseVoice) : []);

export const parseOverview = (raw: unknown): VoiceOverview => {
  const data = asObject(raw);
  const langs = asObject(data.langs);
  const prefs = asObject(data.lang_prefs);
  return {
    order: list(data.order),
    custom: data.custom === true,
    voices: list(data.voices),
    langs: Object.fromEntries(Object.entries(langs).map(([code, label]) => [code, text(label, code)])),
    langPrefs: Object.fromEntries(Object.entries(prefs).map(([code, voice]) => [code, text(voice)])),
    fallback: text(data.fallback),
    onlineEnabled: data.online_enabled === true,
    autoDownload: data.auto_download === true,
  };
};

export const fetchOverview = async (): Promise<VoiceOverview> => parseOverview(await getJson('/api/voices'));

export const saveOrder = (order: string[]) => sendJson('/api/voices', 'PUT', { order });
export const downloadVoice = (voice: string) => sendJson('/api/voices/download', 'POST', { voice });
export const removeVoice = (voice: string) => sendJson(`/api/voices/${encodeURIComponent(voice)}`, 'DELETE');
export const setLanguageVoice = (lang: string, voice: string) => sendJson('/api/voices/language', 'PUT', { lang, voice });

export async function previewAudio(voice: string): Promise<Blob> {
  const response = await fetch('/api/voices/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ voice }),
  });
  if (!response.ok) {
    const data = asObject(await response.json().catch(() => ({})));
    throw new Error(text(data.detail, `HTTP ${response.status}`));
  }
  return response.blob();
}
