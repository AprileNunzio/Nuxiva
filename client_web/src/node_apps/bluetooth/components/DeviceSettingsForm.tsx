import React from 'react';
import { BluetoothHandle } from '../hooks/useBluetooth';
import { BluetoothDevice, DeviceSettings, PROFILES, ROLES, updatePrefs } from '../data/bluetoothApi';
import { fieldClass, useBluetoothI18n } from '../scope';

export const DeviceSettingsForm: React.FC<{ readonly device: BluetoothDevice; readonly handle: BluetoothHandle }> = ({ device, handle }) => {
  const { t } = useBluetoothI18n();
  const save = (change: Partial<DeviceSettings>) =>
    void handle.run(`settings:${device.mac}`, () => updatePrefs({ devices: { [device.mac]: change } }), 'node_bluetooth_prefs_failed');
  const busy = handle.busy !== null;

  return (
    <div className="mt-3 grid gap-2 border-t border-slate-800/80 pt-3 sm:grid-cols-2">
      <label className="flex flex-col gap-1 text-xs text-slate-400">
        {t('setting_role')}
        <select
          value={device.settings.role}
          disabled={busy}
          onChange={(event) => save({ role: ROLES.find((r) => r === event.target.value) ?? 'auto' })}
          className={fieldClass}
        >
          {ROLES.map((role) => (
            <option key={role} value={role}>
              {t(`role_${role}`)}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs text-slate-400">
        {t('setting_profile')}
        <select
          value={device.settings.profile}
          disabled={busy}
          onChange={(event) => save({ profile: PROFILES.find((p) => p === event.target.value) ?? 'auto' })}
          className={fieldClass}
        >
          {PROFILES.map((profile) => (
            <option key={profile} value={profile}>
              {t(`profile_${profile}`)}
            </option>
          ))}
        </select>
      </label>
      <label className="flex cursor-pointer items-center justify-between gap-3 rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2 text-sm text-slate-100 sm:col-span-2">
        {t('setting_autoconnect')}
        <input
          type="checkbox"
          role="switch"
          disabled={busy}
          checked={device.settings.autoconnect}
          onChange={(event) => save({ autoconnect: event.target.checked })}
          className="h-5 w-9 accent-cyan-400"
        />
      </label>
    </div>
  );
};
