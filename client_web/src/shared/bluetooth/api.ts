import { asRecord, requestJson } from '../../node_apps/shared/data/http';
import { AudioSide, BluetoothState, DeviceAction, GlobalPref, MAC, SettingValue } from './model';
import { parseState } from './parse';

const BASE = '/api/bluetooth';

const deviceUrl = (mac: string, suffix: string): string => {
  if (!MAC.test(mac)) {
    throw new Error('invalid_mac');
  }
  return `${BASE}/devices/${encodeURIComponent(mac)}/${suffix}`;
};

export async function fetchBluetooth(signal?: AbortSignal): Promise<BluetoothState> {
  return parseState(await requestJson<unknown>(BASE, { signal }));
}

export async function startScan(): Promise<number> {
  const raw = asRecord(await requestJson<unknown>(`${BASE}/scan`, { method: 'POST' }));
  return typeof raw.seconds === 'number' && raw.seconds > 0 ? Math.min(raw.seconds, 60) : 20;
}

export async function setPower(on: boolean): Promise<BluetoothState> {
  return parseState(await requestJson<unknown>(`${BASE}/power`, { method: 'POST', body: JSON.stringify({ on }) }));
}

export async function runAction(mac: string, action: DeviceAction): Promise<BluetoothState> {
  return parseState(await requestJson<unknown>(deviceUrl(mac, action), { method: 'POST' }));
}

export async function updateDeviceSettings(mac: string, changes: Readonly<Record<string, SettingValue>>): Promise<BluetoothState> {
  return parseState(await requestJson<unknown>(deviceUrl(mac, 'settings'), { method: 'PUT', body: JSON.stringify(changes) }));
}

export async function updateGlobal(key: GlobalPref, value: boolean): Promise<BluetoothState> {
  return parseState(await requestJson<unknown>(`${BASE}/prefs`, { method: 'PUT', body: JSON.stringify({ [key]: value }) }));
}

export async function updateOrder(side: AudioSide, macs: readonly string[]): Promise<BluetoothState> {
  const body = side === 'output' ? { output_order: macs } : { input_order: macs };
  return parseState(await requestJson<unknown>(`${BASE}/prefs`, { method: 'PUT', body: JSON.stringify(body) }));
}
