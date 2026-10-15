import React, { useState, useEffect, useRef, useMemo } from 'react';
import { MeshTopologyNode, MeshTopologyState } from '../shared/types';
import { TelemetryHUDCard } from './TelemetryHUDCard';
import { ParentBindingModal } from './ParentBindingModal';
import {
  Activity,
  Cpu,
  Server,
  Smartphone,
  Video,
  Mic,
  RefreshCw,
  Layers,
  Sparkles,
} from 'lucide-react';
import { useScopedI18n } from '../shared/i18n/useScopedI18n';

interface MeshTopologyCanvasProps {
  onOpenCoreControl: () => void;
  onOpenNodeControl: (node: { id: string; name: string; tier: string; ip: string }) => void;
}

export const MeshTopologyCanvas: React.FC<MeshTopologyCanvasProps> = ({
  onOpenCoreControl,
  onOpenNodeControl,
}) => {
  const { t } = useScopedI18n('mesh_canvas');
  const [nodes, setNodes] = useState<MeshTopologyNode[]>([]);
  const [hoveredNode, setHoveredNode] = useState<MeshTopologyNode | null>(null);
  const [bindingSatellite, setBindingSatellite] = useState<MeshTopologyNode | null>(null);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Caricamento telemetria reale da backend
  const fetchRealTopology = () => {
    fetch('/api/v5/mesh/topology')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch topology');
        return res.json();
      })
      .then((data: MeshTopologyState) => {
        if (data && data.nodes && data.nodes.length > 0) {
          setNodes(data.nodes);
          setHoveredNode((prev) => prev || data.nodes[0]);
        }
      })
      .catch((err) => {
        console.warn('Real topology fetch error', err);
      });
  };

  // WebSocket 2Hz telemetry stream
  useEffect(() => {
    fetchRealTopology();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v5/mesh/telemetry/stream`;

    const connectWs = () => {
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => setWsConnected(true);
        ws.onmessage = (event) => {
          try {
            const data: MeshTopologyState = JSON.parse(event.data);
            if (data.nodes && data.nodes.length > 0) {
              setNodes(data.nodes);
            }
          } catch {
            // ignore
          }
        };
        ws.onclose = () => {
          setWsConnected(false);
          setTimeout(connectWs, 3000);
        };
        ws.onerror = () => setWsConnected(false);
      } catch {
        setWsConnected(false);
      }
    };

    connectWs();

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const handleSaveBinding = async (
    satelliteId: string,
    parentId: string,
    streamType: string
  ) => {
    try {
      const targetParent = nodes.find((n) => n.id === parentId);
      await fetch('/api/v5/mesh/bind_parent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          satellite_id: satelliteId,
          parent_node_id: parentId,
          parent_ip: targetParent?.ip || '127.0.0.1',
          stream_type: streamType,
        }),
      });

      setNodes((prev) =>
        prev.map((n) => (n.id === satelliteId ? { ...n, parent_id: parentId } : n))
      );
    } catch {
      // handled
    }
  };

  // Separiamo i nodi satellite/compute dal Nucleo Centrale
  const satelliteNodes = useMemo(() => {
    return nodes.filter((n) => n.type !== 'core');
  }, [nodes]);

  // Calcolo dinamico posizioni spaziali dei nodi attorno al Nucleo Centrale
  const nodePositions = useMemo(() => {
    const total = satelliteNodes.length;
    const positions: Record<string, { cx: string; cy: string; xPct: number; yPct: number }> = {};

    satelliteNodes.forEach((node, idx) => {
      // Distribuzione su orbita ellittica
      const angle = total === 1 ? -Math.PI / 2 : (idx / total) * 2 * Math.PI - Math.PI / 2;
      const rx = 34; // percentuale orizzontale dal centro
      const ry = 28; // percentuale verticale dal centro
      const xPct = 50 + Math.cos(angle) * rx;
      const yPct = 46 + Math.sin(angle) * ry;

      positions[node.id] = {
        cx: `${xPct.toFixed(1)}%`,
        cy: `${yPct.toFixed(1)}%`,
        xPct,
        yPct,
      };
    });

    return positions;
  }, [satelliteNodes]);

  const getNodeIcon = (node: MeshTopologyNode) => {
    switch (node.type) {
      case 'compute':
        return <Server className="w-6 h-6 text-cyan-400" />;
      case 'satellite':
        return <Video className="w-5 h-5 text-emerald-400" />;
      case 'micro':
        return <Mic className="w-5 h-5 text-yellow-400" />;
      case 'mobile':
        return <Smartphone className="w-5 h-5 text-purple-400" />;
      default:
        return <Cpu className="w-5 h-5 text-cyan-400" />;
    }
  };

  return (
    <div className="relative w-full h-[calc(100vh-62px)] overflow-hidden bg-[#030712] select-none font-mono">
      {/* Background Cyber Starfield & Isometric Grid */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_40%,rgba(6,182,212,0.12),rgba(2,6,23,0.95))] pointer-events-none" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_46%,#000_70%,transparent_100%)] opacity-35 pointer-events-none" />

      {/* Top Banner Status & Instructions */}
      <div className="absolute top-4 left-6 z-20 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-slate-900/80 border border-cyan-500/40 backdrop-blur-md shadow-[0_0_20px_rgba(6,182,212,0.15)]">
          <div className={`w-2.5 h-2.5 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
          <span className="text-xs font-bold text-cyan-300 tracking-wider">
            PORT :8080 | MESH DECENTRALIZZATA
          </span>
        </div>
        <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 backdrop-blur-md">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          <span>Clicca sul Nucleo per i 24 Applicativi • Clicca sui Nodi per l'Hardware</span>
        </div>
      </div>

      {/* SVG Canvas for Dynamic Laser Energy Conduits */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none">
        <defs>
          <linearGradient id="coreBeam" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0.4" />
          </linearGradient>
          <filter id="laserGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Dynamic laser lines connecting Central Nucleus (50%, 46%) to each node */}
        {satelliteNodes.map((node) => {
          const pos = nodePositions[node.id];
          if (!pos) return null;

          return (
            <g key={`link-${node.id}`}>
              {/* Outer soft glow */}
              <line
                x1="50%"
                y1="46%"
                x2={pos.cx}
                y2={pos.cy}
                stroke="#00f0ff"
                strokeWidth="4"
                strokeOpacity="0.2"
                filter="url(#laserGlow)"
              />
              {/* Inner high-intensity laser conduit with animated pulses */}
              <line
                x1="50%"
                y1="46%"
                x2={pos.cx}
                y2={pos.cy}
                stroke="url(#coreBeam)"
                strokeWidth="2"
                strokeDasharray="8 6"
                className="animate-pulse"
              />
            </g>
          );
        })}
      </svg>

      {/* Central Interactive Nucleus (Virtual Core) */}
      <div
        style={{ left: '50%', top: '46%', transform: 'translate(-50%, -50%)' }}
        className="absolute z-10 flex flex-col items-center cursor-pointer group"
        onClick={onOpenCoreControl}
      >
        {/* Outer Rotating Holographic HUD Rings */}
        <div className="relative flex items-center justify-center">
          {/* Ring 1 - Outer segmented */}
          <div className="absolute w-44 h-44 sm:w-56 sm:h-56 rounded-full border border-cyan-500/20 border-dashed animate-spin [animation-duration:35s] pointer-events-none" />

          {/* Ring 2 - Inner counter-rotating */}
          <div className="absolute w-36 h-36 sm:w-48 sm:h-48 rounded-full border border-indigo-500/30 border-t-cyan-400 border-b-transparent animate-spin [animation-duration:20s] [animation-direction:reverse] pointer-events-none" />

          {/* Central Reactor Core Sphere */}
          <div className="relative w-28 h-28 sm:w-36 sm:h-36 rounded-full bg-slate-950/90 border-2 border-cyan-400/80 shadow-[0_0_60px_rgba(6,182,212,0.45)] flex flex-col items-center justify-center transition-all duration-300 group-hover:scale-110 group-hover:border-cyan-300 group-hover:shadow-[0_0_90px_rgba(6,182,212,0.7)]">
            <div className="absolute inset-0 rounded-full bg-radial from-cyan-400/20 via-transparent to-transparent pointer-events-none" />
            <Activity className="w-9 h-9 sm:w-11 sm:h-11 text-cyan-300 animate-pulse mb-1" />
            <span className="text-[11px] sm:text-xs font-bold text-white tracking-widest uppercase">
              NUCLEO
            </span>
            <span className="text-[9px] font-bold text-cyan-400 tracking-wider">
              CENTRALE
            </span>
            <div className="mt-1 px-2 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-800 text-[8px] text-cyan-300 uppercase font-semibold">
              CRDT VIRTUAL CORE
            </div>
          </div>
        </div>

        {/* Hover / Action Prompt */}
        <div className="mt-3 px-3 py-1 rounded-full bg-slate-900/80 border border-cyan-500/30 text-[10px] text-cyan-300 shadow-md group-hover:bg-cyan-500/20 group-hover:border-cyan-400 transition-all">
          Clicca per Aprire il Pannello Generale (24 App)
        </div>
      </div>

      {/* Orbiting Hardware Nodes */}
      {satelliteNodes.map((node) => {
        const pos = nodePositions[node.id];
        if (!pos) return null;
        const isHovered = hoveredNode?.id === node.id;

        return (
          <div
            key={node.id}
            style={{ left: pos.cx, top: pos.cy, transform: 'translate(-50%, -50%)' }}
            className="absolute z-10 cursor-pointer transition-all duration-300"
            onMouseEnter={() => setHoveredNode(node)}
            onClick={() => {
              onOpenNodeControl({
                id: node.id,
                name: node.name,
                tier: node.tier,
                ip: node.ip,
              });
            }}
          >
            <div
              className={`group relative flex flex-col items-center justify-center p-3 sm:p-4 rounded-2xl bg-slate-900/90 backdrop-blur-xl border transition-all duration-300 min-w-[120px] sm:min-w-[140px] shadow-lg ${
                isHovered
                  ? 'border-cyan-400 shadow-[0_0_35px_rgba(6,182,212,0.4)] scale-110 ring-2 ring-cyan-400/60'
                  : 'border-slate-800 hover:border-cyan-500/60 hover:scale-105'
              }`}
            >
              {/* Online beacon dot */}
              <div className="absolute top-2.5 right-2.5 flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              </div>

              {/* Hardware Icon */}
              <div className="p-2 rounded-xl bg-slate-950/80 border border-slate-800 mb-2 group-hover:border-cyan-500/40">
                {getNodeIcon(node)}
              </div>

              {/* Node Name */}
              <span className="font-bold text-xs text-white text-center truncate max-w-[120px]">
                {node.name}
              </span>

              {/* Node IP */}
              <span className="text-[10px] text-cyan-400/90 font-mono mt-0.5">
                {node.ip}
              </span>

              {/* Tier badge */}
              <span className="mt-1.5 text-[8px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-cyan-950/60 text-cyan-300 border border-cyan-800/80">
                {node.tier.split(' ')[0]}
              </span>

              {/* Click prompt */}
              <span className="text-[8px] text-slate-500 group-hover:text-cyan-300 transition-colors mt-1">
                Gestisci Hardware →
              </span>
            </div>
          </div>
        );
      })}

      {/* Floating Holographic Telemetry HUD Card in bottom-left */}
      {hoveredNode && (
        <div className="absolute bottom-6 left-6 z-30">
          <TelemetryHUDCard
            node={hoveredNode}
            onOpenNodeControl={(nodeId) => {
              const target = nodes.find((n) => n.id === nodeId);
              if (target) {
                onOpenNodeControl({
                  id: target.id,
                  name: target.name,
                  tier: target.tier,
                  ip: target.ip,
                });
              }
            }}
            onOpenCoreControl={onOpenCoreControl}
          />
        </div>
      )}

      {/* Parent Binding Modal */}
      {bindingSatellite && (
        <ParentBindingModal
          satellite={bindingSatellite}
          availableParents={nodes.filter((n) => n.type === 'compute')}
          onClose={() => setBindingSatellite(null)}
          onSaveBinding={handleSaveBinding}
        />
      )}
    </div>
  );
};
