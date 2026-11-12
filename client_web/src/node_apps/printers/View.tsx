import React, { useCallback, useEffect, useState } from 'react';
import { Printer as PrinterIcon } from 'lucide-react';
import { reportError } from '../../shared/errors/errorBus';
import { ControlScope } from '../console/data/nodeConsoleApi';
import { DeviceInventory } from '../shared/components/DeviceInventory';
import { ModuleFrame, Notice, Panel } from '../shared/components/ModuleFrame';
import { usePairedNode } from '../shared/hooks/usePairedNode';
import { AddPrinterPanel } from './components/AddPrinterPanel';
import { DiscoverPanel } from './components/DiscoverPanel';
import { PrinterCard } from './components/PrinterCard';
import { PrinterOptionsPanel } from './components/PrinterOptionsPanel';
import { PrinterList, fetchPrinters } from './data/printersApi';
import { usePrintersI18n } from './scope';

interface Props {
  readonly nodeId?: string;
  readonly scope?: ControlScope;
}

export const View: React.FC<Props> = ({ nodeId = '', scope = 'mesh' }) => {
  const { t } = usePrintersI18n();
  const local = scope === 'local';
  const { node } = usePairedNode(nodeId, scope);
  const [list, setList] = useState<PrinterList | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const refresh = useCallback(() => setTick((value) => value + 1), []);

  useEffect(() => {
    if (!local) {
      return;
    }
    const controller = new AbortController();
    fetchPrinters(controller.signal)
      .then(setList)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('node_printers_unavailable', cause));
    return () => controller.abort();
  }, [local, tick]);

  const printers = list?.printers ?? [];
  const selected = printers.find((p) => p.id === selectedId) ?? printers.find((p) => p.isDefault) ?? printers[0] ?? null;

  return (
    <ModuleFrame icon={PrinterIcon} title={t('title')} subtitle={t('description')} badge={t(`scope_${scope}`)}>
      {scope === 'mesh' && <Notice tone="warn">{t('notice_unpaired')}</Notice>}
      {scope === 'paired' && (
        <>
          <Notice tone="info">{t('notice_paired')}</Notice>
          <DeviceInventory title={t('inventory_title')} devices={node?.hardware?.usb ?? []} emptyLabel={t('inventory_empty')} />
        </>
      )}
      {local && list && (
        <div className="grid gap-4 xl:grid-cols-2">
          <div className="flex min-w-0 flex-col gap-4">
            <Panel title={t('list_title', { count: printers.length })}>
              <ul className="flex flex-col gap-2">
                {printers.map((printer) => (
                  <PrinterCard
                    key={printer.id}
                    printer={printer}
                    selected={printer.id === selected?.id}
                    onSelect={() => setSelectedId(printer.id)}
                    onChanged={refresh}
                  />
                ))}
              </ul>
            </Panel>
            {selected && <PrinterOptionsPanel printer={selected} onSaved={refresh} />}
          </div>
          <div className="flex min-w-0 flex-col gap-4">
            <DiscoverPanel canInstall={list.canInstall} onInstalled={refresh} />
            <AddPrinterPanel onAdded={refresh} />
          </div>
        </div>
      )}
    </ModuleFrame>
  );
};

export default View;
