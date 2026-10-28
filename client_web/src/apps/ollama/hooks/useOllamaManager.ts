import { useCallback, useEffect, useState } from 'react';
import {
  fetchOllamaStatus,
  resetToAutoProfile,
  restartOllamaService,
  runOllamaBenchmark,
  updateOllamaConfig,
} from '../api';
import type { BenchmarkResult, DaemonStatus, HardwareProfile, OllamaConfig } from '../types';

export function useOllamaManager() {
  const [status, setStatus] = useState<DaemonStatus | null>(null);
  const [config, setConfig] = useState<OllamaConfig | null>(null);
  const [hardware, setHardware] = useState<HardwareProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [benchmarking, setBenchmarking] = useState<boolean>(false);
  const [benchResult, setBenchResult] = useState<BenchmarkResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successKey, setSuccessKey] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchOllamaStatus();
      setStatus(res);
      setConfig(res.config);
      setHardware(res.hardware);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const updateField = useCallback(<K extends keyof OllamaConfig>(key: K, value: OllamaConfig[K]) => {
    setConfig((prev) => (prev ? { ...prev, [key]: value } : prev));
  }, []);

  const handleSave = useCallback(async () => {
    if (!config) return;
    try {
      setSaving(true);
      setError(null);
      setSuccessKey(null);
      const res = await updateOllamaConfig(config);
      setConfig(res.config);
      setSuccessKey('save_applied');
      await loadStatus();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }, [config, loadStatus]);

  const handleResetAuto = useCallback(async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccessKey(null);
      const res = await resetToAutoProfile();
      setConfig(res.config);
      setHardware(res.hardware);
      setSuccessKey('reset_success');
      await loadStatus();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }, [loadStatus]);

  const handleRestart = useCallback(async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccessKey(null);
      await restartOllamaService();
      setSuccessKey('restart_success');
      setTimeout(loadStatus, 2000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }, [loadStatus]);

  const handleBenchmark = useCallback(async (model: string = '') => {
    try {
      setBenchmarking(true);
      setError(null);
      setBenchResult(null);
      const res = await runOllamaBenchmark(model);
      setBenchResult(res);
      setSuccessKey('bench_success');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBenchmarking(false);
    }
  }, []);

  return {
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
    refresh: loadStatus,
  };
}
