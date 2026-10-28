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
        <h3 className="text-sm font-semibold tracking-wide uppercase text-muted-foreground flex items-center gap-1.5">
          <Zap className="w-4 h-4 text-primary" />
          {t('hardware_detected_title')}
        </h3>
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
          {t(`tier_${hardware.tier}`)}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="p-3.5 rounded-xl border border-border bg-card/40 flex flex-col justify-between gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-primary" />
              {t('cpu_specs')}
            </span>
            <div className="flex items-center gap-1">
              {hardware.cpu.has_avx2 && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-secondary text-secondary-foreground font-semibold">
                  AVX2
                </span>
              )}
              {hardware.cpu.has_avx512 && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-secondary text-secondary-foreground font-semibold">
                  AVX-512
                </span>
              )}
            </div>
          </div>
          <div className="text-sm font-semibold truncate text-foreground" title={hardware.cpu.model}>
            {hardware.cpu.model}
          </div>
          <div className="text-xs text-muted-foreground flex items-center justify-between">
            <span>{t('cores_physical')}: {hardware.cpu.physical_cores}</span>
            <span>{t('cores_logical')}: {hardware.cpu.logical_cores}</span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl border border-border bg-card/40 flex flex-col justify-between gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
              <HardDrive className="w-3.5 h-3.5 text-primary" />
              {t('memory_specs')}
            </span>
            <span className="text-xs font-mono font-semibold text-foreground">
              {hardware.memory.available_gb} GB {t('free_suffix')}
            </span>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-sm font-semibold text-foreground">{hardware.memory.total_gb} GB RAM</span>
            <span className="text-xs text-muted-foreground">{ramPct}% in uso</span>
          </div>
          <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                ramPct > 85 ? 'bg-destructive' : ramPct > 65 ? 'bg-amber-500' : 'bg-primary'
              }`}
              style={{ width: `${ramPct}%` }}
            />
          </div>
        </div>

        <div className="p-3.5 rounded-xl border border-border bg-card/40 flex flex-col justify-between gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-primary" />
              {t('gpu_specs')}
            </span>
            {hardware.gpu ? (
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-emerald-500/10 text-emerald-500">
                {hardware.gpu.backend}
              </span>
            ) : (
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono text-muted-foreground bg-secondary">
                CPU Only
              </span>
            )}
          </div>
          <div className="text-sm font-semibold truncate text-foreground">
            {hardware.gpu ? hardware.gpu.name : t('no_gpu_detected')}
          </div>
          <div className="text-xs text-muted-foreground flex items-center justify-between">
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
