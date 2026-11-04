import React from 'react';
import { Panel } from '../../shared/components/ModuleFrame';
import { BluetoothDevice } from '../../../shared/bluetooth/model';
import { BluetoothHandle } from '../../../shared/bluetooth/useBluetooth';
import { DeviceRow } from './DeviceRow';

interface DeviceSectionProps {
  readonly title: string;
  readonly empty: string;
  readonly devices: readonly BluetoothDevice[];
  readonly handle: BluetoothHandle;
  readonly openMac: string | null;
  readonly onToggle: (mac: string) => void;
}

export const DeviceSection: React.FC<DeviceSectionProps> = ({ title, empty, devices, handle, openMac, onToggle }) => (
  <Panel title={title}>
    {devices.length === 0 ? (
      <p className="text-sm text-slate-500">{empty}</p>
    ) : (
      <ul className="flex flex-col gap-2">
        {devices.map((device) => (
          <DeviceRow key={device.mac} device={device} handle={handle} open={openMac === device.mac} onToggle={() => onToggle(device.mac)} />
        ))}
      </ul>
    )}
  </Panel>
);
