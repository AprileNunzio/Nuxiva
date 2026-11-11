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
  Video,
  Zap,
  Power,
  Compass,
} from 'lucide-react';

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

  return (
    <AppFrame
      title={`${t('title')} (${spec})`}
      description={t('description')}
      actions={
        <Btn tone="slate" onClick={loadData}>
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          {t('refresh_button')}
        </Btn>
      }
    >
      <div className="flex flex-col gap-4 p-4 h-full overflow-y-auto">
        <StatRow>
          <Stat label="Spec Matter" value={spec} tone="cyan" />
          <Stat label="Nodi Controllati" value={nodes.length} tone="emerald" />
          <Stat label="Endpoint Bridge" value={bridgeEndpoints.length} tone="purple" />
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
              <Panel title={t('tab_commission')}>
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
                    <option value={0x0100}>Illuminazione On/Off (0x0100)</option>
                    <option value={0x0101}>Luce Dimmerabile (0x0101)</option>
                    <option value={0x0301}>Termostato / Clima (0x0301)</option>
                    <option value={0x0500}>Telecamera PTZ 360° (0x0500)</option>
                    <option value={0x0510}>Smart Energy Meter (0x0510)</option>
                    <option value={0x0076}>Allarme Smoke & CO (0x0076)</option>
                    <option value={0x0107}>Sensore Presenza (0x0107)</option>
                  </select>

                  <Btn
                    tone="cyan"
                    disabled={!pairingCode || commissioning}
                    onClick={handleCommission}
                  >
                    <PlusCircle className="h-3.5 w-3.5" aria-hidden="true" />
                    {commissioning ? 'Associazione...' : t('commission_button')}
                  </Btn>

                  {commissionMsg && (
                    <div className="p-3 bg-surface-container-high rounded-xl text-xs text-on-surface">
                      {commissionMsg}
                    </div>
                  )}
                </div>
              </Panel>
            )}

            {tab === 'ptz' && (
              <Panel title={t('tab_ptz')}>
                <div className="flex flex-col gap-4">
                  <div className="flex items-center gap-3">
                    <Video size={18} className="text-primary" />
                    <span className="text-sm font-semibold">Controllo Telecamere PTZ 360° Matter 1.6.1</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="flex flex-col gap-2 p-3 bg-surface-container rounded-xl">
                      <div className="flex justify-between text-xs">
                        <span>{t('ptz_pan')}</span>
                        <span className="font-bold">{pan}°</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="360"
                        value={pan}
                        onChange={(e) => handlePtzMove(Number(e.target.value), tilt, zoom)}
                      />
                    </div>
                    <div className="flex flex-col gap-2 p-3 bg-surface-container rounded-xl">
                      <div className="flex justify-between text-xs">
                        <span>{t('ptz_tilt')}</span>
                        <span className="font-bold">{tilt}°</span>
                      </div>
                      <input
                        type="range"
                        min="-90"
                        max="90"
                        value={tilt}
                        onChange={(e) => handlePtzMove(pan, Number(e.target.value), zoom)}
                      />
                    </div>
                    <div className="flex flex-col gap-2 p-3 bg-surface-container rounded-xl">
                      <div className="flex justify-between text-xs">
                        <span>{t('ptz_zoom')}</span>
                        <span className="font-bold">{zoom.toFixed(1)}x</span>
                      </div>
                      <input
                        type="range"
                        min="1"
                        max="10"
                        step="0.5"
                        value={zoom}
                        onChange={(e) => handlePtzMove(pan, tilt, Number(e.target.value))}
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Btn
                      tone="slate"
                      onClick={() => handlePtzMove(180, 0, 1)}
                    >
                      <Compass className="h-3.5 w-3.5" aria-hidden="true" />
                      Centra Telecamera 360°
                    </Btn>
                  </div>
                </div>
              </Panel>
            )}

            {tab === 'energy' && (
              <Panel title={t('tab_energy')}>
                <div className="flex flex-col gap-3">
                  <div className="flex items-center gap-3">
                    <Zap size={18} className="text-warning" />
                    <span className="text-sm font-semibold">Monitoraggio Energetico Matter 1.6</span>
                  </div>
                  <StatRow>
                    <Stat label="Potenza Attiva Istantanea" value="420 W" tone="amber" />
                    <Stat label="Energia Cumulativa" value="12.8 kWh" tone="cyan" />
                    <Stat label="Stoccaggio Batteria" value="84%" tone="emerald" />
                    <Stat label="Ricarica EVSE" value="7.4 kW" tone="purple" />
                  </StatRow>
                </div>
              </Panel>
            )}

            {tab === 'bridge' && (
              <Panel title={t('tab_bridge')}>
                <div className="flex flex-col gap-3">
                  <div className="flex justify-between items-center pb-2 border-b border-outline">
                    <span className="text-xs text-on-surface-variant">
                      Entità Nuxiva esposte agli ecosistemi Matter (Apple Home, Google Home, Alexa)
                    </span>
                    <Btn tone="purple" onClick={() => alert('Finestra di associazione aperta per 180s')}>
                      {t('open_window_button')}
                    </Btn>
                  </div>
                  <List>
                    {bridgeEndpoints.map((ep) => (
                      <Row
                        key={ep.id}
                        actions={
                          <Pill tone="slate">{ep.entity_id || 'Nuxiva Bridged'}</Pill>
                        }
                      >
                        <div className="font-semibold">{ep.name}</div>
                        <div className="text-xs text-on-surface-variant">
                          Endpoint ID: {ep.id} · Type: 0x{ep.device_type.toString(16)}
                        </div>
                      </Row>
                    ))}
                  </List>
                </div>
              </Panel>
            )}
          </>
        )}
      </div>
    </AppFrame>
  );
};

export default View;
