import React from 'react';
import { Panel } from '../../shared/components/ModuleFrame';
import { BluetoothHandle } from '../hooks/useBluetooth';
import { BluetoothState, GLOBAL_PREFS, updatePrefs } from '../data/bluetoothApi';
import { useBluetoothI18n } from '../scope';

export const PreferencesPanel: React.FC<{ readonly state: BluetoothState; readonly handle: BluetoothHandle }> = ({ state, handle }) => {
  const { t } = useBluetoothI18n();
  return (
    <Panel title={t('prefs_title')}>
      <div className="flex flex-col gap-2">
        {GLOBAL_PREFS.map((key) => (
          <label
            key={key}
            className="flex cursor-pointer items-start justify-between gap-3 rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2.5"
          >
            <span className="min-w-0">
              <span className="block text-sm text-slate-100">{t(`pref_${key}`)}</span>
              <span className="block text-[11px] text-slate-500">{t(`pref_${key}_hint`)}</span>
            </span>
            <input
              type="checkbox"
              role="switch"
              disabled={handle.busy !== null}
              checked={state.globals[key]}
              onChange={(event) =>
                void handle.run(`pref:${key}`, () => updatePrefs({ [key]: event.target.checked }), 'node_bluetooth_prefs_failed')
              }
              className="mt-0.5 h-5 w-9 shrink-0 accent-cyan-400"
            />
          </label>
        ))}
      </div>
    </Panel>
  );
};
