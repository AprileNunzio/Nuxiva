import React, { useState, useEffect, useRef } from 'react';
import { MeshTopologyNode, MeshTopologyLink, MeshTopologyState } from '../shared/types';
import { TelemetryHUDCard } from './TelemetryHUDCard';
import { ParentBindingModal } from './ParentBindingModal';
import { Activity, Shield, Cpu, Wifi, Radio, Server, Smartphone, Video, Mic, RefreshCw, Link2 } from 'lucide-react';
import { useScopedI18n } from '../shared/i18n/useScopedI18n';

interface MeshTopologyCanvasProps {
  onOpenCoreControl: () => void;
  onOpenNodeControl: (nodeId: string) => void;
}

export const MeshTopologyCanvas: React.FC<MeshTopologyCanvasProps> = ({
  onOpenCoreControl,
  onOpenNodeControl,
}) => {
  const { t } = useScopedI18n('mesh_canvas');
  const [nodes, setNodes] = useState<MeshTopologyNode[]>([]);
  const [links, setLinks] = useState<MeshTopologyLink[]>([]);
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
        if (data && data.links) {
          setLinks(data.links);
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

        ws.onopen = () => {
          setWsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data: MeshTopologyState = JSON.parse(event.data);
            if (data.nodes && data.nodes.length > 0) {
              setNodes(data.nodes);
            }
            if (data.links && data.links.length > 0) {
              setLinks(data.links);
            }
          } catch {
            // ignore json parse error
          }
        };

        ws.onclose = () => {
          setWsConnected(false);
          setTimeout(connectWs, 3000);
        };

        ws.onerror = () => {
          setWsConnected(false);
        };
      } catch {
        setWsConnected(false);
      }
    };

    connectWs();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
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

      // Update local state
      setNodes((prev) =>
        prev.map((n) => (n.id === satelliteId ? { ...n, parent_id: parentId } : n))
      );
    } catch {
      // handled
    }
  };

  // Posizioni topologiche fisse/bilanciate per rendering visivo spaziale
  const getNodePosition = (node: MeshTopologyNode, index: number, total: number) => {
    if (node.type === 'core') {
      return { cx: '50%', cy: '48%' };
    }
    if (node.id === 'node-pc-i9') {
      return { cx: '25%', cy: '36%' };
    }
    if (node.id === 'node-mini-pc') {
      return { cx: '75%', cy: '36%' };
    }
    if (node.id === 'sat-rpi-cam') {
      return { cx: '14%', cy: '68%' };
    }
    if (node.id === 'sat-esp32-audio') {
      return { cx: '34%', cy: '74%' };
    }
    if (node.id === 'sat-mobile-nunzio') {
      return { cx: '86%', cy: '68%' };
    }
    const angle = (index / total) * 2 * Math.PI;
    const r = 240;
    return { cx: `calc(50% + ${Math.cos(angle) * r}px)`, cy: `calc(48% + ${Math.sin(angle) * r}px)` };
  };

  const getNodeIcon = (node: MeshTopologyNode) => {
    switch (node.type) {
      case 'core':
        return <Activity className="w-8 h-8 text-cyan-300 animate-pulse" />;
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
    <div className="relative w-full h-[calc(100vh-68px)] overflow-hidden bg-[#030712] select-none">
      {/* Background radial cosmic grid */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(14,165,233,0.15),rgba(255,255,255,0))] pointer-events-none" />
      <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:32px_32px] opacity-25 pointer-events-none" />

      {/* Top Banner Status */}
      <div className="absolute top-4 left-6 z-20 flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/80 border border-cyan-500/30 backdrop-blur-md">
          <div className={`w-2.5 h-2.5 rounded-full ${wsConnected ? 'bg-emerald-400 animate-ping' : 'bg-yellow-400'}`} />
          <span className="text-xs font-mono font-bold text-cyan-300 tracking-wider">
            PORT :8080 | MESH DECENTRALIZZATA
          </span>
        </div>
        <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/60 border border-slate-800 text-[11px] font-mono text-slate-400">
          <Link2 className="w-3.5 h-3.5 text-cyan-400" />
          <span>{t('drag_drop_hint')}</span>
        </div>
      </div>

      {/* SVG Canvas for Topological Lines & Links */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none">
        <defs>
          <linearGradient id="crdtGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.3" />
          </linearGradient>
          <linearGradient id="p2pGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#00f0ff" stopOpacity="0.4" />
          </linearGradient>
        </defs>

        {/* Dynamic connection lines */}
        <line x1="50%" y1="48%" x2="25%" y2="36%" stroke="url(#crdtGrad)" strokeWidth="2.5" strokeDasharray="6 4" />
        <line x1="50%" y1="48%" x2="75%" y2="36%" stroke="url(#crdtGrad)" strokeWidth="2.5" strokeDasharray="6 4" />
        <line x1="25%" y1="36%" x2="14%" y2="68%" stroke="url(#p2pGrad)" strokeWidth="2.5" />
        <line x1="25%" y1="36%" x2="34%" y2="74%" stroke="url(#p2pGrad)" strokeWidth="2.5" />
        <line x1="25%" y1="36%" x2="86%" y2="68%" stroke="#a855f7" strokeWidth="2" strokeDasharray="4 4" />
      </svg>

      {/* Interactive Graph Nodes */}
      <div className="absolute inset-0 w-full h-full pointer-events-auto">
        {nodes.map((node, index) => {
          const pos = getNodePosition(node, index, nodes.length);
          const isCore = node.type === 'core';
          const isHovered = hoveredNode?.id === node.id;

          return (
            <div
              key={node.id}
              style={{ left: pos.cx, top: pos.cy, transform: 'translate(-50%, -50%)' }}
              className="absolute cursor-pointer transition-all duration-300"
              onMouseEnter={() => setHoveredNode(node)}
              onClick={() => {
                if (isCore) {
                  onOpenCoreControl();
                } else {
                  onOpenNodeControl(node.id);
                }
              }}
            >
              <div
                className={`group relative flex flex-col items-center justify-center transition-all duration-300 ${
                  isCore
                    ? 'w-28 h-28 md:w-36 md:h-36 rounded-full bg-slate-950/90 border-2 border-cyan-400 shadow-[0_0_50px_rgba(0,240,255,0.5)] hover:scale-105'
                    : 'w-20 h-20 md:w-24 md:h-24 rounded-2xl bg-slate-900/90 border border-cyan-500/40 hover:border-cyan-300 shadow-lg hover:shadow-[0_0_25px_rgba(0,240,255,0.4)] hover:scale-110'
                } ${isHovered ? 'ring-2 ring-cyan-400 ring-offset-2 ring-offset-slate-950' : ''}`}
              >
                {/* Node icon */}
                {getNodeIcon(node)}

                {/* Node Label */}
                <span
                  className={`mt-1 font-mono font-bold text-center px-1 text-white tracking-wider ${
                    isCore ? 'text-xs md:text-sm text-cyan-300' : 'text-[10px] md:text-xs'
                  }`}
                >
                  {node.name}
                </span>

                {/* Node IP / Badge */}
                <span className="text-[9px] font-mono text-cyan-400/80">
                  {node.ip}
                </span>

                {/* Badges */}
                {node.is_remote_vpn && (
                  <span className="absolute -top-2 px-1.5 py-0.5 rounded-full bg-purple-600 text-[8px] font-bold text-white shadow">
                    REMOTE-VPN
                  </span>
                )}

                {node.type === 'satellite' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setBindingSatellite(node);
                    }}
                    title="Parent Binding"
                    className="absolute -bottom-2 px-1.5 py-0.5 rounded-md bg-emerald-700 hover:bg-emerald-600 text-[8px] font-mono text-white opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    P2P BIND
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Floating Hover Telemetry Card (Top Right / FIG 5.1) */}
      {hoveredNode && (
        <div className="absolute top-4 right-6 z-30">
          <TelemetryHUDCard
            node={hoveredNode}
            onOpenNodeControl={onOpenNodeControl}
            onOpenCoreControl={onOpenCoreControl}
          />
        </div>
      )}

      {/* Parent Binding Modal */}
      {bindingSatellite && (
        <ParentBindingModal
          satellite={bindingSatellite}
          availableParents={nodes}
          onClose={() => setBindingSatellite(null)}
          onSaveBinding={handleSaveBinding}
        />
      )}
    </div>
  );
};
