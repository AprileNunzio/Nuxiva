import React from 'react';
import { CircleDot } from 'lucide-react';
import { Panel } from './ModuleFrame';

interface DeviceInventoryProps {
  readonly title: string;
  readonly devices: readonly string[];
  readonly emptyLabel: string;
}

export const DeviceInventory: React.FC<DeviceInventoryProps> = ({ title, devices, emptyLabel }) => (
  <Panel title={title}>
    {devices.length === 0 ? (
      <p className="text-sm text-on-surface-variant">{emptyLabel}</p>
    ) : (
      <ul className="flex flex-col gap-1.5">
        {devices.map((device) => (
          <li key={device} className="flex items-center gap-2 rounded-lg bg-surface-container px-3 py-2 text-sm text-on-surface">
            <CircleDot className="h-3.5 w-3.5 shrink-0 text-success" aria-hidden="true" />
            <span className="truncate">{device}</span>
          </li>
        ))}
      </ul>
    )}
  </Panel>
);
