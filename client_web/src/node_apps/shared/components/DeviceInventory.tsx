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
      <p className="text-sm text-slate-500">{emptyLabel}</p>
    ) : (
      <ul className="flex flex-col gap-1.5">
        {devices.map((device) => (
          <li key={device} className="flex items-center gap-2 rounded-lg border border-slate-800/80 bg-slate-950/40 px-3 py-2 text-sm text-slate-200">
            <CircleDot className="h-3.5 w-3.5 shrink-0 text-emerald-300" aria-hidden="true" />
            <span className="truncate">{device}</span>
          </li>
        ))}
      </ul>
    )}
  </Panel>
);
