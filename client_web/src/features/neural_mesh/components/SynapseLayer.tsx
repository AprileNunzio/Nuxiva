import React from 'react';
import { toSvgPath } from '../domain/geometry';
import { KIND_COLORS } from '../domain/palette';
import { MeshLayout } from '../domain/types';

interface SynapseLayerProps {
  readonly layout: MeshLayout;
  readonly width: number;
  readonly height: number;
  readonly activeId: string | null;
}

export const SynapseLayer: React.FC<SynapseLayerProps> = ({ layout, width, height, activeId }) => (
  <svg className="pointer-events-none absolute inset-0" width={width} height={height} aria-hidden="true">
    <defs>
      <filter id="nm-synapse-glow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="2.6" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    </defs>
    {layout.synapses.map((synapse) => {
      const d = toSvgPath(synapse);
      const color = KIND_COLORS[synapse.kind];
      const active = activeId !== null && (synapse.targetId === activeId || synapse.sourceId === activeId);
      return (
        <g key={synapse.id}>
          <path
            d={d}
            fill="none"
            stroke={color}
            strokeOpacity={active ? 0.6 : 0.16}
            strokeWidth={active ? 2.6 : 1.4}
            filter={active ? 'url(#nm-synapse-glow)' : undefined}
          />
          <path
            d={d}
            fill="none"
            stroke={color}
            strokeOpacity={active ? 0.95 : 0.45}
            strokeWidth={1.3}
            strokeLinecap="round"
            className="nm-flow"
          />
        </g>
      );
    })}
  </svg>
);
