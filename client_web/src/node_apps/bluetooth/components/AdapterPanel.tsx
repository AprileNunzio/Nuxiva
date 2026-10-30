import React from 'react';
import { Loader2, Radar } from 'lucide-react';
import { Notice, Panel } from '../../shared/components/ModuleFrame';
import { BluetoothHandle } from '../../../shared/bluetooth/useBluetooth';
import { BluetoothState } from '../../../shared/bluetooth/model';
import { useBluetoothI18n } from '../scope';
import { Switch } from './Switch';

function statusKey(state: BluetoothState): string {
  if (!state.enabled) return 'status_disabled';
  if (!state.controller.present) return 'status_absent';
  if (!state.controller.installed) return 'status_preparing';
  return state.controller.powered ? 'status_on' : 'status_off';
}

export const AdapterPanel: React.FC<{ readonly state: BluetoothState; readonly handle: BluetoothHandle }> = ({ state, handle }) => {
  const { t } = useBluetoothI18n();
  const { controller } = state;
  const powered = controller.powered;

  return (
    <Panel
      title={t('adapter_title')}
      action={handle.ready && <Switch checked={powered} disabled={handle.busy !== null} label={t('power')} onChange={(on) => void handle.power(on)} />}
    >
      <div className="flex items-center gap-4">
        <span className="relative flex h-14 w-14 shrink-0 items-center justify-center">
          {handle.scanning && <span className="absolute inset-0 animate-ping rounded-full border border-blue-300" aria-hidden="true" />}
          <span
            className={`relative flex h-14 w-14 items-center justify-center rounded-full border ${
              powered ? 'border-blue-200 bg-blue-50 text-blue-600' : 'border-slate-200 bg-slate-50 text-slate-400'
            }`}
          >
            <Radar className="h-6 w-6" aria-hidden="true" />
          </span>
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-900">{controller.name ?? t('adapter_unnamed')}</p>
          {controller.address && <p className="font-mono text-[11px] text-slate-500">{controller.address}</p>}
          <p className="mt-0.5 text-xs text-slate-600" aria-live="polite">
            {t(statusKey(state))}
          </p>
        </div>
      </div>
      {!state.enabled && (
        <div className="mt-3">
          <Notice tone="warn">{t('notice_disabled')}</Notice>
        </div>
      )}
      {state.enabled && !controller.present && (
        <div className="mt-3">
          <Notice tone="info">{t('notice_absent')}</Notice>
        </div>
      )}
      {handle.ready && (
        <>
          <button
            type="button"
            disabled={!powered || handle.scanning || handle.busy !== null}
            onClick={() => void handle.scan()}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-xs transition hover:bg-blue-700 disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-300"
          >
            {handle.scanning ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Radar className="h-4 w-4" aria-hidden="true" />}
            {t(handle.scanning ? 'scanning' : 'scan')}
          </button>
          <p className="mt-2 text-[11px] leading-relaxed text-slate-500">{t(powered ? 'scan_hint' : 'power_hint')}</p>
        </>
      )}
    </Panel>
  );
};
