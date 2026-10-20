import React, { useState } from 'react';
import { BatteryMedium, ChevronDown, Link2, Link2Off, Loader2, Mic, Plus, Trash2, Volume2 } from 'lucide-react';
import { ConfirmDialog } from '../../../shared/ui/ConfirmDialog';
import { BluetoothHandle } from '../hooks/useBluetooth';
import { BluetoothDevice, DeviceAction, runAction } from '../data/bluetoothApi';
import { iconFor, kindKey, useBluetoothI18n } from '../scope';
import { DeviceSettingsForm } from './DeviceSettingsForm';

interface DeviceCardProps {
  readonly device: BluetoothDevice;
  readonly handle: BluetoothHandle;
  readonly activeOutput: boolean;
  readonly activeInput: boolean;
}

const actionClass =
  'flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-semibold transition disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400';

export const DeviceCard: React.FC<DeviceCardProps> = ({ device, handle, activeOutput, activeInput }) => {
  const { t } = useBluetoothI18n();
  const [open, setOpen] = useState(false);
  const [confirmForget, setConfirmForget] = useState(false);
  const Icon = iconFor(device.icon);
  const audio = device.audioOut || device.audioIn;
  const key = (action: DeviceAction) => `${action}:${device.mac}`;
  const act = (action: DeviceAction) => handle.run(key(action), () => runAction(device.mac, action), `node_bluetooth_${action}_failed`);

  const button = (action: DeviceAction, icon: React.ReactNode, tone: string) => (
    <button type="button" disabled={handle.busy !== null} onClick={() => void act(action)} className={`${actionClass} ${tone}`}>
      {handle.busy === key(action) ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : icon}
      {t(`action_${action}`)}
    </button>
  );

  return (
    <li
      className={`rounded-2xl border p-3 transition ${
        device.connected ? 'border-cyan-400/50 bg-cyan-400/[0.04] shadow-[0_0_18px_rgba(34,211,238,0.08)]' : 'border-slate-800/80 bg-slate-950/40'
      }`}
    >
      <div className="flex items-start gap-3">
        <span
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${
            device.connected ? 'border-cyan-400/50 bg-cyan-400/10' : 'border-slate-700 bg-slate-900'
          }`}
        >
          <Icon className={`h-5 w-5 ${device.connected ? 'text-cyan-200' : 'text-slate-400'}`} aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-100">{device.name}</p>
          <p className="truncate text-[11px] text-slate-500">
            {t(kindKey(device.icon))} · <span className="font-mono">{device.mac}</span>
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${
                device.connected ? 'border-emerald-400/40 text-emerald-300' : device.paired ? 'border-slate-600 text-slate-400' : 'border-amber-400/40 text-amber-200'
              }`}
            >
              {t(device.connected ? 'state_connected' : device.paired ? 'state_paired' : 'state_nearby')}
            </span>
            {activeOutput && (
              <span className="flex items-center gap-1 rounded-full border border-cyan-400/40 px-2 py-0.5 text-[10px] font-semibold text-cyan-200">
                <Volume2 className="h-3 w-3" aria-hidden="true" />
                {t('active_output')}
              </span>
            )}
            {activeInput && (
              <span className="flex items-center gap-1 rounded-full border border-indigo-400/40 px-2 py-0.5 text-[10px] font-semibold text-indigo-200">
                <Mic className="h-3 w-3" aria-hidden="true" />
                {t('active_input')}
              </span>
            )}
          </div>
        </div>
        {device.battery !== null && (
          <span className="flex shrink-0 flex-col items-end gap-1" aria-label={t('battery', { value: device.battery })}>
            <span className="flex items-center gap-1 font-mono text-[11px] text-slate-300">
              <BatteryMedium className="h-3.5 w-3.5" aria-hidden="true" />
              {device.battery}%
            </span>
            <span className="h-1 w-12 overflow-hidden rounded-full bg-slate-800">
              <span
                className={`block h-full rounded-full ${device.battery > 30 ? 'bg-emerald-400' : device.battery > 15 ? 'bg-amber-400' : 'bg-rose-500'}`}
                style={{ width: `${device.battery}%` }}
              />
            </span>
          </span>
        )}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {!device.paired && button('pair', <Plus className="h-3.5 w-3.5" aria-hidden="true" />, 'border-cyan-400/50 bg-cyan-400/10 text-cyan-100 hover:bg-cyan-400/20')}
        {device.paired && !device.connected && button('connect', <Link2 className="h-3.5 w-3.5" aria-hidden="true" />, 'border-emerald-400/40 text-emerald-200 hover:bg-emerald-400/10')}
        {device.connected && button('disconnect', <Link2Off className="h-3.5 w-3.5" aria-hidden="true" />, 'border-slate-700 text-slate-200 hover:border-slate-500')}
        {device.paired && audio && (
          <button
            type="button"
            aria-expanded={open}
            onClick={() => setOpen(!open)}
            className={`${actionClass} border-slate-700 text-slate-300 hover:border-cyan-400/50`}
          >
            <ChevronDown className={`h-3.5 w-3.5 transition ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
            {t('audio_settings')}
          </button>
        )}
        {device.paired && (
          <button
            type="button"
            aria-label={t('action_forget')}
            disabled={handle.busy !== null}
            onClick={() => setConfirmForget(true)}
            className="ml-auto rounded-lg p-1.5 text-slate-500 transition hover:text-rose-300 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-300"
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        )}
      </div>
      {open && device.paired && audio && <DeviceSettingsForm device={device} handle={handle} />}
      {confirmForget && (
        <ConfirmDialog
          title={t('forget_title')}
          body={t('forget_body', { name: device.name })}
          confirmLabel={t('action_forget')}
          cancelLabel={t('cancel')}
          pending={handle.busy === key('forget')}
          tone="danger"
          onConfirm={() => void act('forget').then(() => setConfirmForget(false))}
          onCancel={() => setConfirmForget(false)}
        />
      )}
    </li>
  );
};
