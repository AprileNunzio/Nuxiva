export const HANDS_FEATURE_ID = 'hands';

export type HandsSettingKey = 'NUXIVA_HANDS_FPS' | 'NUXIVA_HANDS_COUNT' | 'NUXIVA_HANDS_MAX_MS';

export type HandFilter = 'any' | 'left' | 'right' | 'dominant' | 'secondary';
export type Handedness = 'left' | 'right' | 'unknown';

export interface GestureBinding {
  gesture: string;
  hand: HandFilter;
  context: string;
  modifier: string | null;
  action: string;
  args: Record<string, string>;
  confirm: boolean;
  enabled: boolean;
}

export interface GestureProfile {
  version: number;
  mirror: boolean;
  dominant: Handedness;
  pointer: boolean;
  pinch_on: number;
  pinch_off: number;
  follow: number;
  follow_window_ms: number;
  lost_ms: number;
  flick_speed: number;
  flick_window_ms: number;
  zone: { x0: number; x1: number; y0: number; y1: number };
  smoothing: { min_cutoff: number; beta: number };
  motion: {
    swipe_distance: number;
    swipe_speed: number;
    swipe_window_ms: number;
    circle_window_ms: number;
    circle_min_radius: number;
    cooldown_ms: number;
    hold_ms: number;
    tap_max_ms: number;
    double_tap_ms: number;
    stable_frames: number;
  };
  duo: Record<string, number>;
  bindings: GestureBinding[];
}

export interface RecentEvent {
  type: 'gesture' | 'action';
  gesture: string;
  hand: Handedness;
  action?: string;
  confidence?: number;
}

export interface HandsView {
  native: boolean;
  profile: GestureProfile | Record<string, never>;
  catalog: string[];
  actions: string[];
  contexts: string[];
  recent: RecentEvent[];
}

export const HAND_FILTERS: readonly HandFilter[] = ['any', 'dominant', 'secondary', 'left', 'right'];
export const MODIFIER_POSES: readonly string[] = ['open_palm', 'fist', 'point', 'victory', 'three', 'four', 'rock_on', 'call_me', 'thumbs_up', 'thumbs_down', 'ok_sign'];
export const IDENTIFIER = /^[a-z0-9_.-]{1,64}$/;
