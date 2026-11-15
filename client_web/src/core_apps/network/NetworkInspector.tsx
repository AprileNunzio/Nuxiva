import React from 'react';
import { OSIcon3D } from '../../app_shell/OSIcon3D';
import icon from './icon.png';
import { isStale } from '../../features/neural_mesh/domain/metrics';
import { OSInspector } from '../shared/kit';
import { MeshNeuron } from '../../features/neural_mesh/domain/types';
import { NetworkMetrics } from './NetworkMetrics';

export interface MCPInsightState {
  readonly loading: boolean;
  readonly text?: string;
  readonly error?: string;
}

interface NetworkInspectorProps {
  readonly selectedNode: MeshNeuron | null;
  readonly studyingNodeId: string | null;
  readonly mcpInsights: Record<string, MCPInsightState>;
  readonly onClose: () => void;
  readonly onOpenConsole: (node: MeshNeuron, module?: string) => void;
  readonly onAskMCP: (nodeId: string, address: string) => void;
  readonly onStudy: (nodeId: string, address: string) => void;
  readonly format: (value: number, maxDigits?: number) => string;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

export const NetworkInspector: React.FC<NetworkInspectorProps> = ({
  selectedNode,
  studyingNodeId,
  mcpInsights,
  onClose,
  onOpenConsole,
  onAskMCP,
  onStudy,
  format,
  t,
}) => {
  if (!selectedNode) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center text-on-surface-variant">
        <OSIcon3D name="Preview" source={icon} size="md" />
        <p className="mt-3 text-xs font-semibold text-on-surface">{t('devices')}</p>
        <span className="mt-1 text-[11px]">
          {t('description')}
        </span>
      </div>
    );
  }

  const isLive = !isStale(selectedNode, Date.now()) && selectedNode.online !== false;
  const nodeInsight = mcpInsights[selectedNode.id];
  const address = selectedNode.ip || selectedNode.name;

  return (
    <OSInspector
      title={selectedNode.name}
      subtitle={`${selectedNode.room || t(selectedNode.kind)} · ${selectedNode.ip || '—'}`}
      onClose={onClose}
      actions={
        <div className="network-inspector-actions">
          <button type="button" className="network-btn network-btn-primary network-btn-block" onClick={() => onOpenConsole(selectedNode)}>
            {t('manage')} →
          </button>
          <button type="button" className="network-btn network-btn-soft network-btn-block" onClick={() => onOpenConsole(selectedNode, 'task_manager')}>
            {t('task_manager')} →
          </button>
          <button type="button" className="network-btn network-btn-soft network-btn-block" onClick={() => onOpenConsole(selectedNode, 'connections')}>
            {t('connections_center')} →
          </button>
          <div className="network-inspector-pair">
            <button type="button" className="network-btn network-btn-ghost" onClick={() => onAskMCP(selectedNode.id, address)}>
              {t('mcp_whois')}
            </button>
            <button
              type="button"
              className="network-btn network-btn-ghost"
              disabled={studyingNodeId === selectedNode.id}
              onClick={() => onStudy(selectedNode.id, selectedNode.ip || selectedNode.id)}
            >
              {studyingNodeId === selectedNode.id ? '…' : t('device_study')}
            </button>
          </div>
        </div>
      }
    >
      <div className="network-inspector">
        <div className="network-inspector-head">
          <OSIcon3D name={selectedNode.name} source={icon} size="md" />
          <div>
            <strong>{selectedNode.name}</strong>
            <span>{t(selectedNode.kind)}</span>
          </div>
          <span className="network-node-status" data-live={isLive}>
            {isLive ? t('online') : t('offline')}
          </span>
        </div>

        <NetworkMetrics node={selectedNode} live={isLive} isHost={selectedNode.local} format={format} t={t} />

        <section className="network-inspector-section">
          <h3>{t('technical')}</h3>
          <dl>
            <div><dt>{t('address')}</dt><dd className="font-mono">{selectedNode.ip || '—'}</dd></div>
            <div><dt>{t('platform')}</dt><dd>{selectedNode.telemetry.os || '—'}</dd></div>
            <div><dt>{t('node_id')}</dt><dd className="font-mono">{selectedNode.id}</dd></div>
            {selectedNode.telemetry.uptimeSeconds !== null && (
              <div><dt>{t('uptime')}</dt><dd>{format(selectedNode.telemetry.uptimeSeconds / 3600)} h</dd></div>
            )}
          </dl>
        </section>

        {nodeInsight && (
          <section className="network-inspector-section">
            <h3>{t('mcp_insight')}</h3>
            {nodeInsight.loading && <p>{t('scanning')}</p>}
            {nodeInsight.error && <p className="network-error">{nodeInsight.error}</p>}
            {nodeInsight.text && <p className="network-insight-text">{nodeInsight.text}</p>}
          </section>
        )}
      </div>
    </OSInspector>
  );
};
