import { asRecord, asString, requestJson } from '../../shared/data/http';

export const ROLES = ['auto', 'output', 'input', 'both', 'off'] as const;
export const PROFILES = ['auto', 'quality', 'headset'] as const;
export const GLOBAL_PREFS = ['auto_switch', 'auto_connect', 'announce'] as const;
export const ACTIONS = ['pair', 'connect', 'disconnect', 'forget'] as const;

export type Role = (typeof ROLES)[number];
export type Profile = (typeof PROFILES)[number];
export type GlobalPref = (typeof GLOBAL_PREFS)[number];
export type DeviceAction = (typeof ACTIONS)[number];

export interface Controller {
  readonly present: boolean;
  readonly installed: boolean;
  readonly powered: boolean;
  readonly discovering: boolean;
  readonly name: string | null;
  readonly address: string | null;
}

export interface DeviceSettings {
  readonly role: Role;
  readonly profile: Profile;
  readonly autoconnect: boolean;
}

export interface BluetoothDevice {
  readonly mac: string;
  readonly name: string;
  readonly icon: string;
  readonly paired: boolean;
  readonly trusted: boolean;
  readonly connected: boolean;
  readonly battery: number | null;
  readonly audioOut: boolean;
  readonly audioIn: boolean;
  readonly settings: DeviceSettings;
}

export interface BluetoothState {
  readonly enabled: boolean;
  readonly scanning: boolean;
  readonly controller: Controller;
  readonly devices: readonly BluetoothDevice[];
  readonly outputOrder: readonly string[];
  readonly inputOrder: readonly string[];
  readonly globals: Readonly<Record<GlobalPref, boolean>>;
  readonly activeOutput: string | null;
  readonly activeInput: string | null;
}

export const MAC = /^[0-9A-F]{2}(:[0-9A-F]{2}){5}$/;

const pick = <T extends string>(values: readonly T[], value: unknown, fallback: T): T => values.find((v) => v === value) ?? fallback;
const macOrNull = (value: unknown): string | null => (typeof value === 'string' && MAC.test(value) ? value : null);
const macList = (value: unknown): string[] => (Array.isArray(value) ? value.map(macOrNull).filter((m): m is string => m !== null).slice(0, 32) : []);

function parseDevice(value: unknown): BluetoothDevice | null {
  const d = asRecord(value);
  const mac = macOrNull(d.mac);
  if (!mac) {
    return null;
  }
  const s = asRecord(d.settings);
  const battery = typeof d.battery === 'number' && d.battery >= 0 && d.battery <= 100 ? Math.round(d.battery) : null;
  return {
    mac,
    name: asString(d.name, 80) ?? mac,
    icon: asString(d.icon, 40) ?? '',
    paired: d.paired === true,
    trusted: d.trusted === true,
    connected: d.connected === true,
    battery,
    audioOut: d.audio_out === true,
    audioIn: d.audio_in === true,
    settings: {
      role: pick(ROLES, s.role, 'auto'),
      profile: pick(PROFILES, s.profile, 'auto'),
      autoconnect: s.autoconnect !== false,
    },
  };
}

function parseState(value: unknown): BluetoothState {
  const raw = asRecord(value);
  const c = asRecord(raw.controller);
  const prefs = asRecord(raw.prefs);
  const routing = asRecord(raw.routing);
  return {
    enabled: raw.enabled !== false,
    scanning: raw.scanning === true,
    controller: {
      present: c.present === true,
      installed: c.installed === true,
      powered: c.powered === true,
      discovering: c.discovering === true,
      name: asString(c.name, 80),
      address: macOrNull(c.address),
    },
    devices: (Array.isArray(raw.devices) ? raw.devices : []).map(parseDevice).filter((d): d is BluetoothDevice => d !== null),
    outputOrder: macList(prefs.output_order),
    inputOrder: macList(prefs.input_order),
    globals: {
      auto_switch: prefs.auto_switch !== false,
      auto_connect: prefs.auto_connect !== false,
      announce: prefs.announce !== false,
    },
    activeOutput: macOrNull(routing.output),
    activeInput: macOrNull(routing.input),
  };
}

export async function fetchBluetooth(signal?: AbortSignal): Promise<BluetoothState> {
  return parseState(await requestJson<unknown>('/api/bluetooth', { signal }));
}

export async function startScan(): Promise<number> {
  const raw = asRecord(await requestJson<unknown>('/api/bluetooth/scan', { method: 'POST' }));
  return typeof raw.seconds === 'number' ? raw.seconds : 20;
}

export async function setPower(on: boolean): Promise<BluetoothState> {
  return parseState(await requestJson<unknown>('/api/bluetooth/power', { method: 'POST', body: JSON.stringify({ on }) }));
}

export async function runAction(mac: string, action: DeviceAction): Promise<BluetoothState> {
  if (!MAC.test(mac)) {
    throw new Error('invalid_mac');
  }
  return parseState(await requestJson<unknown>(`/api/bluetooth/devices/${encodeURIComponent(mac)}/${action}`, { method: 'POST' }));
}

export interface PrefsChange {
  readonly output_order?: readonly string[];
  readonly input_order?: readonly string[];
  readonly auto_switch?: boolean;
  readonly auto_connect?: boolean;
  readonly announce?: boolean;
  readonly devices?: Readonly<Record<string, Partial<DeviceSettings>>>;
}

export async function updatePrefs(change: PrefsChange): Promise<BluetoothState> {
  return parseState(await requestJson<unknown>('/api/bluetooth/prefs', { method: 'PUT', body: JSON.stringify(change) }));
}
