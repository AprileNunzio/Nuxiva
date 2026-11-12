export const DEVICE_KINDS = [
  'speaker',
  'headphones',
  'headset',
  'microphone',
  'keyboard',
  'mouse',
  'gamepad',
  'joystick',
  'phone',
  'computer',
  'wearable',
  'other',
] as const;
export const CAPABILITIES = ['audio_out', 'audio_in', 'pointer', 'keyboard', 'gamepad'] as const;
export const SETTING_GROUPS = ['general', ...CAPABILITIES] as const;
export const GLOBAL_PREFS = ['auto_switch', 'auto_connect', 'announce'] as const;
export const DEVICE_ACTIONS = ['pair', 'connect', 'disconnect', 'forget', 'trust', 'untrust'] as const;
export const AUDIO_SIDES = ['output', 'input'] as const;

export type DeviceKind = (typeof DEVICE_KINDS)[number];
export type Capability = (typeof CAPABILITIES)[number];
export type SettingGroup = (typeof SETTING_GROUPS)[number];
export type GlobalPref = (typeof GLOBAL_PREFS)[number];
export type DeviceAction = (typeof DEVICE_ACTIONS)[number];
export type AudioSide = (typeof AUDIO_SIDES)[number];
export type SettingValue = string | number | boolean;

interface SettingBase {
  readonly key: string;
  readonly group: SettingGroup;
  readonly requires: readonly Capability[];
}

export type SettingSpec =
  | (SettingBase & { readonly type: 'bool'; readonly default: boolean })
  | (SettingBase & { readonly type: 'int'; readonly default: number; readonly min: number; readonly max: number; readonly step: number })
  | (SettingBase & { readonly type: 'enum'; readonly default: string; readonly options: readonly string[] })
  | (SettingBase & { readonly type: 'text'; readonly default: string; readonly max: number });

export interface Controller {
  readonly present: boolean;
  readonly installed: boolean;
  readonly powered: boolean;
  readonly discovering: boolean;
  readonly name: string | null;
  readonly address: string | null;
}

export interface BluetoothDevice {
  readonly mac: string;
  readonly name: string;
  readonly kind: DeviceKind;
  readonly capabilities: readonly Capability[];
  readonly paired: boolean;
  readonly trusted: boolean;
  readonly blocked: boolean;
  readonly connected: boolean;
  readonly battery: number | null;
  readonly rssi: number | null;
  readonly settings: Readonly<Record<string, SettingValue>>;
}

export interface BluetoothState {
  readonly enabled: boolean;
  readonly scanning: boolean;
  readonly controller: Controller;
  readonly devices: readonly BluetoothDevice[];
  readonly schema: readonly SettingSpec[];
  readonly outputOrder: readonly string[];
  readonly inputOrder: readonly string[];
  readonly globals: Readonly<Record<GlobalPref, boolean>>;
  readonly activeOutput: string | null;
  readonly activeInput: string | null;
  readonly notice: string | null;
}

export const MAC = /^[0-9A-F]{2}(:[0-9A-F]{2}){5}$/;

export const isReady = (state: BluetoothState | null): boolean =>
  state !== null && state.enabled && state.controller.present && state.controller.installed;

export const displayName = (device: BluetoothDevice): string => {
  const alias = device.settings.alias;
  return typeof alias === 'string' && alias.trim() ? alias : device.name;
};

export const appliesTo = (spec: SettingSpec, device: BluetoothDevice): boolean =>
  spec.group === 'general' || spec.requires.every((cap) => device.capabilities.includes(cap));

export const hasAudio = (device: BluetoothDevice): boolean =>
  device.capabilities.includes('audio_out') || device.capabilities.includes('audio_in');
