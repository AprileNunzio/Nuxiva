import React from 'react';
import { OSIcon3D } from '../../app_shell/OSIcon3D';
import icon from './icon.png';
import { isStale } from '../../features/neural_mesh/domain/metrics';
import { MeshNeuron } from '../../features/neural_mesh/domain/types';

interface NetworkDeviceCardProps {
  readonly node: MeshNeuron;
  readonly isSelected: boolean;
  readonly technical: boolean;
  readonly format: (value: number, maxDigits?: number) => string;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly onSelect: (nodeId: string) => void;
  readonly onOpenConsole: (node: MeshNeuron, module?: string) => void;
}

export const NetworkDeviceCard: React.FC<NetworkDeviceCardProps> = ({
  node,
  isSelected,
  technical,
  format,
  t,
  onSelect,
  onOpenConsole,
}) => {
  const isLive = !isStale(node, Date.now()) && node.online !== false;
  const measuredPower = isLive && node.telemetry.powerWatts !== null;

  return (
    <article
      className={`network-device cursor-pointer ${isSelected ? 'is-selected' : ''}`}
      onClick={() => onSelect(node.id)}
    >
      <header>
        <OSIcon3D name={node.name} source={icon} size="md" />
        <div className="network-device-title-wrap">
          <h2>{node.name}</h2>
          <span>{node.room || t(node.kind)}</span>
        </div>
        <span className="network-node-status" data-live={isLive}>
          {t(isLive ? 'online' : 'offline')}
        </span>
      </header>

      <div className="network-node-metrics">
        <div>
          <span>{t('power')}</span>
          <strong>{measuredPower ? `${format(node.telemetry.powerWatts ?? 0)} W` : t('not_measured')}</strong>
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
        <div className="network-device-actions">
          <button
            type="button"
            className="network-btn-action"
            onClick={(e) => {
              e.stopPropagation();
              onOpenConsole(node, 'task_manager');
            }}
          >
            {t('task_manager')}
          </button>
          <button
            type="button"
            className="network-btn-action"
            onClick={(e) => {
              e.stopPropagation();
              onOpenConsole(node, 'connections');
            }}
          >
            {t('connections_center')}
          </button>
          <button
            type="button"
            className="network-btn-primary"
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
