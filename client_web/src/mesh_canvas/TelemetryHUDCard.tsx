import React from 'react';
import { MeshTopologyNode } from '../shared/types';
import { Activity, Cpu, HardDrive, Zap, Thermometer, Radio, ArrowRight, ShieldCheck, Wifi } from 'lucide-react';
import { useScopedI18n } from '../shared/i18n/useScopedI18n';

interface TelemetryHUDCardProps {
  node: MeshTopologyNode;
  onOpenNodeControl: (nodeId: string) => void;
  onOpenCoreControl?: () => void;
}

export const TelemetryHUDCard: React.FC<TelemetryHUDCardProps> = ({
  node,
  onOpenNodeControl,
  onOpenCoreControl,
}) => {
  const { t } = useScopedI18n('mesh_canvas');
  const telem = node.telemetry as Record<string, any>;
  const isCore = node.type === 'core';

  return (
    <div className="w-96 backdrop-blur-2xl bg-slate-950/90 border border-cyan-500/40 rounded-2xl p-5 shadow-[0_0_30px_rgba(0,240,255,0.25)] text-slate-100 flex flex-col gap-3 font-mono text-xs animate-in fade-in zoom-in-95 duration-200">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-cyan-900/60 pb-2.5">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />
          <span className="font-bold uppercase tracking-wider text-cyan-300">
            {t('hover_title')}: {node.name}
          </span>
        </div>
        {node.is_remote_vpn && (
          <span className="px-2 py-0.5 rounded-full bg-purple-500/20 border border-purple-500/40 text-purple-300 text-[10px] font-bold">
            {t('remote_vpn_badge')}
          </span>
        )}
      </div>

      {/* Hardware / Compute info */}
      <div className="space-y-1.5 text-slate-300">
        <div className="flex items-center gap-2">
          <Cpu className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          <span>
            <strong className="text-white">{t('hw_label')}:</strong> {telem.cpu_name || 'Compute Engine'} | {t('ram_label')}: {telem.ram_used_gb || 0} / {telem.ram_total_gb || 0} GB ({Math.round(telem.cpu_percent || 0)}%)
          </span>
        </div>

        {telem.gpu_name && (
          <div className="flex items-center gap-2">
            <HardDrive className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>
              <strong className="text-white">{t('gpu_label')}:</strong> {telem.gpu_name} | {t('vram_alloc')}: {telem.vram_used_gb || 0} GB ({telem.active_model || 'Idle'})
            </span>
          </div>
        )}

        <div className="flex items-center gap-2">
          <Zap className="w-3.5 h-3.5 text-yellow-400 shrink-0" />
          <span>
            <strong className="text-white">{t('power_consumption')}:</strong> {telem.power_watts || 0}W | <Thermometer className="w-3 h-3 inline text-rose-400" /> {telem.temp_c || 0}°C | <Wifi className="w-3 h-3 inline text-cyan-400" /> {telem.ping_ms || 0}ms
          </span>
        </div>
      </div>

      {/* Satelliti Figli Attivi */}
      {telem.child_satellites && telem.child_satellites.length > 0 && (
        <div className="bg-slate-900/60 rounded-lg p-2 border border-slate-800">
          <span className="text-[11px] font-bold text-cyan-400 block mb-1">
            {t('active_satellites')}:
          </span>
          <div className="flex flex-wrap gap-1.5">
            {telem.child_satellites.map((sat: string, idx: number) => (
              <span
                key={idx}
                className="px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800 text-[10px] text-cyan-200"
              >
                {sat}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Stato */}
      <div className="flex items-start gap-2 text-slate-300">
        <ShieldCheck className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-white">{t('status_label')}:</strong> {telem.status || 'Attivo in Mesh'}
        </div>
      </div>

      {/* CTA Button */}
      <button
        onClick={() => {
          if (isCore && onOpenCoreControl) {
            onOpenCoreControl();
          } else {
            onOpenNodeControl(node.id);
          }
        }}
        className="mt-1 w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold transition-all shadow-[0_0_15px_rgba(0,240,255,0.4)] text-[11px]"
      >
        <span>{isCore ? t('click_open_core') : t('click_open_node')}</span>
        <ArrowRight className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};
