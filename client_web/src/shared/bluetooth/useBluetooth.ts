import { useCallback, useSyncExternalStore } from 'react';
import { runAction, setPower, startScan, updateDeviceSettings, updateGlobal, updateOrder } from './api';
import { AudioSide, BluetoothDevice, DeviceAction, GlobalPref, SettingValue, isReady } from './model';
import { BluetoothSnapshot, bluetoothStore } from './store';

export interface BluetoothHandle extends BluetoothSnapshot {
  readonly ready: boolean;
  readonly scanning: boolean;
  readonly refresh: () => void;
  readonly power: (on: boolean) => Promise<boolean>;
  readonly scan: () => Promise<boolean>;
  readonly act: (device: BluetoothDevice, action: DeviceAction) => Promise<boolean>;
  readonly configure: (device: BluetoothDevice, key: string, value: SettingValue) => Promise<boolean>;
  readonly setGlobal: (key: GlobalPref, value: boolean) => Promise<boolean>;
  readonly reorder: (side: AudioSide, macs: readonly string[]) => Promise<boolean>;
}

export const actionKey = (action: string, mac = ''): string => (mac ? `${action}:${mac}` : action);

export function useBluetooth(): BluetoothHandle {
  const snap = useSyncExternalStore(bluetoothStore.subscribe, bluetoothStore.getSnapshot, bluetoothStore.getSnapshot);
  const power = useCallback((on: boolean) => bluetoothStore.run('power', () => setPower(on), 'node_bluetooth_power_failed'), []);
  const scan = useCallback(
    () =>
      bluetoothStore.run(
        'scan',
        async () => {
          bluetoothStore.markScanning(await startScan());
        },
        'node_bluetooth_scan_failed',
      ),
    [],
  );
  const act = useCallback(
    (device: BluetoothDevice, action: DeviceAction) =>
      bluetoothStore.run(actionKey(action, device.mac), () => runAction(device.mac, action), `node_bluetooth_${action}_failed`),
    [],
  );
  const configure = useCallback(
    (device: BluetoothDevice, key: string, value: SettingValue) =>
      bluetoothStore.run(actionKey(`setting_${key}`, device.mac), () => updateDeviceSettings(device.mac, { [key]: value }), 'node_bluetooth_prefs_failed'),
    [],
  );
  const setGlobal = useCallback(
    (key: GlobalPref, value: boolean) => bluetoothStore.run(actionKey(`pref_${key}`), () => updateGlobal(key, value), 'node_bluetooth_prefs_failed'),
    [],
  );
  const reorder = useCallback(
    (side: AudioSide, macs: readonly string[]) => bluetoothStore.run(actionKey(`order_${side}`), () => updateOrder(side, macs), 'node_bluetooth_prefs_failed'),
    [],
  );
  const scanning = snap.scanRequestedUntil > Date.now() || snap.state?.scanning === true || snap.state?.controller.discovering === true;
  return { ...snap, ready: isReady(snap.state), scanning, refresh: bluetoothStore.refresh, power, scan, act, configure, setGlobal, reorder };
}
