import React, { useState } from 'react';
import { useScopedI18n } from '../shared/i18n/useScopedI18n';
import { 
  Cpu, Volume2, Mic, Camera, Printer, Bluetooth, 
  Monitor, Edit3, Smartphone, ArrowLeft, RefreshCw, 
  Sliders, ShieldCheck, Activity, Wifi
} from 'lucide-react';

import BrainView from './brain';
import AudioView from './audio';
import MicView from './mic';
import CameraView from './camera';
import PrintersView from './printers';
import BluetoothView from './bluetooth';
import DisplayView from './display';
import WhiteboardView from './whiteboard';
import ClientLinkView from './client_link';

interface NodeDetailProps {
  nodeId: string;
  nodeName?: string;
  nodeTier?: string;
  ipAddress?: string;
  onBack?: () => void;
}

export const NodeDetailView: React.FC<NodeDetailProps> = ({
  nodeId,
  nodeName = 'Node-01',
  nodeTier = 'Tier-2 Satellite',
  ipAddress = '192.168.1.15',
  onBack,
}) => {
  const { t } = useScopedI18n('node_apps');
  const [activeTab, setActiveTab] = useState<string>('brain');
  const [isRebooting, setIsRebooting] = useState(false);

  const modules = [
    { id: 'brain', icon: Cpu, label: 'Brain', component: BrainView },
    { id: 'audio', icon: Volume2, label: 'Audio', component: AudioView },
    { id: 'mic', icon: Mic, label: 'Mic', component: MicView },
    { id: 'camera', icon: Camera, label: 'Camera', component: CameraView },
    { id: 'printers', icon: Printer, label: 'Printers', component: PrintersView },
    { id: 'bluetooth', icon: Bluetooth, label: 'Bluetooth', component: BluetoothView },
    { id: 'display', icon: Monitor, label: 'Display', component: DisplayView },
    { id: 'whiteboard', icon: Edit3, label: 'Whiteboard', component: WhiteboardView },
    { id: 'client_link', icon: Smartphone, label: 'Client Link', component: ClientLinkView },
  ];

  const CurrentComponent = modules.find((m) => m.id === activeTab)?.component || BrainView;

  const handleReboot = async () => {
    if (window.confirm(t('reboot_confirm') || 'Reboot node?')) {
      setIsRebooting(true);
      try {
        await fetch(`/api/v5/nodes/${nodeId}/reboot`, { method: 'POST' });
      } catch (err) {
        console.error('Reboot request error', err);
      }
      setTimeout(() => setIsRebooting(false), 3000);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#030712] text-slate-100 font-mono p-6 overflow-y-auto">
      {/* Top Bar Navigation & Node Summary */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
        <div className="flex items-center gap-4">
          {onBack && (
            <button
              onClick={onBack}
              className="p-2 rounded-lg bg-slate-900 border border-slate-800 hover:border-cyan-500 text-slate-400 hover:text-cyan-400 transition"
              title={t('back_to_canvas')}
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
          )}
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight text-white">{nodeName}</h1>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                {nodeTier}
              </span>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                ONLINE
              </span>
            </div>
            <div className="text-xs text-slate-400 mt-1 flex items-center gap-4">
              <span>Node ID: <code className="text-slate-300">{nodeId}</code></span>
              <span>IP: <code className="text-slate-300">{ipAddress}</code></span>
              <span className="flex items-center gap-1 text-slate-400">
                <Wifi className="w-3.5 h-3.5 text-cyan-400" /> P2P Zero-Bottleneck
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleReboot}
            disabled={isRebooting}
            className="flex items-center gap-2 px-3.5 py-2 bg-slate-900 border border-slate-800 hover:border-rose-500/60 hover:text-rose-400 text-xs font-semibold rounded-lg text-slate-300 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRebooting ? 'animate-spin text-rose-400' : ''}`} />
            {t('reboot_node')}
          </button>
        </div>
      </div>

      {/* Real-Time Telemetry Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <div className="bg-slate-900/60 border border-slate-800/80 p-3.5 rounded-xl">
          <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            {t('cpu_load')}
          </div>
          <div className="text-lg font-bold text-cyan-300 mt-1">14.2%</div>
        </div>
        <div className="bg-slate-900/60 border border-slate-800/80 p-3.5 rounded-xl">
          <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-purple-400" />
            {t('ram_usage')}
          </div>
          <div className="text-lg font-bold text-purple-300 mt-1">1.8 / 4.0 GB</div>
        </div>
        <div className="bg-slate-900/60 border border-slate-800/80 p-3.5 rounded-xl">
          <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <Sliders className="w-3.5 h-3.5 text-amber-400" />
            {t('temperature')}
          </div>
          <div className="text-lg font-bold text-amber-300 mt-1">42.8 °C</div>
        </div>
        <div className="bg-slate-900/60 border border-slate-800/80 p-3.5 rounded-xl">
          <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            {t('latency')}
          </div>
          <div className="text-lg font-bold text-emerald-300 mt-1">2.4 ms</div>
        </div>
      </div>

      {/* Node Plane Module Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800/80 pb-3 mb-6 overflow-x-auto">
        {modules.map((m) => {
          const Icon = m.icon;
          const isSelected = activeTab === m.id;
          return (
            <button
              key={m.id}
              onClick={() => setActiveTab(m.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition ${
                isSelected
                  ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/40 shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                  : 'bg-slate-900/50 text-slate-400 border border-slate-800/60 hover:text-slate-200 hover:border-slate-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {m.label}
            </button>
          );
        })}
      </div>

      {/* Active Hardware Module View */}
      <div className="flex-1">
        <CurrentComponent nodeId={nodeId} />
      </div>
    </div>
  );
};

export default NodeDetailView;
