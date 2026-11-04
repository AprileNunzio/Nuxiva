import React from 'react';
import { Panel } from '../../shared/components/ModuleFrame';
import { GLOBAL_PREFS } from '../../../shared/bluetooth/model';
import { BluetoothHandle, actionKey } from '../../../shared/bluetooth/useBluetooth';
import { useBluetoothI18n } from '../scope';
import { Switch } from './Switch';

export const BehaviorPanel: React.FC<{ readonly handle: BluetoothHandle }> = ({ handle }) => {
  const { t } = useBluetoothI18n();
  const globals = handle.state?.globals;
  if (!globals) return null;
  return (
    <Panel title={t('prefs_title')}>
      <div className="flex flex-col gap-2">
        {GLOBAL_PREFS.map((key) => (
          <div key={key} className="flex items-start justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5">
            <span className="min-w-0">
              <span className="block text-sm font-medium text-slate-900">{t(`pref_${key}`)}</span>
              <span className="block text-[11px] leading-relaxed text-slate-500">{t(`pref_${key}_hint`)}</span>
            </span>
            <Switch
              checked={globals[key]}
              disabled={handle.busy === actionKey(`pref_${key}`)}
              label={t(`pref_${key}`)}
              onChange={(next) => void handle.setGlobal(key, next)}
            />
          </div>
        ))}
      </div>
    </Panel>
  );
};
