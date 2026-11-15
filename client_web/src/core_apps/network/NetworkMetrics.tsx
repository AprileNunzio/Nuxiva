import React from 'react';
import { MeshNeuron } from '../../features/neural_mesh/domain/types';

export interface MetricFormat {
  readonly format: (value: number, maxDigits?: number) => string;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

interface Tile {
  readonly id: string;
  readonly label: string;
  readonly value: string;
  readonly level: number | null;
}

function percent(value: number | null, format: MetricFormat['format']): string {
  return value === null ? '—' : `${format(value)}%`;
}

export function buildTiles(node: MeshNeuron, live: boolean, { format, t }: MetricFormat, isHost: boolean): Tile[] {
  const m = node.telemetry;
  const ram = m.ramUsedGb !== null && m.ramTotalGb ? m.ramUsedGb / m.ramTotalGb : null;
  const tiles: Tile[] = [
    { id: 'power', label: t('power'), value: live && m.powerWatts !== null ? `${format(m.powerWatts)} W` : '—', level: null },
    {
      id: 'latency',
      label: t('latency'),
      value: m.pingMs !== null ? `${format(m.pingMs, 0)} ms` : isHost ? t('local') : '—',
      level: null,
    },
    { id: 'cpu', label: 'CPU', value: percent(m.cpuPercent, format), level: m.cpuPercent === null ? null : m.cpuPercent / 100 },
    { id: 'gpu', label: 'GPU', value: percent(m.gpuPercent, format), level: m.gpuPercent === null ? null : m.gpuPercent / 100 },
    {
      id: 'ram',
      label: 'RAM',
      value: m.ramUsedGb === null ? '—' : `${format(m.ramUsedGb)} / ${format(m.ramTotalGb || 0)} GB`,
      level: ram,
    },
  ];
  if (m.batteryPercent !== null) {
    tiles.push({
      id: 'battery',
      label: t(m.charging ? 'battery_charging' : 'battery'),
      value: percent(m.batteryPercent, format),
      level: m.batteryPercent / 100,
    });
  }
  if (m.tempC !== null) {
    tiles.push({ id: 'temp', label: t('temperature'), value: `${format(m.tempC)} °C`, level: null });
  }
  return tiles;
}

interface NetworkMetricsProps extends MetricFormat {
  readonly node: MeshNeuron;
  readonly live: boolean;
  readonly isHost: boolean;
}

export const NetworkMetrics: React.FC<NetworkMetricsProps> = ({ node, live, isHost, format, t }) => (
  <dl className="network-metrics">
    {buildTiles(node, live, { format, t }, isHost).map((tile) => (
      <div key={tile.id} className="network-metric" data-id={tile.id}>
        <dt>{tile.label}</dt>
        <dd>{tile.value}</dd>
        {tile.level !== null && (
          <span className="network-metric-bar" aria-hidden="true">
            <span style={{ width: `${Math.round(Math.min(1, Math.max(0, tile.level)) * 100)}%` }} />
          </span>
        )}
      </div>
    ))}
  </dl>
);
