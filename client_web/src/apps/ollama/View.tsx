import React from 'react';
import { AlertCircle, CheckCircle, RefreshCw } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { ActionBar } from './components/ActionBar';
import { BenchmarkCard } from './components/BenchmarkCard';
import { ConfigurationCard } from './components/ConfigurationCard';
import { HardwareMetricsCard } from './components/HardwareMetricsCard';
import { HeaderStatus } from './components/HeaderStatus';
import { useOllamaManager } from './hooks/useOllamaManager';

export const View: React.FC = () => {
  const { t } = useScopedI18n('apps/ollama');
  const {
    status,
    config,
    hardware,
    loading,
    saving,
    benchmarking,
    benchResult,
    error,
    successKey,
    updateField,
    handleSave,
    handleResetAuto,
    handleRestart,
    handleBenchmark,
    refresh,
  } = useOllamaManager();

  if (loading && !status) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-3 p-8">
        <RefreshCw className="w-8 h-8 text-primary animate-spin" />
        <span className="text-xs text-muted-foreground">{t('loading_state')}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-4 md:p-6 max-w-6xl mx-auto w-full text-foreground">
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl border border-destructive/30 bg-destructive/10 text-destructive text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {successKey && (
        <div className="flex items-center gap-2 p-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-xs">
          <CheckCircle className="w-4 h-4 shrink-0" />
          <span>{t(successKey)}</span>
        </div>
      )}

      <HeaderStatus status={status} t={t} />

      <HardwareMetricsCard hardware={hardware} t={t} />

      <ConfigurationCard config={config} updateField={updateField} t={t} />

      <BenchmarkCard
        models={status?.active_models || []}
        benchmarking={benchmarking}
        result={benchResult}
        onRunBenchmark={handleBenchmark}
        t={t}
      />

      <ActionBar
        saving={saving}
        onSave={handleSave}
        onResetAuto={handleResetAuto}
        onRestart={handleRestart}
        t={t}
      />
    </div>
  );
};
