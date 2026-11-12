import React, { useState } from 'react';
import { BatteryMedium, ChevronDown, Link2, Link2Off, Loader2, Mic, Plus, ShieldCheck, ShieldOff, Signal, Trash2, Volume2 } from 'lucide-react';
import { ConfirmDialog } from '../../../shared/ui/ConfirmDialog';
import { BluetoothDevice, DeviceAction, displayName } from '../../../shared/bluetooth/model';
import { kindIcon } from '../../../shared/bluetooth/kinds';
import { BluetoothHandle, actionKey } from '../../../shared/bluetooth/useBluetooth';
import { buttonClass, tones, useBluetoothI18n } from '../scope';
import { DeviceSettings } from './DeviceSettings';

interface DeviceRowProps {
  readonly device: BluetoothDevice;
  readonly handle: BluetoothHandle;
  readonly open: boolean;
  readonly onToggle: () => void;
}

const ACTION_ICONS: Readonly<Record<DeviceAction, React.ReactNode>> = {
  pair: <Plus className="h-3.5 w-3.5" aria-hidden="true" />,
  connect: <Link2 className="h-3.5 w-3.5" aria-hidden="true" />,
  disconnect: <Link2Off className="h-3.5 w-3.5" aria-hidden="true" />,
  forget: <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />,
  trust: <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />,
  untrust: <ShieldOff className="h-3.5 w-3.5" aria-hidden="true" />,
};

const batteryTone = (value: number) => (value > 30 ? 'bg-emerald-500' : value > 15 ? 'bg-amber-500' : 'bg-rose-500');

export const DeviceRow: React.FC<DeviceRowProps> = ({ device, handle, open, onToggle }) => {
  const { t } = useBluetoothI18n();
  const [confirmForget, setConfirmForget] = useState(false);
  const Icon = kindIcon(device.kind);
  const name = displayName(device);
  const state = handle.state;
  const busy = (action: DeviceAction) => handle.busy === actionKey(action, device.mac);

  const button = (action: DeviceAction, tone: keyof typeof tones) => (
    <button type="button" disabled={handle.busy !== null} onClick={() => void handle.act(device, action)} className={`${buttonClass} ${tones[tone]}`}>
      {busy(action) ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : ACTION_ICONS[action]}
      {t(`action_${action}`)}
    </button>
  );

  return (
    <li className={`rounded-2xl border p-3 transition ${device.connected ? 'border-blue-200 bg-blue-50/40' : 'border-slate-200 bg-white'}`}>
      <div className="flex items-start gap-3">
        <span
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${
            device.connected ? 'border-blue-200 bg-white text-blue-600' : 'border-slate-200 bg-slate-50 text-slate-500'
          }`}
        >
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-900">{name}</p>
          <p className="truncate text-[11px] text-slate-500">
            {t(`kind_${device.kind}`)}
            {name !== device.name && <> · {device.name}</>} · <span className="font-mono">{device.mac}</span>
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                device.connected
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                  : device.paired
                    ? 'border-slate-200 bg-slate-50 text-slate-600'
                    : 'border-amber-200 bg-amber-50 text-amber-700'
              }`}
            >
              {t(device.connected ? 'state_connected' : device.paired ? 'state_paired' : 'state_nearby')}
            </span>
            {device.trusted && (
              <span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-600">{t('state_trusted')}</span>
            )}
            {state?.activeOutput === device.mac && (
              <span className="flex items-center gap-1 rounded-full border border-blue-200 bg-white px-2 py-0.5 text-[10px] font-semibold text-blue-700">
                <Volume2 className="h-3 w-3" aria-hidden="true" />
                {t('active_output')}
              </span>
            )}
            {state?.activeInput === device.mac && (
              <span className="flex items-center gap-1 rounded-full border border-indigo-200 bg-white px-2 py-0.5 text-[10px] font-semibold text-indigo-700">
                <Mic className="h-3 w-3" aria-hidden="true" />
                {t('active_input')}
              </span>
            )}
            {!device.paired && device.rssi !== null && (
              <span className="flex items-center gap-1 text-[10px] text-slate-500" aria-label={t('signal', { value: device.rssi })}>
                <Signal className="h-3 w-3" aria-hidden="true" />
                {t('signal_value', { value: device.rssi })}
              </span>
            )}
          </div>
        </div>
        {device.battery !== null && (
          <span className="flex shrink-0 flex-col items-end gap-1" aria-label={t('battery', { value: device.battery })}>
            <span className="flex items-center gap-1 font-mono text-[11px] text-slate-700">
              <BatteryMedium className="h-3.5 w-3.5" aria-hidden="true" />
              {t('battery_value', { value: device.battery })}
            </span>
            <span className="h-1 w-12 overflow-hidden rounded-full bg-slate-200">
              <span className={`block h-full rounded-full ${batteryTone(device.battery)}`} style={{ width: `${device.battery}%` }} />
            </span>
          </span>
        )}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {!device.paired && button('pair', 'primary')}
        {device.paired && !device.connected && button('connect', 'positive')}
        {device.connected && button('disconnect', 'neutral')}
        {device.paired && button(device.trusted ? 'untrust' : 'trust', 'neutral')}
        {device.paired && (
          <button type="button" aria-expanded={open} onClick={onToggle} className={`${buttonClass} ${tones.neutral}`}>
            <ChevronDown className={`h-3.5 w-3.5 transition ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
            {t(open ? 'settings_close' : 'settings_open')}
          </button>
        )}
        {device.paired && (
          <button
            type="button"
            aria-label={t('action_forget')}
            title={t('action_forget')}
            disabled={handle.busy !== null}
            onClick={() => setConfirmForget(true)}
            className={`${buttonClass} ${tones.danger} ml-auto`}
          >
            {ACTION_ICONS.forget}
          </button>
        )}
      </div>
      {!device.paired && <p className="mt-2 text-[11px] text-slate-500">{t('pair_hint')}</p>}
      {open && device.paired && <DeviceSettings device={device} handle={handle} />}
      {confirmForget && (
        <ConfirmDialog
          title={t('forget_title')}
          body={t('forget_body', { name })}
          confirmLabel={t('action_forget')}
          cancelLabel={t('cancel')}
          pending={busy('forget')}
          tone="danger"
          onConfirm={() => void handle.act(device, 'forget').then(() => setConfirmForget(false))}
          onCancel={() => setConfirmForget(false)}
        />
      )}
    </li>
  );
};
