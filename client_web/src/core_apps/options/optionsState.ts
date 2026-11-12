import { SystemSwitchOption } from './types';

const STORAGE_KEY = 'nuxiva_system_options_v2';

export const DEFAULT_OPTIONS: SystemSwitchOption[] = [
  {
    id: 'multimedia_music_display_on_screen',
    category: 'multimedia',
    enabled: true,
    defaultEnabled: true,
    titleKey: 'opt_music_display_title',
    descriptionKey: 'opt_music_display_desc',
    tags: ['canzone', 'musica', 'schermo', 'song', 'music', 'display', 'screen', 'audio'],
  },
  {
    id: 'multimedia_music_recognition',
    category: 'multimedia',
    enabled: true,
    defaultEnabled: true,
    titleKey: 'opt_music_recognition_title',
    descriptionKey: 'opt_music_recognition_desc',
    tags: ['riconoscimento', 'fingerprint', 'shazam', 'acustico', 'acoustic', 'identify'],
  },
  {
    id: 'security_alarm_system',
    category: 'security',
    enabled: false,
    defaultEnabled: false,
    titleKey: 'opt_alarm_system_title',
    descriptionKey: 'opt_alarm_system_desc',
    tags: ['allarme', 'sicurezza', 'antintrusione', 'alarm', 'security', 'intrusion'],
  },
  {
    id: 'security_red_alert',
    category: 'security',
    enabled: false,
    defaultEnabled: false,
    titleKey: 'opt_red_alert_title',
    descriptionKey: 'opt_red_alert_desc',
    tags: ['allarme rosso', 'rosso', 'emergenza', 'red alert', 'emergency', 'lock'],
  },
  {
    id: 'security_camera_motion_alerts',
    category: 'security',
    enabled: true,
    defaultEnabled: true,
    titleKey: 'opt_camera_alerts_title',
    descriptionKey: 'opt_camera_alerts_desc',
    tags: ['telecamere', 'movimento', 'motion', 'camera', 'notifiche', 'alert'],
  },
  {
    id: 'ai_voice_continuous_listening',
    category: 'ai_voice',
    enabled: true,
    defaultEnabled: true,
    titleKey: 'opt_voice_listening_title',
    descriptionKey: 'opt_voice_listening_desc',
    tags: ['voce', 'ascolto', 'wake word', 'voice', 'listening', 'mic'],
  },
  {
    id: 'ai_voice_speech_feedback',
    category: 'ai_voice',
    enabled: true,
    defaultEnabled: true,
    titleKey: 'opt_speech_feedback_title',
    descriptionKey: 'opt_speech_feedback_desc',
    tags: ['sintesi', 'audio', 'tts', 'speech', 'feedback', 'risposta'],
  },
  {
    id: 'ai_mcp_autonomous_tools',
    category: 'ai_voice',
    enabled: true,
    defaultEnabled: true,
    titleKey: 'opt_mcp_tools_title',
    descriptionKey: 'opt_mcp_tools_desc',
    tags: ['mcp', 'tools', 'agenti', 'protocol', 'autonomia'],
  },
  {
    id: 'display_kiosk_hud',
    category: 'display',
    enabled: true,
    defaultEnabled: true,
    titleKey: 'opt_kiosk_hud_title',
    descriptionKey: 'opt_kiosk_hud_desc',
    tags: ['hud', 'kiosk', 'desktop', 'widget', 'indicatori'],
  },
  {
    id: 'display_song_lyrics_overlay',
    category: 'display',
    enabled: true,
    defaultEnabled: true,
    titleKey: 'opt_lyrics_overlay_title',
    descriptionKey: 'opt_lyrics_overlay_desc',
    tags: ['testi', 'karaoke', 'overlay', 'lyrics', 'canzone'],
  },
  {
    id: 'privacy_vitals_tracking',
    category: 'privacy',
    enabled: false,
    defaultEnabled: false,
    titleKey: 'opt_vitals_tracking_title',
    descriptionKey: 'opt_vitals_tracking_desc',
    tags: ['vitali', 'presenza', 'salute', 'vitals', 'sensors', 'privacy'],
  },
];

export function loadStoredOptions(): SystemSwitchOption[] {
  if (typeof window === 'undefined') return DEFAULT_OPTIONS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_OPTIONS;
    const storedMap = JSON.parse(raw) as Record<string, boolean>;
    return DEFAULT_OPTIONS.map((opt) => ({
      ...opt,
      enabled: storedMap[opt.id] ?? opt.defaultEnabled,
    }));
  } catch {
    return DEFAULT_OPTIONS;
  }
}

export function saveStoredOption(id: string, enabled: boolean): void {
  if (typeof window === 'undefined') return;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const storedMap = raw ? (JSON.parse(raw) as Record<string, boolean>) : {};
    storedMap[id] = enabled;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(storedMap));
  } catch {
  }
}
