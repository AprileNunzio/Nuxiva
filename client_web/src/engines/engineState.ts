import type { ActiveEnginesState, EngineFamily } from './types';
import { getDefaultEngineForFamily } from './registry';

const ACTIVE_ENGINES_KEY = 'nuxiva_active_engines_state';
const ENGINE_OPTIONS_KEY = 'nuxiva_engine_options_state';
const EVENT_ENGINE_CHANGED = 'nuxiva:active_engine_changed';

export function loadActiveEngines(): ActiveEnginesState {
  const fallback: ActiveEnginesState = {
    reasoning: getDefaultEngineForFamily('reasoning') || 'react_autonomous',
    speech_recognition: getDefaultEngineForFamily('speech_recognition') || 'web_speech',
    music_recognition: getDefaultEngineForFamily('music_recognition') || 'acoustid_chromaprint',
  };

  if (typeof window === 'undefined') return fallback;

  try {
    const raw = localStorage.getItem(ACTIVE_ENGINES_KEY);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return {
      reasoning: parsed.reasoning || fallback.reasoning,
      speech_recognition: parsed.speech_recognition || fallback.speech_recognition,
      music_recognition: parsed.music_recognition || fallback.music_recognition,
      vision: parsed.vision,
    };
  } catch {
    return fallback;
  }
}

export function saveActiveEngine(family: EngineFamily, engineId: string): void {
  if (typeof window === 'undefined') return;
  const current = loadActiveEngines();
  const updated: ActiveEnginesState = {
    ...current,
    [family]: engineId,
  };
  try {
    localStorage.setItem(ACTIVE_ENGINES_KEY, JSON.stringify(updated));
    window.dispatchEvent(new CustomEvent(EVENT_ENGINE_CHANGED, { detail: { family, engineId } }));
  } catch {}
}

export function loadEngineOption<T = unknown>(engineId: string, optionId: string, defaultValue: T): T {
  if (typeof window === 'undefined') return defaultValue;
  try {
    const raw = localStorage.getItem(ENGINE_OPTIONS_KEY);
    if (!raw) return defaultValue;
    const parsed = JSON.parse(raw) as Record<string, Record<string, T>>;
    const engineMap = parsed[engineId];
    if (!engineMap) return defaultValue;
    const val = engineMap[optionId];
    return val !== undefined ? val : defaultValue;
  } catch {
    return defaultValue;
  }
}

export function saveEngineOption<T = unknown>(engineId: string, optionId: string, value: T): void {
  if (typeof window === 'undefined') return;
  try {
    const raw = localStorage.getItem(ENGINE_OPTIONS_KEY);
    const parsed = raw ? (JSON.parse(raw) as Record<string, Record<string, T>>) : {};
    if (!parsed[engineId]) {
      parsed[engineId] = {};
    }
    const targetMap = parsed[engineId];
    if (targetMap) {
      targetMap[optionId] = value;
    }
    localStorage.setItem(ENGINE_OPTIONS_KEY, JSON.stringify(parsed));
  } catch {}
}
