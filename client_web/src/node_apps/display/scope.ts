import { SettingSpec } from '../shared/data/schema';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function useDisplayI18n() {
  return useScopedI18n('node_apps/display');
}

export const APPEARANCE_SPECS: readonly SettingSpec[] = [
  { key: 'NUXIVA_AVATAR', kind: 'choice', options: ['auto', 'full', 'light'], fallback: 'auto' },
  { key: 'NUXIVA_AVATAR_STYLE', kind: 'choice', options: ['character', 'hologram'], fallback: 'character' },
  { key: 'NUXIVA_FACE_COLOR', kind: 'color', fallback: '#29e0ff' },
];

export const KIOSK_SPECS: readonly SettingSpec[] = [
  { key: 'NUXIVA_KIOSK', kind: 'toggle', fallback: true },
  { key: 'NUXIVA_GPU_DRIVER', kind: 'choice', options: ['auto', 'nouveau'], fallback: 'auto' },
  { key: 'NUXIVA_GPU_DRIVER_REBOOT', kind: 'choice', options: ['night', 'now'], fallback: 'night' },
];

export const fieldClass =
  'rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-cyan-400/70 focus-visible:ring-2 focus-visible:ring-cyan-400/40';
