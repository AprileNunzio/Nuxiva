import React from 'react';
import { Loader2, Power, Radar } from 'lucide-react';
import { Notice, Panel } from '../../shared/components/ModuleFrame';
import { BluetoothHandle } from '../hooks/useBluetooth';
import { BluetoothState, setPower, startScan } from '../data/bluetoothApi';
import { useBluetoothI18n } from '../scope';

export const ControllerPanel: React.FC<{ readonly state: BluetoothState; readonly handle: BluetoothHandle }> = ({ state, handle }) => {
  const { t } = useBluetoothI18n();
  const { controller } = state;
  const ready = controller.present && controller.installed;
  const scanning = state.scanning || controller.discovering;

  const status = !state.enabled
    ? 'status_disabled'
    : !controller.present
      ? 'status_absent'
      : !controller.installed
        ? 'status_preparing'
        : controller.powered
          ? 'status_on'
          : 'status_off';

  return (
    <Panel
      title={t('controller_title')}
      action={
        ready && (
          <button
            type="button"
            role="switch"
            aria-checked={controller.powered}
            aria-label={t('power')}
            disabled={handle.busy !== null}
            onClick={() => void handle.run('power', () => setPower(!controller.powered), 'node_bluetooth_power_failed')}
            className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-semibold transition disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
              controller.powered ? 'border-emerald-400/50 bg-emerald-400/10 text-emerald-200' : 'border-slate-700 text-slate-300'
            }`}
          >
            {handle.busy === 'power' ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Power className="h-3.5 w-3.5" aria-hidden="true" />}
            {t(controller.powered ? 'power_on' : 'power_off')}
          </button>
        )
      }
    >
      <div className="flex items-center gap-4">
        <span className="relative flex h-14 w-14 shrink-0 items-center justify-center">
          {scanning && <span className="absolute inset-0 animate-ping rounded-full border border-cyan-400/50" aria-hidden="true" />}
          <span
            className={`relative flex h-14 w-14 items-center justify-center rounded-full border ${
              controller.powered ? 'border-cyan-400/60 bg-cyan-400/10 shadow-[0_0_24px_rgba(34,211,238,0.25)]' : 'border-slate-700 bg-slate-900'
            }`}
          >
            <Radar className={`h-6 w-6 ${controller.powered ? 'text-cyan-200' : 'text-slate-500'}`} aria-hidden="true" />
          </span>
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-100">{controller.name ?? t('controller_unnamed')}</p>
          {controller.address && <p className="font-mono text-[11px] text-slate-500">{controller.address}</p>}
          <p className="mt-0.5 text-xs text-slate-400">{t(status)}</p>
        </div>
      </div>
      {!state.enabled && <div className="mt-3"><Notice tone="warn">{t('notice_disabled')}</Notice></div>}
      {state.enabled && !controller.present && <div className="mt-3"><Notice tone="info">{t('notice_absent')}</Notice></div>}
      {ready && (
        <button
          type="button"
          disabled={scanning || handle.busy !== null}
          onClick={() => void handle.run('scan', async () => void (await startScan()), 'node_bluetooth_scan_failed')}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-4 py-2.5 text-sm font-bold text-slate-950 transition hover:brightness-110 disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200"
        >
          {scanning ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Radar className="h-4 w-4" aria-hidden="true" />}
          {t(scanning ? 'scanning' : 'scan')}
        </button>
      )}
    </Panel>
  );
};
