import React from 'react';
import { OSIcon3D } from '../../app_shell/OSIcon3D';
import icon from './icon.png';
import { isStale } from '../../features/neural_mesh/domain/metrics';
import { OSEnergyBar, OSSectionHeader } from '../shared/kit';
import { MeshNeuron } from '../../features/neural_mesh/domain/types';

interface NetworkEnergyViewProps {
  readonly nodes: readonly MeshNeuron[];
  readonly maxPower: number;
  readonly selectedId?: string;
  readonly format: (value: number, maxDigits?: number) => string;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly onSelect: (nodeId: string) => void;
}

export const NetworkEnergyView: React.FC<NetworkEnergyViewProps> = ({
  nodes,
  maxPower,
  selectedId,
  format,
  t,
  onSelect,
}) => (
  <div className="network-energy-section">
    <OSSectionHeader title={t('energy')} description={t('energy_note')} />
    <div className="network-energy-list">
      {nodes.map((node) => {
        const live = !isStale(node, Date.now()) && node.online !== false;
        const power = live && node.telemetry.powerWatts !== null ? node.telemetry.powerWatts : 0;
        const formattedValue = live && node.telemetry.powerWatts !== null ? `${format(power)} W` : t('not_measured');
        const isSelected = selectedId === node.id;

        return (
          <div
            key={node.id}
            className={`network-energy-row cursor-pointer transition ${isSelected ? 'is-selected' : ''}`}
            onClick={() => onSelect(node.id)}
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
);
