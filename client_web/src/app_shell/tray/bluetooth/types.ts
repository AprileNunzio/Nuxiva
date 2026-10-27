export interface BluetoothController {
  present: boolean;
  installed: boolean;
  powered: boolean;
  pairable?: boolean;
  discoverable?: boolean;
  discovering?: boolean;
  address?: string;
  name?: string;
}

export interface BluetoothDevice {
  mac: string;
  name: string;
  connected: boolean;
  paired: boolean;
  trusted?: boolean;
  icon?: string;
  rssi?: number;
}

export interface BluetoothPayload {
  controller: BluetoothController;
  devices: BluetoothDevice[];
  scanning?: boolean;
}
