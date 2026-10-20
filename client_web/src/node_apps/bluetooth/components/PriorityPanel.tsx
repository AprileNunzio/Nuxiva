import React from 'react';
import { ArrowDown, ArrowUp } from 'lucide-react';
import { Panel } from '../../shared/components/ModuleFrame';
import { BluetoothHandle } from '../hooks/useBluetooth';
import { BluetoothDevice, BluetoothState, updatePrefs } from '../data/bluetoothApi';
import { useBluetoothI18n } from '../scope';

type Side = 'output' | 'input';

function ordered(order: readonly string[], devices: readonly BluetoothDevice[], side: Side): BluetoothDevice[] {
  const eligible = devices.filter((d) => d.paired && (side === 'output' ? d.audioOut : d.audioIn));
  const rank = (mac: string) => {
    const index = order.indexOf(mac);
    return index < 0 ? Number.MAX_SAFE_INTEGER : index;
  };
  return [...eligible].sort((a, b) => rank(a.mac) - rank(b.mac));
}

const moveClass =
  'rounded-md p-1 text-slate-400 transition hover:bg-slate-800 hover:text-cyan-200 disabled:opacity-30 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400';

export const PriorityPanel: React.FC<{ readonly state: BluetoothState; readonly handle: BluetoothHandle }> = ({ state, handle }) => {
  const { t } = useBluetoothI18n();

  const column = (side: Side) => {
    const list = ordered(side === 'output' ? state.outputOrder : state.inputOrder, state.devices, side);
    const move = (index: number, delta: number) => {
      const next = list.map((d) => d.mac);
      const [item] = next.splice(index, 1);
      next.splice(index + delta, 0, item);
      void handle.run(`order:${side}`, () => updatePrefs(side === 'output' ? { output_order: next } : { input_order: next }), 'node_bluetooth_prefs_failed');
    };
    return (
      <div key={side} className="min-w-0">
        <p className="mb-2 text-xs font-semibold text-slate-300">{t(`priority_${side}`)}</p>
        {list.length === 0 ? (
          <p className="text-xs text-slate-500">{t('priority_empty')}</p>
        ) : (
          <ol className="flex flex-col gap-1.5">
            {list.map((device, index) => (
              <li key={device.mac} className="flex items-center gap-2 rounded-lg border border-slate-800/80 bg-slate-950/40 px-2.5 py-1.5">
                <span className="w-4 shrink-0 font-mono text-[11px] text-cyan-300">{index + 1}</span>
                <span className="min-w-0 flex-1 truncate text-sm text-slate-200">{device.name}</span>
                <button type="button" aria-label={t('move_up')} disabled={index === 0 || handle.busy !== null} onClick={() => move(index, -1)} className={moveClass}>
                  <ArrowUp className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  aria-label={t('move_down')}
                  disabled={index === list.length - 1 || handle.busy !== null}
                  onClick={() => move(index, 1)}
                  className={moveClass}
                >
                  <ArrowDown className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </li>
            ))}
          </ol>
        )}
      </div>
    );
  };

  return (
    <Panel title={t('priority_title')}>
      <p className="mb-3 text-xs text-slate-500">{t('priority_hint')}</p>
      <div className="grid gap-4 sm:grid-cols-2">{(['output', 'input'] as const).map(column)}</div>
    </Panel>
  );
};
