import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { SettingSpec } from '../shared/data/schema';

export function useAudioI18n() {
  return useScopedI18n('node_apps/audio');
}

export const VOICE_SPECS: readonly SettingSpec[] = [
  { key: 'NUXIVA_VOICE_VOLUME', kind: 'range', min: 0.4, max: 2, step: 0.05, fallback: 1, unit: '×' },
  { key: 'NUXIVA_VOICE_SPEED', kind: 'range', min: 0.6, max: 1.6, step: 0.05, fallback: 1, unit: '×' },
  { key: 'NUXIVA_VOICE_PITCH', kind: 'range', min: -6, max: 6, step: 0.5, fallback: 0, unit: ' st' },
  { key: 'NUXIVA_QUIET_VOICE', kind: 'range', min: 0, max: 100, step: 1, fallback: 45, unit: '%' },
  { key: 'NUXIVA_SOUNDS_VOLUME', kind: 'range', min: 0, max: 100, step: 1, fallback: 55, unit: '%' },
  { key: 'NUXIVA_SOUNDS_AMBIENT_VOLUME', kind: 'range', min: 0, max: 100, step: 1, fallback: 18, unit: '%' },
];
