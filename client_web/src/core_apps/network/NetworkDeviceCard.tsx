import React from 'react';
import { OSIcon3D } from '../../app_shell/OSIcon3D';
import icon from './icon.png';
import { isStale } from '../../features/neural_mesh/domain/metrics';
import { MeshNeuron } from '../../features/neural_mesh/domain/types';
import { NetworkMetrics } from './NetworkMetrics';

interface NetworkDeviceCardProps {
  readonly node: MeshNeuron;
  readonly isSelected: boolean;
  readonly isNearest: boolean;
  readonly isHost: boolean;
  readonly format: (value: number, maxDigits?: number) => string;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly onSelect: (nodeId: string) => void;
  readonly onOpenConsole: (node: MeshNeuron, module?: string) => void;
}

export const NetworkDeviceCard: React.FC<NetworkDeviceCardProps> = ({
  node,
  isSelected,
  isNearest,
  isHost,
  format,
  t,
  onSelect,
  onOpenConsole,
}) => {
  const isLive = !isStale(node, Date.now()) && node.online !== false;

  return (
    <article className={`network-device ${isSelected ? 'is-selected' : ''}`} onClick={() => onSelect(node.id)}>
      <header>
        <OSIcon3D name={node.name} source={icon} size="md" />
        <div className="network-device-title-wrap">
          <h2>{node.name}</h2>
          <span>{node.room || t(node.kind)}</span>
        </div>
        {isNearest && <span className="network-nearest">{t('nearest_badge')}</span>}
        <span className="network-node-status" data-live={isLive}>
          {t(isLive ? 'online' : 'offline')}
        </span>
      </header>

      <NetworkMetrics node={node} live={isLive} isHost={isHost} format={format} t={t} />

      <footer>
        <span className="network-device-kind-badge">{t(node.kind)}</span>
        <div className="network-device-actions">
          <button
            type="button"
            className="network-btn network-btn-ghost"
            onClick={(e) => {
              e.stopPropagation();
              onOpenConsole(node, 'task_manager');
            }}
          >
            {t('task_manager')}
          </button>
          <button
            type="button"
            className="network-btn network-btn-ghost"
            onClick={(e) => {
              e.stopPropagation();
              onOpenConsole(node, 'connections');
            }}
          >
            {t('connections_center')}
          </button>
          <button
            type="button"
            className="network-btn network-btn-primary"
            onClick={(e) => {
              e.stopPropagation();
              onOpenConsole(node);
            }}
          >
            {t('manage')} →
          </button>
        </div>
      </footer>
    </article>
  );
};
