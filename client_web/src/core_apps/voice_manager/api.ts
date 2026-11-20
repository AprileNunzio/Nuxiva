import { asObject, getJson, num, sendJson, text } from '../shared/http';
import {
  AudioVaultClip,
  AudioVaultStats,
  ElevenLabsSubscription,
  ElevenLabsVoice,
  EngineKind,
  EngineSettings,
  VoiceItem,
  VoiceOverview,
} from './types';

const ENGINES: readonly EngineKind[] = ['kokoro', 'piper', 'online', 'studio', 'elevenlabs'];

const parseVoice = (raw: unknown): VoiceItem => {
  const item = asObject(raw);
  const engine = (ENGINES.find((value) => value === item.engine) ?? 'piper') as EngineKind;
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
  const vaultRaw = asObject(data.vault_stats);

  const vaultStats: AudioVaultStats | undefined = data.vault_stats ? {
    total_clips: num(vaultRaw.total_clips),
    total_hits: num(vaultRaw.total_hits),
    total_chars_saved: num(vaultRaw.total_chars_saved),
    equivalent_free_plans_saved: num(vaultRaw.equivalent_free_plans_saved),
    total_size_mb: num(vaultRaw.total_size_mb),
    common_phrases_count: num(vaultRaw.common_phrases_count),
  } : undefined;

  return {
    order: list(data.order),
    custom: data.custom === true,
    voices: list(data.voices),
    langs: Object.fromEntries(Object.entries(langs).map(([code, label]) => [code, text(label, code)])),
    langPrefs: Object.fromEntries(Object.entries(prefs).map(([code, voice]) => [code, text(voice)])),
    fallback: text(data.fallback),
    onlineEnabled: data.online_enabled === true,
    autoDownload: data.auto_download === true,
    engine_mode: (text(data.engine_mode) as any) || 'hybrid',
    elevenlabs_configured: data.elevenlabs_configured === true,
    vault_stats: vaultStats,
  };
};

export const fetchOverview = async (): Promise<VoiceOverview> => parseOverview(await getJson('/api/voices'));

export const saveOrder = (order: string[]) => sendJson('/api/voices', 'PUT', { order });
export const downloadVoice = (voice: string) => sendJson('/api/voices/download', 'POST', { voice });
export const removeVoice = (voice: string) => sendJson(`/api/voices/${encodeURIComponent(voice)}`, 'DELETE');
export const setLanguageVoice = (lang: string, voice: string) => sendJson('/api/voices/language', 'PUT', { lang, voice });

export async function previewAudio(voice: string, testText?: string): Promise<Blob> {
  const response = await fetch('/api/voices/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ voice, text: testText }),
  });
  if (!response.ok) {
    const data = asObject(await response.json().catch(() => ({})));
    throw new Error(text(data.detail, `HTTP ${response.status}`));
  }
  return response.blob();
}

// =========================================================================
// ENGINE STRATEGY & TUNING API
// =========================================================================

export const fetchEngineSettings = async (): Promise<EngineSettings> => {
  const raw = asObject(await getJson('/api/voices/engine'));
  return {
    engine_mode: (text(raw.engine_mode) as any) || 'hybrid',
    elevenlabs_voice_id: text(raw.elevenlabs_voice_id, '21m00Tcm4TlvDq8ikWAM'),
    fallback_local: text(raw.fallback_local, 'if_sara'),
    elevenlabs_configured: raw.elevenlabs_configured === true,
    speed: num(raw.speed, 1.0),
    pitch: num(raw.pitch, 0.0),
    volume: num(raw.volume, 1.0),
    stability: num(raw.stability, 0.65),
    similarity_boost: num(raw.similarity_boost, 0.75),
  };
};

export const saveEngineSettings = (settings: Partial<EngineSettings>) => sendJson('/api/voices/engine', 'PUT', settings);

// =========================================================================
// ELEVENLABS API
// =========================================================================

export const fetchElevenLabsStatus = async (): Promise<ElevenLabsSubscription> => {
  const raw = asObject(await getJson('/api/voices/elevenlabs/status'));
  return {
    configured: raw.configured === true,
    tier: text(raw.tier, 'none'),
    character_count: num(raw.character_count),
    character_limit: num(raw.character_limit),
    remaining_characters: num(raw.remaining_characters),
    percent_used: num(raw.percent_used),
    next_reset_days: num(raw.next_reset_days),
    status: text(raw.status, 'unconfigured'),
    message: raw.message ? text(raw.message) : undefined,
  };
};

export const saveElevenLabsKey = (apiKey: string) => sendJson('/api/voices/elevenlabs/key', 'POST', { api_key: apiKey });

export const fetchElevenLabsVoices = async (): Promise<ElevenLabsVoice[]> => {
  const raw = asObject(await getJson('/api/voices/elevenlabs/voices'));
  const list = Array.isArray(raw.voices) ? raw.voices : [];
  return list.map((v) => {
    const o = asObject(v);
    return {
      id: text(o.id),
      name: text(o.name),
      category: text(o.category, 'premade'),
      preview_url: text(o.preview_url),
      gender: text(o.gender),
      accent: text(o.accent),
      description: text(o.description),
    };
  });
};

export async function testElevenLabsSpeech(voiceId: string, testText: string): Promise<Blob> {
  const response = await fetch('/api/voices/elevenlabs/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ voice_id: voiceId, text: testText }),
  });
  if (!response.ok) {
    const data = asObject(await response.json().catch(() => ({})));
    throw new Error(text(data.detail, `HTTP ${response.status}`));
  }
  return response.blob();
}

// =========================================================================
// AUDIO VAULT (CASSAFORTE RISPARMIO CREDITI/TOKEN)
// =========================================================================

export const fetchVaultStats = async (): Promise<AudioVaultStats> => {
  const raw = asObject(await getJson('/api/voices/vault/stats'));
  return {
    total_clips: num(raw.total_clips),
    total_hits: num(raw.total_hits),
    total_chars_saved: num(raw.total_chars_saved),
    equivalent_free_plans_saved: num(raw.equivalent_free_plans_saved),
    total_size_mb: num(raw.total_size_mb),
    common_phrases_count: num(raw.common_phrases_count),
  };
};

export const fetchVaultClips = async (q: string = ''): Promise<AudioVaultClip[]> => {
  const raw = asObject(await getJson(`/api/voices/vault/clips${q ? `?q=${encodeURIComponent(q)}` : ''}`));
  const list = Array.isArray(raw.clips) ? raw.clips : [];
  return list.map((c) => {
    const o = asObject(c);
    return {
      id: text(o.id),
      text: text(o.text),
      voice_id: text(o.voice_id),
      engine: text(o.engine),
      char_count: num(o.char_count),
      hit_count: num(o.hit_count),
      chars_saved: num(o.chars_saved),
      created_at: text(o.created_at),
      last_used_at: text(o.last_used_at),
      pinned: o.pinned === true,
      file_size: typeof o.file_size === 'number' ? num(o.file_size) : undefined,
    };
  });
};

export const deleteVaultClip = (clipId: string) => sendJson(`/api/voices/vault/clips/${encodeURIComponent(clipId)}`, 'DELETE');

export const pregenerateVaultClips = (voice?: string) => sendJson('/api/voices/vault/pregenerate', 'POST', { voice });

export const clearVaultClips = () => sendJson('/api/voices/vault/clear', 'POST', {});

export const speakToRoom = (speechText: string, lang?: string) => sendJson('/api/voice/speak', 'POST', { text: speechText, lang });
