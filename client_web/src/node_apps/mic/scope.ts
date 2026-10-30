import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { SettingSpec } from '../shared/data/schema';

export function useMicI18n() {
  return useScopedI18n('node_apps/mic');
}

export const EAR_SPECS: readonly SettingSpec[] = [
  { key: 'NUXIVA_EAR', kind: 'toggle', fallback: true },
  { key: 'NUXIVA_EAR_MODE', kind: 'choice', options: ['offline', 'online', 'hybrid'], fallback: 'offline' },
  { key: 'NUXIVA_EAR_MULTILANG', kind: 'toggle', fallback: true },
  { key: 'NUXIVA_VOICEPRINT_ENFORCE', kind: 'toggle', fallback: false },
  { key: 'NUXIVA_EAR_AUTO_FOLLOWUP', kind: 'range', min: 0, max: 30, step: 1, fallback: 8, unit: ' s' },
  { key: 'NUXIVA_EAR_ENHANCE_ENGINE', kind: 'choice', options: ['auto', 'deepfilternet', 'spectral'], fallback: 'auto' },
  { key: 'NUXIVA_EAR_MAX_GAIN', kind: 'range', min: 2, max: 80, step: 1, fallback: 30, unit: '×' },
  { key: 'NUXIVA_EAR_TARGET_RMS', kind: 'range', min: 0.03, max: 0.2, step: 0.005, fallback: 0.075 },
];

export const EQ_SPECS: readonly SettingSpec[] = [
  { key: 'NUXIVA_EAR_EQ', kind: 'toggle', fallback: false },
  { key: 'NUXIVA_EAR_EQ_HIGHPASS', kind: 'range', min: 0, max: 300, step: 10, fallback: 0, unit: ' Hz' },
  { key: 'NUXIVA_EAR_EQ_LOW', kind: 'range', min: -12, max: 12, step: 0.5, fallback: 0, unit: ' dB' },
  { key: 'NUXIVA_EAR_EQ_MID', kind: 'range', min: -12, max: 12, step: 0.5, fallback: 0, unit: ' dB' },
  { key: 'NUXIVA_EAR_EQ_HIGH', kind: 'range', min: -12, max: 12, step: 0.5, fallback: 0, unit: ' dB' },
];
