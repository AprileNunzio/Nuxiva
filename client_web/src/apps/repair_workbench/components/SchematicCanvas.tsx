import React from 'react';
import { CircuitBoard, Zap } from 'lucide-react';
import type { CircuitSpec } from '../types';

interface SchematicCanvasProps {
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly circuit: CircuitSpec;
  readonly expectedVoltages: Record<string, number>;
}

export const SchematicCanvas: React.FC<SchematicCanvasProps> = ({
  t,
  circuit,
  expectedVoltages,
}) => {
  const components = circuit.components;
  const nets = circuit.nets;
  const voltages = Object.entries(expectedVoltages);

  if (components.length === 0 && nets.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-800 p-6 text-center text-xs text-slate-400">
        <CircuitBoard className="h-8 w-8 text-slate-600" aria-hidden="true" />
        <p>{t('schematic_empty')}</p>
      </div>
    );
  }

  const cols = Math.max(2, Math.ceil(Math.sqrt(components.length)));
  const svgWidth = Math.max(480, cols * 160);
  const rows = Math.max(1, Math.ceil(components.length / cols));
  const svgHeight = Math.max(260, rows * 110 + 40);

  const posMap = new Map<string, { x: number; y: number }>();
  components.forEach((comp, idx) => {
    const col = idx % cols;
    const row = Math.floor(idx / cols);
    posMap.set(comp.ref, { x: 80 + col * 150, y: 60 + row * 100 });
  });

  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950 p-2">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="h-64 w-full min-w-[24rem]"
          role="img"
          aria-label={t('schematic_title')}
        >
          {nets.map((net) => {
            const pts = net.connections
              .map((c) => posMap.get(c.ref))
              .filter((p): p is { x: number; y: number } => p !== undefined);
            if (pts.length < 2) return null;
            return pts.slice(1).map((target, idx) => (
              <g key={`${net.name}-${idx}`}>
                <line
                  x1={pts[0].x}
                  y1={pts[0].y}
                  x2={target.x}
                  y2={target.y}
                  stroke="#06b6d4"
                  strokeWidth={1.8}
                  strokeDasharray="4 2"
                />
                <text
                  x={(pts[0].x + target.x) / 2}
                  y={(pts[0].y + target.y) / 2 - 4}
                  fill="#67e8f9"
                  fontSize="10"
                  textAnchor="middle"
                >
                  {net.name}
                </text>
              </g>
            ));
          })}

          {components.map((comp) => {
            const pos = posMap.get(comp.ref) || { x: 60, y: 60 };
            return (
              <g key={comp.ref} transform={`translate(${pos.x - 45}, ${pos.y - 22})`}>
                <rect
                  width={90}
                  height={44}
                  rx={8}
                  fill="#0f172a"
                  stroke="#38bdf8"
                  strokeWidth={1.5}
                />
                <text x={45} y={18} fill="#f8fafc" fontSize="11" fontWeight="bold" textAnchor="middle">
                  {comp.ref}
                </text>
                <text x={45} y={33} fill="#94a3b8" fontSize="9.5" textAnchor="middle">
                  {(comp.value || comp.category).slice(0, 14)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {voltages.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-2.5 text-xs">
          <div className="mb-1.5 flex items-center gap-1.5 font-semibold text-amber-300">
            <Zap className="h-3.5 w-3.5" aria-hidden="true" />
            <span>{t('schematic_dc_solver')}</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {voltages.map(([node, val]) => (
              <span
                key={node}
                className="rounded-md border border-amber-500/30 bg-amber-950/50 px-2 py-0.5 font-mono text-[11px] text-amber-200"
              >
                {node}: {val}V
              </span>
            ))}
          </div>
        </div>
      )}

      {nets.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-2.5 text-xs">
          <h4 className="mb-1.5 font-semibold text-slate-300">{t('schematic_nets')}</h4>
          <div className="flex flex-col gap-1">
            {nets.map((net) => (
              <div key={net.name} className="flex flex-wrap items-center gap-1 text-[11px]">
                <span className="font-mono font-semibold text-cyan-300">{net.name}:</span>
                <span className="text-slate-400">
                  {net.connections.map((c) => `${c.ref}.${c.pin}`).join(' ↔ ')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
