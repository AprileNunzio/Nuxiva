import React, { useCallback, useEffect, useState } from 'react';
import { Plus, Server, Trash2 } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { reportError } from '../../shared/errors/errorBus';
import { ConfirmDialog } from '../../shared/ui/ConfirmDialog';
import { useLinks } from '../../node_apps/client_link/hooks/useLinks';
import { AppFrame, Btn, Empty, Loading, Panel, Pill, Row } from '../shared/kit';
import { fetchNodes, fetchUsbPorts, deleteNode } from './api';
import { MeshNodeItem, UsbPort } from './types';
import { NodeWizard } from './NodeWizard';
import { PcLinkPanel } from './components/PcLinkPanel';

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/nodes');
  const [nodes, setNodes] = useState<MeshNodeItem[]>([]);
  const [usbPorts, setUsbPorts] = useState<UsbPort[]>([]);
  const [loading, setLoading] = useState(true);
  const [showWizard, setShowWizard] = useState(false);
  const [removing, setRemoving] = useState<MeshNodeItem | null>(null);
  const [busy, setBusy] = useState(false);
  const links = useLinks(true);
  const load = useCallback(async () => {
    try {
      setNodes(await fetchNodes());
    } catch (cause) {
      reportError('nodes_load_failed', cause);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    void load();
    fetchUsbPorts().then(setUsbPorts).catch((cause) => reportError('nodes_usb_failed', cause));
    const timer = window.setInterval(() => !document.hidden && void load(), 10000);
    return () => window.clearInterval(timer);
  }, [load]);
  const remove = async () => {
    if (!removing) return;
    setBusy(true);
    try {
      await deleteNode(removing.id);
      await load();
      setRemoving(null);
    } catch (cause) {
      reportError('nodes_delete_failed', cause);
    } finally {
      setBusy(false);
    }
  };
  return (
    <AppFrame title={t('title')} description={t('description')} onReload={() => void load()} actions={
      <Btn onClick={() => setShowWizard(true)}><Plus className="h-4 w-4" aria-hidden="true" />{t('add_node')}</Btn>
    }>
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title={t('step2_pc_title')}><PcLinkPanel handle={links} /></Panel>
        <Panel title={t('total_nodes')}>
          {loading ? <Loading label={t('loading')} /> : nodes.length === 0 ? <Empty>{t('empty')}</Empty> : (
            <ul className="space-y-2">
              {nodes.map((node) => (
                  <Row key={node.id} actions={node.source !== 'local' && node.id !== 'virtual-core' && node.id !== 'virtual_core' ? (
                    <Btn tone="rose" busy={busy} onClick={() => setRemoving(node)} title={t('deprovision')}>
                      <Trash2 className="h-4 w-4" aria-hidden="true" />{t('deprovision')}
                    </Btn>
                  ) : undefined}>
                    <div className="flex flex-wrap items-center gap-2"><Server className="h-4 w-4 text-cyan-700" aria-hidden="true" /><b>{node.name}</b><Pill tone={node.online ? 'emerald' : 'slate'}>{node.online === undefined ? node.status || '—' : t(node.online ? 'online' : 'offline')}</Pill></div>
                    <p className="mt-1 break-all text-xs text-slate-600">{[node.tier, node.ip].filter(Boolean).join(' · ')}</p>
                    {node.source === 'local' && <p className="mt-1 text-xs text-slate-500">{t('local_host')}</p>}
                  </Row>
              ))}
            </ul>
          )}
        </Panel>
      </div>
      {showWizard && <NodeWizard nodes={nodes} usbPorts={usbPorts} links={links} onChanged={setNodes} onClose={() => setShowWizard(false)} />}
      {removing && <ConfirmDialog title={t('deprovision')} body={t('confirm_delete')} confirmLabel={t('deprovision')} cancelLabel={t('cancel')} pending={busy} tone="danger" onConfirm={() => void remove()} onCancel={() => setRemoving(null)} />}
    </AppFrame>
  );
};
