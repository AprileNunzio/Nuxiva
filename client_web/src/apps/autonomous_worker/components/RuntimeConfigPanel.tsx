import React, { useEffect, useState } from 'react';
import { Activity, CheckCircle2, Cpu, RefreshCw, Save, XCircle } from 'lucide-react';
import { checkRuntimeHealth, fetchRuntimeConfig, updateRuntimeConfig } from '../api';
import { inputFieldClass, primaryBtnClass, secondaryBtnClass, useAutonomousI18n } from '../scope';
import { RuntimeConfig, RuntimeHealth } from '../types';
import { AgentInferenceGrid } from './AgentInferenceGrid';

export const RuntimeConfigPanel: React.FC = () => {
  const { t } = useAutonomousI18n();
  const [config, setConfig] = useState<RuntimeConfig | null>(null);
  const [health, setHealth] = useState<RuntimeHealth | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    try {
      const [cfg, hlt] = await Promise.all([fetchRuntimeConfig(), checkRuntimeHealth()]);
      setConfig(cfg);
      setHealth(hlt);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!config) return;
    setSaving(true);
    try {
      const updated = await updateRuntimeConfig(config);
      setConfig(updated);
      const hlt = await checkRuntimeHealth();
      setHealth(hlt);
    } finally {
      setSaving(false);
    }
  }

  async function handleHealthcheck() {
    setLoading(true);
    try {
      const hlt = await checkRuntimeHealth();
      setHealth(hlt);
    } finally {
      setLoading(false);
    }
  }

  if (!config) return null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900/50 p-6 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-cyan-500/10 p-3 text-cyan-400">
            <Activity className="h-6 w-6" />
          </div>
          <div>
            <div className="text-base font-semibold text-slate-100">
              {health?.healthy ? t('health_ok') : t('health_bad')}
            </div>
            <div className="text-xs text-slate-400">
              {health ? t('latency', { ms: health.latency_ms }) : '---'}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void handleHealthcheck()}
          disabled={loading}
          className={secondaryBtnClass}
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          {t('test_health_btn')}
        </button>
      </div>

      <form onSubmit={(e) => void handleSave(e)} className="flex flex-col gap-5 rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
        <div>
          <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-400">
            {t('runtime_mode')}
          </label>
          <select
            value={config.mode}
            onChange={(e) => setConfig({ ...config, mode: e.target.value as RuntimeConfig['mode'] })}
            className={inputFieldClass}
          >
            <option value="auto_fallback">{t('runtime_mode_auto')}</option>
            <option value="ollama">{t('runtime_mode_ollama')}</option>
            <option value="cloud">{t('runtime_mode_cloud')}</option>
          </select>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-400">
              {t('ollama_endpoint')}
            </label>
            <input
              type="text"
              value={config.ollama_endpoint}
              onChange={(e) => setConfig({ ...config, ollama_endpoint: e.target.value })}
              className={inputFieldClass}
            />
          </div>
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-400">
              {t('ollama_model')}
            </label>
            <input
              type="text"
              value={config.ollama_model}
              onChange={(e) => setConfig({ ...config, ollama_model: e.target.value })}
              className={inputFieldClass}
            />
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-400">
              {t('rate_limit_tokens')}
            </label>
            <input
              type="number"
              value={config.token_rate_limit_per_min}
              onChange={(e) => setConfig({ ...config, token_rate_limit_per_min: Number(e.target.value) })}
              className={inputFieldClass}
            />
          </div>
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-400">
              {t('max_concurrency')}
            </label>
            <input
              type="number"
              value={config.max_concurrent_requests}
              onChange={(e) => setConfig({ ...config, max_concurrent_requests: Number(e.target.value) })}
              className={inputFieldClass}
            />
          </div>
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-400">
              {t('timeout_seconds')}
            </label>
            <input
              type="number"
              value={config.request_timeout_seconds}
              onChange={(e) => setConfig({ ...config, request_timeout_seconds: Number(e.target.value) })}
              className={inputFieldClass}
            />
          </div>
        </div>

        <div className="mt-2 flex justify-end">
          <button type="submit" disabled={saving} className={primaryBtnClass}>
            <Save className="h-4 w-4" />
            {t('save_runtime_config')}
          </button>
        </div>
      </form>

      <AgentInferenceGrid />
    </div>
  );
};
