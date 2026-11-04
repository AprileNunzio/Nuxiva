import React from 'react';
import { Sliders, Zap } from 'lucide-react';
import type { OllamaConfig } from '../types';

interface ConfigurationCardProps {
  config: OllamaConfig | null;
  updateField: <K extends keyof OllamaConfig>(key: K, value: OllamaConfig[K]) => void;
  t: (key: string) => string;
}

export const ConfigurationCard: React.FC<ConfigurationCardProps> = ({ config, updateField, t }) => {
  if (!config) return null;

  return (
    <div className="flex flex-col gap-4 p-4 rounded-xl border border-border bg-card/60 backdrop-blur-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold tracking-wide uppercase text-muted-foreground flex items-center gap-1.5">
          <Sliders className="w-4 h-4 text-primary" />
          {t('tuning_title')}
        </h3>
        <span className="text-xs text-muted-foreground flex items-center gap-1">
          <Zap className="w-3.5 h-3.5 text-amber-500" />
          {t('dual_lane_active_badge')}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-foreground flex items-center justify-between">
            <span>{t('parallel_slots_label')}</span>
            <span className="text-[11px] font-mono text-primary font-bold">{config.num_parallel}</span>
          </label>
          <select
            value={config.num_parallel}
            onChange={(e) => updateField('num_parallel', parseInt(e.target.value, 10))}
            className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background focus:ring-1 focus:ring-primary outline-none transition"
          >
            <option value="1">1 ({t('slot_single')})</option>
            <option value="2">2 ({t('slot_dual_recommended')})</option>
            <option value="4">4 ({t('slot_quad_enterprise')})</option>
            <option value="8">8 ({t('slot_octa_server')})</option>
          </select>
          <span className="text-[11px] text-muted-foreground leading-tight">
            {t('parallel_slots_hint')}
          </span>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-foreground flex items-center justify-between">
            <span>{t('context_window_label')}</span>
            <span className="text-[11px] font-mono text-primary font-bold">{config.num_ctx} tok</span>
          </label>
          <select
            value={config.num_ctx}
            onChange={(e) => updateField('num_ctx', parseInt(e.target.value, 10))}
            className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background focus:ring-1 focus:ring-primary outline-none transition"
          >
            <option value="2048">2.048 tok (Minimal)</option>
            <option value="4096">4.096 tok (Standard)</option>
            <option value="8192">8.192 tok (Deep Reasoning)</option>
            <option value="16384">16.384 tok (Long Horizon)</option>
            <option value="32768">32.768 tok (Full Project / Code)</option>
            <option value="65536">65.536 tok (Extreme Enterprise)</option>
          </select>
          <span className="text-[11px] text-muted-foreground leading-tight">
            {t('context_window_hint')}
          </span>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-foreground flex items-center justify-between">
            <span>{t('max_predict_label')}</span>
            <span className="text-[11px] font-mono text-primary font-bold">{config.num_predict} tok</span>
          </label>
          <select
            value={config.num_predict}
            onChange={(e) => updateField('num_predict', parseInt(e.target.value, 10))}
            className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background focus:ring-1 focus:ring-primary outline-none transition"
          >
            <option value="500">500 tok (Legacy Short)</option>
            <option value="1024">1.024 tok (Chat)</option>
            <option value="2048">2.048 tok (Structured)</option>
            <option value="4096">4.096 tok (Deep Code / Proof)</option>
            <option value="8192">8.192 tok (Autonomous Agent)</option>
          </select>
          <span className="text-[11px] text-muted-foreground leading-tight">
            {t('max_predict_hint')}
          </span>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-foreground flex items-center justify-between">
            <span>{t('max_loaded_models_label')}</span>
            <span className="text-[11px] font-mono text-primary font-bold">{config.max_loaded_models}</span>
          </label>
          <select
            value={config.max_loaded_models}
            onChange={(e) => updateField('max_loaded_models', parseInt(e.target.value, 10))}
            className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background focus:ring-1 focus:ring-primary outline-none transition"
          >
            <option value="1">1 (Risparmio RAM)</option>
            <option value="2">2 (Veloce + Profondo)</option>
            <option value="3">3 (Veloce + Profondo + Embedding)</option>
            <option value="4">4 (Workstation)</option>
          </select>
          <span className="text-[11px] text-muted-foreground leading-tight">
            {t('max_loaded_models_hint')}
          </span>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-foreground flex items-center justify-between">
            <span>{t('keep_alive_label')}</span>
            <span className="text-[11px] font-mono text-primary font-bold">{config.keep_alive}</span>
          </label>
          <select
            value={config.keep_alive}
            onChange={(e) => updateField('keep_alive', e.target.value)}
            className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background focus:ring-1 focus:ring-primary outline-none transition"
          >
            <option value="24h">24h ({t('keep_alive_24h_h24')})</option>
            <option value="12h">12h</option>
            <option value="1h">1h</option>
            <option value="10m">10m</option>
            <option value="-1">{t('keep_alive_infinite')}</option>
          </select>
          <span className="text-[11px] text-muted-foreground leading-tight">
            {t('keep_alive_hint')}
          </span>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-foreground flex items-center justify-between">
            <span>{t('cpu_threads_label')}</span>
            <span className="text-[11px] font-mono text-primary font-bold">{config.num_thread}</span>
          </label>
          <input
            type="number"
            min={1}
            max={64}
            value={config.num_thread}
            onChange={(e) => updateField('num_thread', Math.max(1, parseInt(e.target.value, 10) || 1))}
            className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background focus:ring-1 focus:ring-primary outline-none transition"
          />
          <span className="text-[11px] text-muted-foreground leading-tight">
            {t('cpu_threads_hint')}
          </span>
        </div>
      </div>

      <div className="pt-2 border-t border-border/60 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={config.flash_attention}
              onChange={(e) => updateField('flash_attention', e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-secondary peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"></div>
          </label>
          <div>
            <span className="text-xs font-semibold text-foreground">{t('flash_attention_label')}</span>
            <p className="text-[11px] text-muted-foreground leading-tight">{t('flash_attention_hint')}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
