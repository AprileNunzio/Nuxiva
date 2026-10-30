export type { BluetoothDevice, BluetoothState, Controller as BluetoothController, DeviceKind } from '../../../shared/bluetooth/model';

export interface OpenAppRequest {
  readonly appId: string;
  readonly targetNodeId?: string;
  readonly initialPayload?: Readonly<Record<string, string>>;
}
