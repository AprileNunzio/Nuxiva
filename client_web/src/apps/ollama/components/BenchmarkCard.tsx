import React, { useState } from 'react';
import { Gauge, Play, Timer } from 'lucide-react';
import type { BenchmarkResult } from '../types';

interface BenchmarkCardProps {
  models: string[];
  benchmarking: boolean;
  result: BenchmarkResult | null;
  onRunBenchmark: (model: string) => void;
  t: (key: string) => string;
}

export const BenchmarkCard: React.FC<BenchmarkCardProps> = ({
  models,
  benchmarking,
  result,
  onRunBenchmark,
  t,
}) => {
  const [selectedModel, setSelectedModel] = useState<string>(models[0] || '');

  return (
    <div className="flex flex-col gap-3 p-5 rounded-2xl border border-border/80 bg-card/70 backdrop-blur-md shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold tracking-wide uppercase text-muted-foreground flex items-center gap-2">
          <Gauge className="w-4 h-4 text-primary" />
          {t('bench_title')}
        </h3>
        <span className="text-xs text-muted-foreground font-medium">{t('bench_subtitle')}</span>
      </div>

      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
          className="flex-1 px-3.5 py-2.5 text-xs rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary/40 focus:border-primary outline-none transition"
        >
          {models.length > 0 ? (
            models.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))
          ) : (
            <option value="">{t('no_models_installed')}</option>
          )}
        </select>

        <button
          type="button"
          onClick={() => onRunBenchmark(selectedModel)}
          disabled={benchmarking}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold bg-secondary hover:bg-secondary/80 text-foreground border border-border/80 transition-all active:scale-95 disabled:opacity-50 cursor-pointer shadow-xs"
        >
          <Play className="w-3.5 h-3.5 fill-current text-primary" />
          <span>{benchmarking ? t('bench_running') : t('bench_run_btn')}</span>
        </button>
      </div>

      {result && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-border/60">
          <div className="p-3.5 rounded-xl bg-background/60 border border-border/60 flex flex-col shadow-xs">
            <span className="text-[11px] text-muted-foreground font-medium">{t('bench_speed')}</span>
            <span className="text-base font-bold text-primary font-mono mt-0.5">
              {result.tokens_per_second} <span className="text-xs font-normal">tok/s</span>
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-background/60 border border-border/60 flex flex-col shadow-xs">
            <span className="text-[11px] text-muted-foreground font-medium flex items-center gap-1.5">
              <Timer className="w-3 h-3 text-muted-foreground" />
              {t('bench_ttft')}
            </span>
            <span className="text-base font-bold text-foreground font-mono mt-0.5">
              {result.time_to_first_token_ms} <span className="text-xs font-normal">ms</span>
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-background/60 border border-border/60 flex flex-col shadow-xs">
            <span className="text-[11px] text-muted-foreground font-medium">{t('bench_tokens_generated')}</span>
            <span className="text-base font-bold text-foreground font-mono mt-0.5">
              {result.generated_tokens} <span className="text-xs font-normal">tok</span>
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-background/60 border border-border/60 flex flex-col shadow-xs">
            <span className="text-[11px] text-muted-foreground font-medium">{t('bench_total_duration')}</span>
            <span className="text-base font-bold text-foreground font-mono mt-0.5">
              {(result.total_duration_ms / 1000).toFixed(2)} <span className="text-xs font-normal">s</span>
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
