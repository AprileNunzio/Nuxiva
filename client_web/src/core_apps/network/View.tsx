import React, { useCallback, useEffect, useState } from 'react';
import { useWindowTopology } from '../../app_shell/WindowTopology';
import { useOSApp, useWindowToolbar } from '../../app_shell/window_manager/WindowContext';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { isStale } from '../../features/neural_mesh/domain/metrics';
import { Loading, Empty, OSAppLayout, OSSidebar } from '../shared/kit';
import { triggerNetworkScan, queryWhoIsMCP, studyDevice } from './api';
import { NetworkDeviceCard } from './NetworkDeviceCard';
import { NetworkEnergyView } from './NetworkEnergyView';
import { NetworkInspector, MCPInsightState } from './NetworkInspector';
import { MeshNeuron } from '../../features/neural_mesh/domain/types';
import './style.css';

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

  const selectedNode = nodes.find((n) => n.id === os.selectedId) || null;

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
        [nodeId]: { loading: false, text: response || 'Nessuna informazione registrata.' },
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
    } finally {
      setTimeout(() => setStudyingNodeId(null), 1500);
    }
  };

  const handleOpenConsole = (node: MeshNeuron, module?: string) => {
    os.openApp({
      appId: 'node_apps/console',
      targetNodeId: node.id,
      initialPayload: { name: node.name, ...(module ? { module } : {}) },
    });
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
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{t('view')}</span>
            <div className="flex rounded-xl border border-slate-200/80 dark:border-slate-800/80 p-0.5 bg-slate-100/70 dark:bg-slate-900/70">
              <button
                type="button"
                className={`flex-1 rounded-lg py-1.5 text-xs font-medium transition ${
                  view === 'devices'
                    ? 'bg-white dark:bg-slate-800 text-blue-600 dark:text-blue-400 font-semibold shadow-xs'
                    : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                }`}
                onClick={() => setView('devices')}
              >
                {t('devices')}
              </button>
              <button
                type="button"
                className={`flex-1 rounded-lg py-1.5 text-xs font-medium transition ${
                  view === 'energy'
                    ? 'bg-white dark:bg-slate-800 text-blue-600 dark:text-blue-400 font-semibold shadow-xs'
                    : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
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

  const inspector = (
    <NetworkInspector
      selectedNode={selectedNode}
      studyingNodeId={studyingNodeId}
      mcpInsights={mcpInsights}
      onClose={() => os.setSelectedId?.(undefined)}
      onOpenConsole={handleOpenConsole}
      onAskMCP={(id, addr) => void handleAskMCP(id, addr)}
      onStudy={(id, addr) => void handleStudy(id, addr)}
      format={format}
      t={t}
    />
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
            <NetworkEnergyView
              nodes={filtered}
              maxPower={maxPower}
              selectedId={os.selectedId}
              format={format}
              t={t}
              onSelect={(id) => os.setSelectedId?.(id)}
            />
          )}

          {view === 'devices' && (
            <div className="network-device-grid">
              {filtered.map((node) => (
                <NetworkDeviceCard
                  key={node.id}
                  node={node}
                  isSelected={os.selectedId === node.id}
                  technical={technical}
                  format={format}
                  t={t}
                  onSelect={(id) => os.setSelectedId?.(id)}
                  onOpenConsole={handleOpenConsole}
                />
              ))}
            </div>
          )}
        </div>
      }
    />
  );
};
