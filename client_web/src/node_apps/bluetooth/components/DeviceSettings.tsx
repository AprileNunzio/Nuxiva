import React from 'react';
import { Gamepad2, Keyboard, Mic, Mouse, Settings2, Volume2, LucideIcon } from 'lucide-react';
import { BluetoothDevice, SETTING_GROUPS, SettingGroup, appliesTo } from '../../../shared/bluetooth/model';
import { BluetoothHandle, actionKey } from '../../../shared/bluetooth/useBluetooth';
import { useBluetoothI18n } from '../scope';
import { SettingField } from './SettingField';

const GROUP_ICONS: Readonly<Record<SettingGroup, LucideIcon>> = {
  general: Settings2,
  audio_out: Volume2,
  audio_in: Mic,
  pointer: Mouse,
  keyboard: Keyboard,
  gamepad: Gamepad2,
};

export const DeviceSettings: React.FC<{ readonly device: BluetoothDevice; readonly handle: BluetoothHandle }> = ({ device, handle }) => {
  const { t } = useBluetoothI18n();
  const schema = handle.state?.schema ?? [];
  const groups = SETTING_GROUPS.map((group) => ({ group, specs: schema.filter((s) => s.group === group && appliesTo(s, device)) })).filter(
    (entry) => entry.specs.length > 0,
  );

  return (
    <div className="mt-3 flex flex-col gap-4 border-t border-slate-100 pt-3">
      {groups.map(({ group, specs }) => {
        const Icon = GROUP_ICONS[group];
        return (
          <section key={group} aria-labelledby={`bt-${device.mac}-${group}`} className="flex flex-col gap-2">
            <header className="flex items-start gap-2">
              <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-blue-100 bg-blue-50 text-blue-600">
                <Icon className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
              <span className="min-w-0">
                <h4 id={`bt-${device.mac}-${group}`} className="text-sm font-semibold text-slate-900">
                  {t(`group_${group}`)}
                </h4>
                <p className="text-[11px] leading-relaxed text-slate-500">{t(`group_${group}_hint`)}</p>
              </span>
            </header>
            <div className="grid gap-2 md:grid-cols-2">
              {specs.map((spec) => (
                <SettingField
                  key={spec.key}
                  spec={spec}
                  value={device.settings[spec.key] ?? spec.default}
                  disabled={handle.busy === actionKey(`setting_${spec.key}`, device.mac)}
                  onCommit={(value) => void handle.configure(device, spec.key, value)}
                />
              ))}
            </div>
          </section>
        );
      })}
      <p className="text-[11px] text-slate-500">{t('settings_live')}</p>
    </div>
  );
};
