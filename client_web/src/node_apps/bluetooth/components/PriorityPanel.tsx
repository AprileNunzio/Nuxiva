import React from 'react';
import { ArrowDown, ArrowUp } from 'lucide-react';
import { Panel } from '../../shared/components/ModuleFrame';
import { AUDIO_SIDES, AudioSide, BluetoothDevice, BluetoothState, displayName } from '../../../shared/bluetooth/model';
import { BluetoothHandle } from '../../../shared/bluetooth/useBluetooth';
import { useBluetoothI18n } from '../scope';

function ordered(state: BluetoothState, side: AudioSide): BluetoothDevice[] {
  const cap = side === 'output' ? 'audio_out' : 'audio_in';
  const order = side === 'output' ? state.outputOrder : state.inputOrder;
  const rank = (mac: string) => {
    const index = order.indexOf(mac);
    return index < 0 ? Number.MAX_SAFE_INTEGER : index;
  };
  return state.devices.filter((d) => d.paired && d.capabilities.includes(cap)).sort((a, b) => rank(a.mac) - rank(b.mac));
}

const moveClass =
  'rounded-md p-1 text-slate-500 transition hover:bg-slate-100 hover:text-blue-600 disabled:opacity-30 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500';

export const PriorityPanel: React.FC<{ readonly handle: BluetoothHandle }> = ({ handle }) => {
  const { t } = useBluetoothI18n();
  const state = handle.state;
  if (!state) return null;

  const column = (side: AudioSide) => {
    const list = ordered(state, side);
    const move = (index: number, delta: number) => {
      const next = list.map((d) => d.mac);
      const [item] = next.splice(index, 1);
      next.splice(index + delta, 0, item);
      void handle.reorder(side, next);
    };
    return (
      <div key={side} className="min-w-0">
        <p className="mb-2 text-xs font-semibold text-slate-700">{t(`priority_${side}`)}</p>
        {list.length === 0 ? (
          <p className="text-xs text-slate-500">{t('priority_empty')}</p>
        ) : (
          <ol className="flex flex-col gap-1.5">
            {list.map((device, index) => (
              <li key={device.mac} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5">
                <span className="w-4 shrink-0 font-mono text-[11px] font-semibold text-blue-600">{index + 1}</span>
                <span className="min-w-0 flex-1 truncate text-sm text-slate-800">{displayName(device)}</span>
                <button type="button" aria-label={t('move_up')} disabled={index === 0} onClick={() => move(index, -1)} className={moveClass}>
                  <ArrowUp className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
                <button type="button" aria-label={t('move_down')} disabled={index === list.length - 1} onClick={() => move(index, 1)} className={moveClass}>
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
      <div className="grid gap-4 sm:grid-cols-2">{AUDIO_SIDES.map(column)}</div>
    </Panel>
  );
};
