import React from 'react';
import { Bluetooth, Loader2 } from 'lucide-react';
import { ControlScope } from '../console/data/nodeConsoleApi';
import { ModuleFrame, Notice, Panel } from '../shared/components/ModuleFrame';
import { usePairedNode } from '../shared/hooks/usePairedNode';
import { ControllerPanel } from './components/ControllerPanel';
import { DeviceCard } from './components/DeviceCard';
import { PreferencesPanel } from './components/PreferencesPanel';
import { PriorityPanel } from './components/PriorityPanel';
import { useBluetooth } from './hooks/useBluetooth';
import { useBluetoothI18n } from './scope';

interface Props {
  readonly nodeId?: string;
  readonly scope?: ControlScope;
}

export const View: React.FC<Props> = ({ nodeId = '', scope = 'mesh' }) => {
  const { t } = useBluetoothI18n();
  const local = scope === 'local';
  const handle = useBluetooth(local);
  const { node } = usePairedNode(nodeId, scope);
  const state = handle.state;
  const ready = state !== null && state.controller.present && state.controller.installed;
  const paired = state?.devices.filter((d) => d.paired) ?? [];
  const nearby = state?.devices.filter((d) => !d.paired) ?? [];

  return (
    <ModuleFrame icon={Bluetooth} title={t('title')} subtitle={t('description')} badge={t(`scope_${scope}`)}>
      {scope === 'mesh' && <Notice tone="warn">{t('notice_unpaired')}</Notice>}
      {scope === 'paired' && (
        <Notice tone="info">{t(node?.hardware?.bluetooth ? 'notice_paired_present' : 'notice_paired_absent')}</Notice>
      )}
      {local && state === null && (
        <p className="flex items-center gap-2 text-sm text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          {t('loading')}
        </p>
      )}
      {local && state && (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
          <div className="flex min-w-0 flex-col gap-4">
            <ControllerPanel state={state} handle={handle} />
            {ready && <PreferencesPanel state={state} handle={handle} />}
          </div>
          {ready && (
            <div className="flex min-w-0 flex-col gap-4">
              <Panel title={t('paired_title', { count: paired.length })}>
                {paired.length === 0 ? (
                  <p className="text-sm text-slate-500">{t('paired_empty')}</p>
                ) : (
                  <ul className="flex flex-col gap-2">
                    {paired.map((device) => (
                      <DeviceCard
                        key={device.mac}
                        device={device}
                        handle={handle}
                        activeOutput={state.activeOutput === device.mac}
                        activeInput={state.activeInput === device.mac}
                      />
                    ))}
                  </ul>
                )}
              </Panel>
              <Panel title={t('nearby_title', { count: nearby.length })}>
                {nearby.length === 0 ? (
                  <p className="text-sm text-slate-500">{t('nearby_empty')}</p>
                ) : (
                  <ul className="flex flex-col gap-2">
                    {nearby.map((device) => (
                      <DeviceCard key={device.mac} device={device} handle={handle} activeOutput={false} activeInput={false} />
                    ))}
                  </ul>
                )}
              </Panel>
              <PriorityPanel state={state} handle={handle} />
            </div>
          )}
        </div>
      )}
    </ModuleFrame>
  );
};

export default View;
