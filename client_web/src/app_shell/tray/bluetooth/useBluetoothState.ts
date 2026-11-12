import { useBluetooth } from '../../../shared/bluetooth/useBluetooth';

export function useBluetoothState() {
  const handle = useBluetooth();
  const controller = handle.state?.controller ?? null;
  return {
    handle,
    isAvailable: Boolean(handle.state?.enabled && controller?.present && controller.installed),
    isPowered: Boolean(controller?.powered),
  };
}
