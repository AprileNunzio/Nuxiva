import React from 'react';
import { Cpu, HardDrive, Sparkles, Zap } from 'lucide-react';
import type { HardwareProfile } from '../types';

interface HardwareMetricsCardProps {
  hardware: HardwareProfile | null;
  t: (key: string) => string;
}

export const HardwareMetricsCard: React.FC<HardwareMetricsCardProps> = ({ hardware, t }) => {
  if (!hardware) return null;

  const ramPct = Math.min(
    100,
    Math.round(((hardware.memory.total_gb - hardware.memory.available_gb) / hardware.memory.total_gb) * 100)
  );

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold tracking-wide uppercase text-muted-foreground flex items-center gap-2">
          <Zap className="w-4 h-4 text-primary" />
          {t('hardware_detected_title')}
        </h3>
        <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
          {t(`tier_${hardware.tier}`)}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        <div className="p-4 rounded-2xl border border-border/80 bg-card/70 backdrop-blur-md flex flex-col justify-between gap-3 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-primary" />
              {t('cpu_specs')}
            </span>
            <div className="flex items-center gap-1">
              {hardware.cpu.has_avx2 && (
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-secondary text-secondary-foreground font-bold">
                  AVX2
                </span>
              )}
              {hardware.cpu.has_avx512 && (
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-secondary text-secondary-foreground font-bold">
                  AVX-512
                </span>
              )}
            </div>
          </div>
          <div className="text-sm font-bold truncate text-foreground" title={hardware.cpu.model}>
            {hardware.cpu.model}
          </div>
          <div className="text-xs text-muted-foreground flex items-center justify-between font-medium">
            <span>{t('cores_physical')}: {hardware.cpu.physical_cores}</span>
            <span>{t('cores_logical')}: {hardware.cpu.logical_cores}</span>
          </div>
        </div>

        <div className="p-4 rounded-2xl border border-border/80 bg-card/70 backdrop-blur-md flex flex-col justify-between gap-3 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
              <HardDrive className="w-4 h-4 text-primary" />
              {t('memory_specs')}
            </span>
            <span className="text-xs font-mono font-bold text-foreground">
              {hardware.memory.available_gb} GB {t('free_suffix')}
            </span>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-sm font-bold text-foreground">{hardware.memory.total_gb} GB RAM</span>
            <span className="text-xs font-medium text-muted-foreground">{ramPct}% in uso</span>
          </div>
          <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                ramPct > 85 ? 'bg-destructive' : ramPct > 65 ? 'bg-amber-500' : 'bg-primary'
              }`}
              style={{ width: `${ramPct}%` }}
            />
          </div>
        </div>

        <div className="p-4 rounded-2xl border border-border/80 bg-card/70 backdrop-blur-md flex flex-col justify-between gap-3 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-primary" />
              {t('gpu_specs')}
            </span>
            {hardware.gpu ? (
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                {hardware.gpu.backend}
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded text-[10px] font-mono text-muted-foreground bg-secondary font-semibold">
                CPU Only
              </span>
            )}
          </div>
          <div className="text-sm font-bold truncate text-foreground">
            {hardware.gpu ? hardware.gpu.name : t('no_gpu_detected')}
          </div>
          <div className="text-xs text-muted-foreground flex items-center justify-between font-medium">
            <span>
              {hardware.gpu
                ? `${hardware.gpu.vram_total_gb} GB VRAM (${hardware.gpu.vram_free_gb} GB ${t('free_suffix')})`
                : t('cpu_inference_active')}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
