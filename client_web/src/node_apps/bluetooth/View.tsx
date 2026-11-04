import React, { useState } from 'react';
import { Bluetooth, Loader2 } from 'lucide-react';
import { ControlScope } from '../console/data/nodeConsoleApi';
import { ModuleFrame, Notice } from '../shared/components/ModuleFrame';
import { usePairedNode } from '../shared/hooks/usePairedNode';
import { BluetoothDevice } from '../../shared/bluetooth/model';
import { useBluetooth } from '../../shared/bluetooth/useBluetooth';
import { AdapterPanel } from './components/AdapterPanel';
import { BehaviorPanel } from './components/BehaviorPanel';
import { DeviceSection } from './components/DeviceSection';
import { PriorityPanel } from './components/PriorityPanel';
import { useBluetoothI18n } from './scope';

interface Props {
  readonly nodeId?: string;
  readonly scope?: ControlScope;
}

const byConnection = (a: BluetoothDevice, b: BluetoothDevice) => Number(b.connected) - Number(a.connected) || a.name.localeCompare(b.name);
const bySignal = (a: BluetoothDevice, b: BluetoothDevice) => (b.rssi ?? -999) - (a.rssi ?? -999);

const LocalBluetooth: React.FC = () => {
  const { t } = useBluetoothI18n();
  const handle = useBluetooth();
  const [openMac, setOpenMac] = useState<string | null>(null);
  const state = handle.state;

  if (state === null) {
    return handle.reachable ? (
      <p className="flex items-center gap-2 text-sm text-slate-500" role="status">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        {t('loading')}
      </p>
    ) : (
      <Notice tone="warn">{t('unreachable')}</Notice>
    );
  }

  const paired = state.devices.filter((d) => d.paired).sort(byConnection);
  const nearby = state.devices.filter((d) => !d.paired).sort(bySignal);
  const toggle = (mac: string) => setOpenMac((current) => (current === mac ? null : mac));

  return (
    <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)] xl:grid-rows-[auto_1fr]">
      <div className="flex min-w-0 flex-col gap-4 xl:col-start-1 xl:row-start-1">
        {!handle.reachable && <Notice tone="warn">{t('unreachable')}</Notice>}
        <AdapterPanel state={state} handle={handle} />
      </div>
      {handle.ready && (
        <div className="flex min-w-0 flex-col gap-4 xl:col-start-2 xl:row-span-2 xl:row-start-1">
          <DeviceSection
            title={t('paired_title', { count: paired.length })}
            empty={t('paired_empty')}
            devices={paired}
            handle={handle}
            openMac={openMac}
            onToggle={toggle}
          />
          <DeviceSection
            title={t('nearby_title', { count: nearby.length })}
            empty={t(handle.scanning ? 'nearby_searching' : 'nearby_empty')}
            devices={nearby}
            handle={handle}
            openMac={openMac}
            onToggle={toggle}
          />
        </div>
      )}
      {handle.ready && (
        <div className="flex min-w-0 flex-col gap-4 xl:col-start-1 xl:row-start-2">
          <BehaviorPanel handle={handle} />
          <PriorityPanel handle={handle} />
        </div>
      )}
    </div>
  );
};

export const View: React.FC<Props> = ({ nodeId = '', scope = 'mesh' }) => {
  const { t } = useBluetoothI18n();
  const { node } = usePairedNode(nodeId, scope);

  return (
    <ModuleFrame icon={Bluetooth} title={t('title')} subtitle={t('description')} badge={t(`scope_${scope}`)}>
      {scope === 'mesh' && <Notice tone="warn">{t('notice_unpaired')}</Notice>}
      {scope === 'paired' && <Notice tone="info">{t(node?.hardware?.bluetooth ? 'notice_paired_present' : 'notice_paired_absent')}</Notice>}
      {scope === 'local' && <LocalBluetooth />}
    </ModuleFrame>
  );
};

export default View;
