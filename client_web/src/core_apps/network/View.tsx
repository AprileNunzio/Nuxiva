import React, { useCallback, useEffect, useState } from 'react';
import { useWindowTopology } from '../../app_shell/WindowTopology';
import { useOSApp, useWindowToolbar } from '../../app_shell/window_manager/WindowContext';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { OSIcon3D } from '../../app_shell/OSIcon3D';
import icon from './icon.png';
import { isStale } from '../../features/neural_mesh/domain/metrics';
import { OSSectionHeader, OSEnergyBar, Loading, Empty, OSAppLayout, OSSidebar, OSInspector } from '../shared/kit';
import { triggerNetworkScan, queryWhoIsMCP, studyDevice } from './api';
import './style.css';

interface MCPInsightState {
  readonly loading: boolean;
  readonly text?: string;
  readonly error?: string;
}

export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('core_apps/network');
  const os = useOSApp();
  const { snapshot, streamState } = useWindowTopology();

  const [localSearch, setLocalSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [view, setView] = useState<'devices' | 'energy'>('devices');
  const [technical, setTechnical] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [studyingNodeId, setStudyingNodeId] = useState<string | null>(null);
  const [mcpInsights, setMcpInsights] = useState<Record<string, MCPInsightState>>({});

  const search = (os.searchQuery || localSearch).trim();

  const handleScan = useCallback(async () => {
    setScanning(true);
    try {
      await triggerNetworkScan();
    } catch {
      // noop
    } finally {
      setTimeout(() => setScanning(false), 2000);
    }
  }, []);

  useWindowToolbar(
    useCallback(
      (id: string, value?: string) => {
        if (id === 'search') {
          const q = value || '';
          os.setSearchQuery(q);
          setLocalSearch(q);
        }
        if (id === 'view') setView(value === 'energy' ? 'energy' : 'devices');
        if (id === 'details') setTechnical((v) => !v);
        if (id === 'rescan') void handleScan();
        if (id === 'add') os.openApp({ appId: 'nodes' });
      },
      [os, handleScan]
    )
  );

  const nodes = snapshot?.neurons || [];
  const online = nodes.filter((node) => !isStale(node, Date.now()) && node.online !== false);
  const measured = online.filter((node) => Number.isFinite(node.telemetry.powerWatts) && node.telemetry.powerWatts !== null);
  const watts = measured.reduce((total, node) => total + (node.telemetry.powerWatts || 0), 0);
  const maxPower = Math.max(...measured.map((n) => n.telemetry.powerWatts || 0), 1);

  const format = useCallback(
    (value: number, maximumFractionDigits = 1) => value.toLocaleString(lang, { maximumFractionDigits }),
    [lang]
  );

  // Trova il nodo correntemente selezionato
  const selectedNode = nodes.find((n) => n.id === os.selectedId) || null;

  // Aggiorna breadcrumbs e status nel footer della finestra
  useEffect(() => {
    const isLive = streamState === 'live';
    const count = nodes.length;
    const onlineCount = online.length;
    const powerStr = measured.length > 0 ? `${format(watts)} W` : '';
    const details = [
      `${onlineCount}/${count} ${t('online').toLowerCase()}`,
      powerStr,
      scanning ? t('scanning') : '',
    ]
      .filter(Boolean)
      .join(' · ');

    os.setStatus({
      connected: isLive,
      itemCount: count,
      details,
    });

    // Breadcrumbs completi nella titlebar
    const crumbs = [
      {
        id: 'network-root',
        label: t('title'),
        onClick: () => {
          setActiveCategory('all');
          os.setSelectedId?.(undefined);
        },
      },
      {
        id: 'network-category',
        label: t(activeCategory),
        onClick: () => os.setSelectedId?.(undefined),
      },
      ...(selectedNode ? [{ id: 'network-device', label: selectedNode.name }] : []),
    ];
    os.setBreadcrumbs?.(crumbs);
  }, [
    os,
    streamState,
    nodes.length,
    online.length,
    measured.length,
    watts,
    scanning,
    activeCategory,
    selectedNode,
    t,
    format,
  ]);

  const handleAskMCP = async (nodeId: string, address: string) => {
    setMcpInsights((prev) => ({ ...prev, [nodeId]: { loading: true } }));
    try {
      const response = await queryWhoIsMCP(address);
      setMcpInsights((prev) => ({
        ...prev,
        [nodeId]: { loading: false, text: response || 'Nessuna informazione semantica aggiuntiva registrata.' },
      }));
    } catch {
      setMcpInsights((prev) => ({
        ...prev,
        [nodeId]: { loading: false, error: 'Errore di connessione MCP.' },
      }));
    }
  };

  const handleStudy = async (nodeId: string, address: string) => {
    setStudyingNodeId(nodeId);
    try {
      await studyDevice(address);
    } catch {
      // noop
    } finally {
      setTimeout(() => setStudyingNodeId(null), 1500);
    }
  };

  const filtered = nodes.filter(
    (node) =>
      (activeCategory === 'all' || node.kind === activeCategory) &&
      `${node.name} ${node.id} ${node.room || ''} ${node.ip || ''}`.toLowerCase().includes(search.toLowerCase())
  );

  const sidebarCategories = [
    { id: 'all', label: t('all'), count: nodes.length },
    { id: 'compute', label: t('compute'), count: nodes.filter((n) => n.kind === 'compute').length },
    { id: 'satellite', label: t('satellite'), count: nodes.filter((n) => n.kind === 'satellite').length },
    { id: 'micro', label: t('micro'), count: nodes.filter((n) => n.kind === 'micro').length },
    { id: 'mobile', label: t('mobile'), count: nodes.filter((n) => n.kind === 'mobile').length },
  ];

  const sidebar = (
    <div className="flex h-full flex-col justify-between">
      <OSSidebar
        title={t('filter')}
        items={sidebarCategories}
        activeId={activeCategory}
        onSelect={(cat) => {
          setActiveCategory(cat);
          os.setSelectedId?.(undefined);
        }}
        footer={
          <div className="flex flex-col gap-1 p-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600">{t('view')}</span>
            <div className="flex rounded-lg border border-slate-200 p-0.5 bg-slate-50">
              <button
                type="button"
                className={`flex-1 rounded-md py-1 text-xs font-medium transition ${
                  view === 'devices' ? 'bg-white shadow-xs text-blue-600 font-semibold' : 'text-slate-500'
                }`}
                onClick={() => setView('devices')}
              >
                {t('devices')}
              </button>
              <button
                type="button"
                className={`flex-1 rounded-md py-1 text-xs font-medium transition ${
                  view === 'energy' ? 'bg-white shadow-xs text-blue-600 font-semibold' : 'text-slate-500'
                }`}
                onClick={() => setView('energy')}
              >
                {t('energy')}
              </button>
            </div>
          </div>
        }
      />
    </div>
  );

  const inspector = selectedNode ? (
    <OSInspector
      title={selectedNode.name}
      subtitle={`${selectedNode.room || t(selectedNode.kind)} · ${selectedNode.ip || '—'}`}
      onClose={() => os.setSelectedId?.(undefined)}
      actions={
        <div className="flex flex-col gap-2">
          <button
            type="button"
            className="w-full rounded-lg bg-blue-600 py-2 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 transition"
            onClick={() =>
              os.openApp({
                appId: 'node_apps/console',
                targetNodeId: selectedNode.id,
                initialPayload: { name: selectedNode.name },
              })
            }
          >
            {t('manage')} →
          </button>
          <button
            type="button"
            className="w-full rounded-lg border border-cyan-300 bg-cyan-950/20 py-2 text-xs font-semibold text-cyan-600 dark:text-cyan-700 shadow-xs hover:bg-cyan-900/30 transition"
            onClick={() =>
              os.openApp({
                appId: 'node_apps/console',
                targetNodeId: selectedNode.id,
                initialPayload: { name: selectedNode.name, module: 'task_manager' },
              })
            }
          >
            {t('task_manager')} →
          </button>
          <button
            type="button"
            className="w-full rounded-lg border border-slate-300 bg-slate-100 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-750 transition"
            onClick={() =>
              os.openApp({
                appId: 'node_apps/console',
                targetNodeId: selectedNode.id,
                initialPayload: { name: selectedNode.name, module: 'connections' },
              })
            }
          >
            {t('connections_center')} →
          </button>
          <div className="flex gap-2">
            <button
              type="button"
              className="flex-1 rounded-lg border border-slate-200 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
              onClick={() => void handleAskMCP(selectedNode.id, selectedNode.ip || selectedNode.name)}
            >
              {t('mcp_whois')}
            </button>
            <button
              type="button"
              className="flex-1 rounded-lg border border-slate-200 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
              disabled={studyingNodeId === selectedNode.id}
              onClick={() => void handleStudy(selectedNode.id, selectedNode.ip || selectedNode.id)}
            >
              {studyingNodeId === selectedNode.id ? '...' : t('device_study')}
            </button>
          </div>
        </div>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-3 rounded-xl border border-slate-100 bg-slate-50/70 p-3">
          <OSIcon3D name={selectedNode.name} source={icon} size="md" />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <strong className="truncate text-sm text-slate-800">{selectedNode.name}</strong>
              <span
                className="rounded-full px-2 py-0.5 text-[10px] font-semibold"
                style={{
                  backgroundColor: !isStale(selectedNode, Date.now()) && selectedNode.online !== false ? '#ecfdf5' : '#f1f5f9',
                  color: !isStale(selectedNode, Date.now()) && selectedNode.online !== false ? '#047857' : '#64748b',
                }}
              >
                {!isStale(selectedNode, Date.now()) && selectedNode.online !== false ? t('online') : t('offline')}
              </span>
            </div>
            <span className="text-xs text-slate-600">{t(selectedNode.kind)}</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-slate-200/80 p-2.5">
            <span className="block text-[10px] text-slate-600">{t('power')}</span>
            <strong className="text-sm font-semibold text-slate-800">
              {selectedNode.telemetry.powerWatts != null ? `${format(selectedNode.telemetry.powerWatts)} W` : '—'}
            </strong>
          </div>
          <div className="rounded-lg border border-slate-200/80 p-2.5">
            <span className="block text-[10px] text-slate-600">{t('latency')}</span>
            <strong className="text-sm font-semibold text-slate-800">
              {selectedNode.telemetry.pingMs != null ? `${selectedNode.telemetry.pingMs} ms` : '—'}
            </strong>
          </div>
          <div className="rounded-lg border border-slate-200/80 p-2.5">
            <span className="block text-[10px] text-slate-600">CPU</span>
            <strong className="text-sm font-semibold text-slate-800">
              {selectedNode.telemetry.cpuPercent != null ? `${format(selectedNode.telemetry.cpuPercent)}%` : '—'}
            </strong>
          </div>
          <div className="rounded-lg border border-slate-200/80 p-2.5">
            <span className="block text-[10px] text-slate-600">RAM</span>
            <strong className="text-xs font-semibold text-slate-800 truncate block">
              {selectedNode.telemetry.ramUsedGb != null
                ? `${format(selectedNode.telemetry.ramUsedGb)} / ${format(selectedNode.telemetry.ramTotalGb || 0)} GB`
                : '—'}
            </strong>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200/80 bg-slate-50/50 p-3 text-xs">
          <span className="mb-2 block text-[10px] font-bold uppercase tracking-wider text-slate-600">
            {t('technical')}
          </span>
          <div className="flex flex-col gap-1.5 text-slate-600">
            <div className="flex justify-between">
              <span className="text-slate-600">{t('address')}</span>
              <span className="font-mono">{selectedNode.ip || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-600">{t('platform')}</span>
              <span>{selectedNode.telemetry.os || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-600">ID Nodo</span>
              <span className="font-mono truncate max-w-[10rem]">{selectedNode.id}</span>
            </div>
          </div>
        </div>

        {mcpInsights[selectedNode.id] && (
          <div className="rounded-lg border border-blue-200 bg-blue-50/40 p-3 text-xs">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-blue-700">
              Insight Assistente MCP
            </span>
            {mcpInsights[selectedNode.id].loading && <p className="italic text-slate-500">{t('scanning')}</p>}
            {mcpInsights[selectedNode.id].error && <p className="text-rose-600">{mcpInsights[selectedNode.id].error}</p>}
            {mcpInsights[selectedNode.id].text && (
              <p className="text-slate-700 leading-relaxed whitespace-pre-wrap">{mcpInsights[selectedNode.id].text}</p>
            )}
          </div>
        )}
      </div>
    </OSInspector>
  ) : (
    <div className="flex h-full flex-col items-center justify-center p-6 text-center text-slate-600">
      <OSIcon3D name="Preview" source={icon} size="md" />
      <p className="mt-3 text-xs font-medium text-slate-600">Seleziona un dispositivo</p>
      <span className="mt-1 text-[11px] text-slate-600">
        Fai clic su qualsiasi elemento per visualizzarne dettagli tecnici, telemetria in tempo reale e insight MCP.
      </span>
    </div>
  );

  return (
    <OSAppLayout
      sidebar={sidebar}
      inspector={inspector}
      isInspectorOpen={os.inspectorOpen ?? true}
      content={
        <div className="network-os">
          <header className="network-intro">
            <div>
              <p>{t('eyebrow')}</p>
              <h1>{t('heading')}</h1>
              <span>{t('description')}</span>
            </div>
            <div className="network-intro-actions">
              <span className="network-live" data-live={streamState === 'live'}>
                {t(streamState === 'live' ? 'live' : 'connecting')}
              </span>
              <button
                type="button"
                className="network-scan-btn"
                disabled={scanning}
                onClick={() => void handleScan()}
              >
                {scanning ? t('scanning') : t('rescan')}
              </button>
            </div>
          </header>

          <div className="network-summary">
            <article>
              <span>{t('devices')}</span>
              <strong>{nodes.length}</strong>
            </article>
            <article>
              <span>{t('online')}</span>
              <strong>
                {online.length}
                <small> / {nodes.length}</small>
              </strong>
            </article>
            <article>
              <span>{t('measured_power')}</span>
              <strong>
                {measured.length ? format(watts) : '—'}
                <small> W</small>
              </strong>
              <p>{t('coverage', { known: measured.length, total: nodes.length })}</p>
            </article>
          </div>

          {!snapshot && <Loading label={t(streamState === 'offline' ? 'unavailable' : 'connecting')} />}
          {snapshot && filtered.length === 0 && <Empty>{t('empty')}</Empty>}

          {view === 'energy' && (
            <div className="network-energy-section">
              <OSSectionHeader title={t('energy')} description={t('energy_note')} />
              <div className="network-energy-list">
                {filtered.map((node) => {
                  const live = !isStale(node, Date.now()) && node.online !== false;
                  const power = live && node.telemetry.powerWatts !== null ? node.telemetry.powerWatts : 0;
                  const formattedValue = live && node.telemetry.powerWatts !== null ? `${format(power)} W` : t('not_measured');
                  const isSelected = os.selectedId === node.id;

                  return (
                    <div
                      key={node.id}
                      className={`network-energy-row cursor-pointer transition ${isSelected ? 'ring-2 ring-blue-500' : ''}`}
                      onClick={() => os.setSelectedId?.(node.id)}
                    >
                      <div className="network-energy-device-info">
                        <OSIcon3D name={node.name} source={icon} size="sm" />
                        <div>
                          <strong>{node.name}</strong>
                          <span>{node.room || t(node.kind)}</span>
                        </div>
                      </div>
                      <div className="network-energy-bar-wrap">
                        <OSEnergyBar
                          label={node.name}
                          sublabel={node.room || t(node.kind)}
                          watts={power}
                          maxWatts={maxPower}
                          formattedValue={formattedValue}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {view === 'devices' && (
            <div className="network-device-grid">
              {filtered.map((node) => {
                const live = !isStale(node, Date.now()) && node.online !== false;
                const measuredPower = live && node.telemetry.powerWatts !== null;
                const isSelected = os.selectedId === node.id;

                return (
                  <article
                    className={`network-device cursor-pointer ${isSelected ? 'ring-2 ring-blue-500' : ''}`}
                    key={node.id}
                    onClick={() => os.setSelectedId?.(node.id)}
                  >
                    <header>
                      <OSIcon3D name={node.name} source={icon} size="md" />
                      <div>
                        <h2>{node.name}</h2>
                        <span>{node.room || t(node.kind)}</span>
                      </div>
                      <span className="network-node-status" data-live={live}>
                        {t(live ? 'online' : 'offline')}
                      </span>
                    </header>

                    <div className="network-node-metrics">
                      <div>
                        <span>{t('power')}</span>
                        <strong>{measuredPower ? `${format(node.telemetry.powerWatts!)} W` : t('not_measured')}</strong>
                      </div>
                      {technical && (
                        <>
                          <div>
                            <span>CPU</span>
                            <strong>
                              {node.telemetry.cpuPercent === null ? '—' : `${format(node.telemetry.cpuPercent)}%`}
                            </strong>
                          </div>
                          <div>
                            <span>RAM</span>
                            <strong>
                              {node.telemetry.ramUsedGb === null
                                ? '—'
                                : `${format(node.telemetry.ramUsedGb)} / ${format(node.telemetry.ramTotalGb || 0)} GB`}
                            </strong>
                          </div>
                        </>
                      )}
                    </div>

                    <footer>
                      <span className="network-device-kind-badge">{t(node.kind)}</span>
                      <div className="network-device-actions flex gap-1.5">
                        <button
                          type="button"
                          className="network-btn-manage"
                          onClick={(e) => {
                            e.stopPropagation();
                            os.openApp({
                              appId: 'node_apps/console',
                              targetNodeId: node.id,
                              initialPayload: { name: node.name, module: 'task_manager' },
                            });
                          }}
                        >
                          {t('task_manager')} →
                        </button>
                        <button
                          type="button"
                          className="network-btn-manage"
                          onClick={(e) => {
                            e.stopPropagation();
                            os.openApp({
                              appId: 'node_apps/console',
                              targetNodeId: node.id,
                              initialPayload: { name: node.name, module: 'connections' },
                            });
                          }}
                        >
                          {t('connections_center')} →
                        </button>
                        <button
                          type="button"
                          className="network-btn-manage"
                          onClick={(e) => {
                            e.stopPropagation();
                            os.openApp({
                              appId: 'node_apps/console',
                              targetNodeId: node.id,
                              initialPayload: { name: node.name },
                            });
                          }}
                        >
                          {t('manage')} →
                        </button>
                      </div>
                    </footer>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      }
    />
  );
};
