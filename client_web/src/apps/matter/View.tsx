import React, { useCallback, useEffect, useState } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import {
  AppFrame,
  Panel,
  Stat,
  StatRow,
  Pill,
  Btn,
  Row,
  List,
  Empty,
  Loading,
  inputClass,
} from '../shared/kit';
import {
  RefreshCw,
  PlusCircle,
  Zap,
  Power,
  Radio,
  Sliders,
} from 'lucide-react';
import { PtzPanel } from './PtzPanel';

type Tab = 'devices' | 'commission' | 'ptz' | 'energy' | 'bridge';

interface MatterNode {
  node_id: number;
  name: string;
  vendor_id: number;
  product_id: number;
  version: string;
  connected: boolean;
  endpoints: Array<{ id: number; device_type: number; name: string; clusters: number[] }>;
}

interface BridgeEndpoint {
  id: number;
  name: string;
  device_type: number;
  entity_id?: string;
}

interface DiscoveredDevice {
  ip: string;
  port: number;
  discriminator: number;
  vendor_id: number;
  product_id: number;
  device_type: number;
  device_name: string;
  commissionable: boolean;
}

export const View: React.FC = () => {
  const { t } = useScopedI18n('apps/matter');
  const [tab, setTab] = useState<Tab>('devices');
  const [loading, setLoading] = useState<boolean>(true);
  const [spec, setSpec] = useState<string>('1.6.1');
  const [nodes, setNodes] = useState<MatterNode[]>([]);
  const [bridgeEndpoints, setBridgeEndpoints] = useState<BridgeEndpoint[]>([]);

  const [pairingCode, setPairingCode] = useState<string>('');
  const [deviceName, setDeviceName] = useState<string>('');
  const [deviceType, setDeviceType] = useState<number>(0x0100);
  const [commissioning, setCommissioning] = useState<boolean>(false);
  const [commissionMsg, setCommissionMsg] = useState<string>('');

  const [scanning, setScanning] = useState<boolean>(false);
  const [discovered, setDiscovered] = useState<DiscoveredDevice[]>([]);
  const [syncingHardware, setSyncingHardware] = useState<boolean>(false);

  const [pan, setPan] = useState<number>(180);
  const [tilt, setTilt] = useState<number>(0);
  const [zoom, setZoom] = useState<number>(1);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const resStatus = await fetch('/api/matter/status');
      if (resStatus.ok) {
        const data = await resStatus.json();
        setSpec(data.spec || '1.6.1');
      }
      const resNodes = await fetch('/api/matter/nodes');
      if (resNodes.ok) {
        const data = await resNodes.json();
        setNodes(data.nodes || []);
      }
      const resBridge = await fetch('/api/matter/bridge/endpoints');
      if (resBridge.ok) {
        const data = await resBridge.json();
        setBridgeEndpoints(data.endpoints || []);
      }
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleScanNetwork = async () => {
    setScanning(true);
    try {
      const res = await fetch('/api/matter/discover?timeout=1.5');
      if (res.ok) {
        const data = await res.json();
        setDiscovered(data.discovered || []);
      }
    } catch {
    } finally {
      setScanning(false);
    }
  };

  const handleAutoEnroll = async (dev: DiscoveredDevice) => {
    setCommissioning(true);
    setCommissionMsg('');
    try {
      const res = await fetch('/api/matter/auto_enroll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dev),
      });
      if (res.ok) {
        const data = await res.json();
        setCommissionMsg(`${t('commissioning_success')}: Node ${data.node_id}`);
        setDiscovered((prev) => prev.filter((d) => d.ip !== dev.ip));
        loadData();
      } else {
        setCommissionMsg(t('error_unsupported'));
      }
    } catch {
      setCommissionMsg(t('error_timeout'));
    } finally {
      setCommissioning(false);
    }
  };

  const handleSyncHardware = async () => {
    setSyncingHardware(true);
    try {
      const res = await fetch('/api/matter/bridge/sync', { method: 'POST' });
      if (res.ok) {
        loadData();
      }
    } catch {
    } finally {
      setSyncingHardware(false);
    }
  };

  const handleCommission = async () => {
    if (!pairingCode) return;
    setCommissioning(true);
    setCommissionMsg('');
    try {
      const res = await fetch('/api/matter/commission', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pairing_code: pairingCode,
          name: deviceName || undefined,
          device_type: deviceType,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setCommissionMsg(`${t('commissioning_success')}: Node ${data.node_id}`);
        setPairingCode('');
        setDeviceName('');
        loadData();
      } else {
        setCommissionMsg(t('error_unsupported'));
      }
    } catch {
      setCommissionMsg(t('error_timeout'));
    } finally {
      setCommissioning(false);
    }
  };

  const invokeCommand = async (
    nodeId: number,
    endpointId: number,
    clusterId: number,
    commandId: number,
    payload?: Record<string, unknown>
  ) => {
    try {
      await fetch('/api/matter/clusters/invoke', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          node_id: nodeId,
          endpoint_id: endpointId,
          cluster_id: clusterId,
          command_id: commandId,
          payload,
        }),
      });
      loadData();
    } catch {}
  };

  const handlePtzMove = (newPan: number, newTilt: number, newZoom: number) => {
    setPan(newPan);
    setTilt(newTilt);
    setZoom(newZoom);
    const bridgeCam = bridgeEndpoints.find(
      (e) => e.device_type === 0x0500 || (e.entity_id && e.entity_id.startsWith('camera.'))
    );
    if (bridgeCam) {
      invokeCommand(0, bridgeCam.id, 0x0552, 0x0001, {
        pan: newPan,
        tilt: newTilt,
        zoom: newZoom,
      });
      return;
    }
    const camNode = nodes.find((n) =>
      n.endpoints.some((e) => e.device_type === 0x0500 || e.clusters.includes(0x0552))
    );
    if (camNode) {
      invokeCommand(camNode.node_id, 1, 0x0552, 0x0001, {
        pan: newPan,
        tilt: newTilt,
        zoom: newZoom,
      });
    }
  };

  const hasPtzCam =
    bridgeEndpoints.some(
      (e) => e.device_type === 0x0500 || (e.entity_id && e.entity_id.startsWith('camera.'))
    ) ||
    nodes.some((n) =>
      n.endpoints.some((e) => e.device_type === 0x0500 || e.clusters.includes(0x0552))
    );

  const realBridgeEndpoints = bridgeEndpoints.filter((e) => e.id !== 0);

  return (
    <AppFrame
      title={`${t('title')} (${spec})`}
      description={t('description')}
      actions={
        <div className="flex items-center gap-2">
          <Btn tone="cyan" onClick={handleSyncHardware} disabled={syncingHardware}>
            <Sliders className="h-3.5 w-3.5" aria-hidden="true" />
            {t('btn_sync_hardware')}
          </Btn>
          <Btn tone="slate" onClick={loadData}>
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            {t('refresh_button')}
          </Btn>
        </div>
      }
    >
      <div className="flex flex-col gap-4 p-4 h-full overflow-y-auto">
        <StatRow>
          <Stat label="Spec Matter" value={spec} tone="cyan" />
          <Stat label="Nodi Controllati" value={nodes.length} tone="emerald" />
          <Stat label="Hardware Bridge" value={realBridgeEndpoints.length} tone="purple" />
          <Stat label="Stato Fabric" value="Multi-Admin" tone="cyan" />
        </StatRow>

        <div className="flex gap-2 border-b border-outline pb-2">
          {(['devices', 'commission', 'ptz', 'energy', 'bridge'] as Tab[]).map((tabKey) => (
            <button
              key={tabKey}
              type="button"
              onClick={() => setTab(tabKey)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                tab === tabKey ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:bg-surface-container-high'
              }`}
            >
              {t(`tab_${tabKey}`)}
            </button>
          ))}
        </div>

        {loading ? (
          <Loading label="Caricamento Matter..." />
        ) : (
          <>
            {tab === 'devices' && (
              <Panel title={t('tab_devices')}>
                {nodes.length === 0 ? (
                  <Empty>{t('no_devices')}</Empty>
                ) : (
                  <List>
                    {nodes.map((node) => (
                      <Row
                        key={node.node_id}
                        actions={
                          <div className="flex items-center gap-2">
                            <Pill tone={node.connected ? 'emerald' : 'slate'}>
                              {node.connected ? 'Online' : 'Offline'}
                            </Pill>
                            {node.endpoints.some((e) => e.clusters.includes(0x0006)) && (
                              <Btn
                                tone="cyan"
                                onClick={() => invokeCommand(node.node_id, 1, 0x0006, 0x0002)}
                              >
                                <Power className="h-3.5 w-3.5" aria-hidden="true" />
                                {t('action_toggle')}
                              </Btn>
                            )}
                          </div>
                        }
                      >
                        <div className="font-semibold">{node.name}</div>
                        <div className="text-xs text-on-surface-variant">
                          Node ID: 0x{node.node_id.toString(16).toUpperCase()} · Vendor: 0x{node.vendor_id.toString(16)}
                        </div>
                      </Row>
                    ))}
                  </List>
                )}
              </Panel>
            )}

            {tab === 'commission' && (
              <div className="flex flex-col gap-6 max-w-2xl">
                <Panel title={t('scan_network_title')}>
                  <div className="flex flex-col gap-3">
                    <p className="text-xs text-on-surface-variant">{t('scan_network_desc')}</p>
                    <div className="flex items-center gap-3">
                      <Btn tone="cyan" onClick={handleScanNetwork} disabled={scanning}>
                        <Radio className="h-3.5 w-3.5" aria-hidden="true" />
                        {t('btn_scan_now')}
                      </Btn>
                    </div>

                    {scanning && <Loading label={t('scanning_label')} />}

                    {!scanning && discovered.length > 0 && (
                      <div className="flex flex-col gap-2 mt-2">
                        <div className="text-xs font-semibold text-primary">
                          {t('discovered_found', { '0': discovered.length })}
                        </div>
                        <List>
                          {discovered.map((dev) => (
                            <Row
                              key={dev.ip}
                              actions={
                                <Btn
                                  tone="emerald"
                                  onClick={() => handleAutoEnroll(dev)}
                                  disabled={commissioning}
                                >
                                  <PlusCircle className="h-3.5 w-3.5" aria-hidden="true" />
                                  {t('btn_auto_enroll')}
                                </Btn>
                              }
                            >
                              <div className="font-semibold">{dev.device_name}</div>
                              <div className="text-xs text-on-surface-variant">
                                IP: {dev.ip}:{dev.port} · Discriminator: {dev.discriminator} · Vendor: 0x{dev.vendor_id.toString(16)}
                              </div>
                            </Row>
                          ))}
                        </List>
                      </div>
                    )}

                    {!scanning && discovered.length === 0 && (
                      <p className="text-xs text-on-surface-variant italic mt-1">
                        {t('no_discovered_devices')}
                      </p>
                    )}
                  </div>
                </Panel>

                <Panel title={t('manual_commission_title')}>
                  <div className="flex flex-col gap-3 max-w-md">
                    <label className="text-xs font-semibold text-on-surface">{t('pairing_code_label')}</label>
                    <input
                      type="text"
                      className={inputClass}
                      placeholder="1234-5678 oppure MT:Y.11..."
                      value={pairingCode}
                      onChange={(e) => setPairingCode(e.target.value)}
                    />

                    <label className="text-xs font-semibold text-on-surface">{t('device_name_label')}</label>
                    <input
                      type="text"
                      className={inputClass}
                      placeholder="es. Lampada Salotto"
                      value={deviceName}
                      onChange={(e) => setDeviceName(e.target.value)}
                    />

                    <label className="text-xs font-semibold text-on-surface">{t('device_category_label')}</label>
                    <select
                      className={inputClass}
                      value={deviceType}
                      onChange={(e) => setDeviceType(Number(e.target.value))}
                    >
                      <option value={0x0100}>Luce On/Off</option>
                      <option value={0x0101}>Luce Dimmabile</option>
                      <option value={0x0301}>Termostato / HVAC</option>
                      <option value={0x0500}>Telecamera PTZ 360°</option>
                      <option value={0x0510}>Smart Energy Meter</option>
                    </select>

                    <Btn tone="cyan" onClick={handleCommission} disabled={commissioning || !pairingCode}>
                      <PlusCircle className="h-3.5 w-3.5" aria-hidden="true" />
                      {commissioning ? 'Associazione in corso...' : t('commission_button')}
                    </Btn>

                    {commissionMsg && (
                      <div className="text-xs font-medium text-primary mt-1">{commissionMsg}</div>
                    )}
                  </div>
                </Panel>
              </div>
            )}

            {tab === 'ptz' && (
              <PtzPanel
                hasPtzCam={hasPtzCam}
                pan={pan}
                tilt={tilt}
                zoom={zoom}
                onMove={handlePtzMove}
              />
            )}

            {tab === 'energy' && (
              <Panel title={t('tab_energy')}>
                <div className="flex flex-col gap-3">
                  <div className="flex items-center gap-2">
                    <Zap className="h-4 w-4 text-amber-400" />
                    <span className="font-semibold text-sm">Cluster Energetici Matter 1.6.1</span>
                  </div>
                  <StatRow>
                    <Stat label="Consumo Attuale" value="0.0 W" tone="emerald" />
                    <Stat label="Energia Giornaliera" value="0.0 kWh" tone="cyan" />
                    <Stat label="Produzione Solare" value="0.0 W" tone="amber" />
                    <Stat label="Stato EVSE" value="Standby" tone="purple" />
                  </StatRow>
                </div>
              </Panel>
            )}

            {tab === 'bridge' && (
              <Panel title={t('tab_bridge')}>
                <p className="text-xs text-on-surface-variant mb-3">{t('bridge_sync_desc')}</p>
                {realBridgeEndpoints.length === 0 ? (
                  <Empty>{t('no_bridge_endpoints')}</Empty>
                ) : (
                  <List>
                    {realBridgeEndpoints.map((ep) => (
                      <Row
                        key={ep.id}
                        actions={
                          <Pill tone="purple">
                            Endpoint #{ep.id}
                          </Pill>
                        }
                      >
                        <div className="font-semibold">{ep.name}</div>
                        <div className="text-xs text-on-surface-variant">
                          Tipo: 0x{ep.device_type.toString(16).toUpperCase()} {ep.entity_id ? `· Entità: ${ep.entity_id}` : ''}
                        </div>
                      </Row>
                    ))}
                  </List>
                )}
              </Panel>
            )}
          </>
        )}
      </div>
    </AppFrame>
  );
};
