import { asRecord, asString } from '../../node_apps/shared/data/http';
import {
  BluetoothDevice,
  BluetoothState,
  CAPABILITIES,
  Capability,
  DEVICE_KINDS,
  MAC,
  SETTING_GROUPS,
  SettingSpec,
  SettingValue,
} from './model';

const MAX_DEVICES = 64;
const KEY = /^[a-z][a-z0-9_]{0,31}$/;

const pick = <T extends string>(values: readonly T[], value: unknown, fallback: T): T => values.find((v) => v === value) ?? fallback;
const macOrNull = (value: unknown): string | null => (typeof value === 'string' && MAC.test(value) ? value : null);
const macList = (value: unknown): string[] =>
  Array.isArray(value) ? value.map(macOrNull).filter((m): m is string => m !== null).slice(0, MAX_DEVICES) : [];
const finite = (value: unknown): number | null => (typeof value === 'number' && Number.isFinite(value) ? value : null);
const capList = (value: unknown): Capability[] =>
  Array.isArray(value) ? CAPABILITIES.filter((cap) => value.includes(cap)) : [];

function parseSpec(value: unknown): SettingSpec | null {
  const raw = asRecord(value);
  const key = typeof raw.key === 'string' && KEY.test(raw.key) ? raw.key : null;
  const group = SETTING_GROUPS.find((g) => g === raw.group);
  if (!key || !group) {
    return null;
  }
  const requires = Array.isArray(raw.requires) ? capList(raw.requires) : group === 'general' ? [] : [group as Capability];
  const base = { key, group, requires };
  if (raw.type === 'bool') {
    return { ...base, type: 'bool', default: raw.default === true };
  }
  if (raw.type === 'int') {
    const min = finite(raw.min) ?? 0;
    const max = Math.max(min, finite(raw.max) ?? min);
    return { ...base, type: 'int', min, max, step: Math.max(1, finite(raw.step) ?? 1), default: finite(raw.default) ?? min };
  }
  if (raw.type === 'enum') {
    const options = Array.isArray(raw.options) ? raw.options.filter((o): o is string => typeof o === 'string' && KEY.test(o)).slice(0, 16) : [];
    return options.length ? { ...base, type: 'enum', options, default: pick(options, raw.default, options[0]) } : null;
  }
  if (raw.type === 'text') {
    return { ...base, type: 'text', max: Math.min(80, finite(raw.max) ?? 40), default: '' };
  }
  return null;
}

function parseSettings(value: unknown, schema: readonly SettingSpec[]): Record<string, SettingValue> {
  const raw = asRecord(value);
  const result: Record<string, SettingValue> = {};
  for (const spec of schema) {
    const v = raw[spec.key];
    if (spec.type === 'bool') {
      result[spec.key] = typeof v === 'boolean' ? v : spec.default;
    } else if (spec.type === 'int') {
      result[spec.key] = typeof v === 'number' && Number.isFinite(v) ? Math.min(spec.max, Math.max(spec.min, Math.round(v))) : spec.default;
    } else if (spec.type === 'enum') {
      result[spec.key] = pick(spec.options, v, spec.default);
    } else {
      result[spec.key] = asString(v, spec.max) ?? '';
    }
  }
  return result;
}

function parseDevice(value: unknown, schema: readonly SettingSpec[]): BluetoothDevice | null {
  const d = asRecord(value);
  const mac = macOrNull(d.mac);
  if (!mac) {
    return null;
  }
  const battery = finite(d.battery);
  const rssi = finite(d.rssi);
  return {
    mac,
    name: asString(d.name, 80) ?? mac,
    kind: pick(DEVICE_KINDS, d.kind, 'other'),
    capabilities: capList(d.capabilities),
    paired: d.paired === true,
    trusted: d.trusted === true,
    blocked: d.blocked === true,
    connected: d.connected === true,
    battery: battery !== null && battery >= 0 && battery <= 100 ? Math.round(battery) : null,
    rssi: rssi !== null && rssi < 0 && rssi > -130 ? Math.round(rssi) : null,
    settings: parseSettings(d.settings, schema),
  };
}

export function parseState(value: unknown): BluetoothState {
  const raw = asRecord(value);
  const c = asRecord(raw.controller);
  const prefs = asRecord(raw.prefs);
  const routing = asRecord(raw.routing);
  const schema = (Array.isArray(raw.schema) ? raw.schema : []).map(parseSpec).filter((s): s is SettingSpec => s !== null);
  const devices = (Array.isArray(raw.devices) ? raw.devices : [])
    .slice(0, MAX_DEVICES)
    .map((d) => parseDevice(d, schema))
    .filter((d): d is BluetoothDevice => d !== null);
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
    devices,
    schema,
    outputOrder: macList(prefs.output_order),
    inputOrder: macList(prefs.input_order),
    globals: {
      auto_switch: prefs.auto_switch !== false,
      auto_connect: prefs.auto_connect !== false,
      announce: prefs.announce !== false,
    },
    activeOutput: macOrNull(routing.output),
    activeInput: macOrNull(routing.input),
    notice: typeof raw.notice === 'string' && KEY.test(raw.notice) ? raw.notice : null,
  };
}
