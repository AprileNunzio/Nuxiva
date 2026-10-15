import React, { useState, useEffect } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import {
  Cpu,
  Server,
  Cloud,
  CheckCircle2,
  AlertTriangle,
  Play,
  Download,
  Terminal,
  Save,
  Eye,
  EyeOff,
  Sparkles,
  Zap,
  Activity,
  Layers,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';

interface Props {
  nodeId?: string;
}

interface CloudProvider {
  id: string;
  name: string;
  base_url: string;
  default_model: string;
  models: string[];
}

interface RemoteNode {
  id: string;
  name: string;
  ip: string;
  tier: string;
  host_url: string;
  is_compute: boolean;
}

export const View: React.FC<Props> = ({ nodeId = 'node-01' }) => {
  const { t } = useScopedI18n('node_apps/brain');

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Architecture mode: local_ollama | remote_ollama | cloud_llm
  const [mode, setMode] = useState<'local_ollama' | 'remote_ollama' | 'cloud_llm'>('local_ollama');

  // Local Ollama state
  const [localOnline, setLocalOnline] = useState(false);
  const [localModels, setLocalModels] = useState<string[]>([]);
  const [selectedLocalModel, setSelectedLocalModel] = useState('llama3.2:latest');
  const [pullInput, setPullInput] = useState('');
  const [isPulling, setIsPulling] = useState(false);
  const [pullFeedback, setPullFeedback] = useState<string | null>(null);

  // Remote Ollama state
  const [remoteNodes, setRemoteNodes] = useState<RemoteNode[]>([]);
  const [selectedRemoteNodeId, setSelectedRemoteNodeId] = useState('');
  const [remoteHostUrl, setRemoteHostUrl] = useState('http://192.168.1.10:11434');
  const [remoteModel, setRemoteModel] = useState('llama3.2:latest');

  // Cloud state
  const [cloudProviders, setCloudProviders] = useState<CloudProvider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('deepseek');
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [cloudBaseUrl, setCloudBaseUrl] = useState('https://api.deepseek.com/v1');
  const [cloudModel, setCloudModel] = useState('deepseek-chat');

  // Hyperparameters & Personality
  const [systemPrompt, setSystemPrompt] = useState(`Sei l'assistente vocale di Nuxiva dedicato per il nodo ${nodeId}.`);
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(2048);
  const [fallbackEnabled, setFallbackEnabled] = useState(true);

  // Test Inference state
  const [testPrompt, setTestPrompt] = useState('Chi sei e su quale nodo sei in esecuzione?');
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    latency_ms: number;
    reply?: string;
    tokens?: number;
    tokens_per_sec?: number;
    error?: string;
  } | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchBrainData = async () => {
      try {
        setLoading(true);
        const res = await fetch(`/api/v5/nodes/${nodeId}/brain`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!isMounted) return;

        const cfg = data.config || {};
        setMode(cfg.mode || 'local_ollama');
        if (cfg.local_model) setSelectedLocalModel(cfg.local_model);
        if (cfg.remote_node_id) setSelectedRemoteNodeId(cfg.remote_node_id);
        if (cfg.remote_host) setRemoteHostUrl(cfg.remote_host);
        if (cfg.remote_model) setRemoteModel(cfg.remote_model);
        if (cfg.cloud_provider) setSelectedProvider(cfg.cloud_provider);
        if (cfg.cloud_model) setCloudModel(cfg.cloud_model);
        if (cfg.cloud_api_key) setApiKey(cfg.cloud_api_key);
        if (cfg.cloud_base_url) setCloudBaseUrl(cfg.cloud_base_url);
        if (cfg.system_prompt) setSystemPrompt(cfg.system_prompt);
        if (typeof cfg.temperature === 'number') setTemperature(cfg.temperature);
        if (typeof cfg.max_tokens === 'number') setMaxTokens(cfg.max_tokens);
        if (typeof cfg.fallback_enabled === 'boolean') setFallbackEnabled(cfg.fallback_enabled);

        if (data.local_ollama) {
          setLocalOnline(!!data.local_ollama.online);
          const models = data.local_ollama.models || [];
          const catalog = data.local_ollama.catalog || [];
          const available = models.length > 0 ? models : catalog;
          setLocalModels(available);
          if (!cfg.local_model && available.length > 0) {
            setSelectedLocalModel(available[0]);
          }
        }

        if (Array.isArray(data.remote_nodes)) {
          setRemoteNodes(data.remote_nodes);
          if (!cfg.remote_node_id && data.remote_nodes.length > 0) {
            setSelectedRemoteNodeId(data.remote_nodes[0].id);
            setRemoteHostUrl(data.remote_nodes[0].host_url);
          }
        }

        if (Array.isArray(data.cloud_providers)) {
          setCloudProviders(data.cloud_providers);
        }
      } catch (err) {
        console.warn('Failed to load brain configuration from server', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchBrainData();
    return () => {
      isMounted = false;
    };
  }, [nodeId]);

  const handleProviderSelect = (providerId: string) => {
    setSelectedProvider(providerId);
    const p = cloudProviders.find((x) => x.id === providerId);
    if (p) {
      setCloudBaseUrl(p.base_url);
      setCloudModel(p.default_model);
    }
  };

  const handleRemoteNodeSelect = (remoteId: string) => {
    setSelectedRemoteNodeId(remoteId);
    const rn = remoteNodes.find((x) => x.id === remoteId);
    if (rn) {
      setRemoteHostUrl(rn.host_url);
    }
  };

  const handlePullModel = async () => {
    if (!pullInput.trim()) return;
    setIsPulling(true);
    setPullFeedback(null);
    try {
      const res = await fetch(`/api/v5/nodes/${nodeId}/brain/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: mode === 'remote_ollama' ? remoteHostUrl : 'http://127.0.0.1:11434',
          model: pullInput.trim(),
        }),
      });
      const data = await res.json();
      if (data.success) {
        setPullFeedback(t('pull_success'));
        if (!localModels.includes(pullInput.trim())) {
          setLocalModels([pullInput.trim(), ...localModels]);
        }
        setSelectedLocalModel(pullInput.trim());
        setPullInput('');
      } else {
        setPullFeedback(`${t('pull_error')}: ${data.error || 'Unknown'}`);
      }
    } catch (err: any) {
      setPullFeedback(`${t('pull_error')}: ${err.message}`);
    } finally {
      setIsPulling(false);
    }
  };

  const handleRunInferenceTest = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const payload: Record<string, any> = {
        mode,
        prompt: testPrompt,
      };

      if (mode === 'local_ollama') {
        payload.host = 'http://127.0.0.1:11434';
        payload.model = selectedLocalModel;
      } else if (mode === 'remote_ollama') {
        payload.host = remoteHostUrl;
        payload.model = remoteModel;
      } else {
        payload.cloud_provider = selectedProvider;
        payload.cloud_api_key = apiKey;
        payload.cloud_base_url = cloudBaseUrl;
        payload.model = cloudModel;
      }

      const res = await fetch(`/api/v5/nodes/${nodeId}/brain/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      setTestResult(data);
    } catch (err: any) {
      setTestResult({
        success: false,
        latency_ms: 0,
        error: `${t('err_prefix')}: ${err.message}`,
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    setSaveSuccess(false);
    setSaveError(null);
    try {
      const payload = {
        mode,
        local_model: selectedLocalModel,
        remote_node_id: selectedRemoteNodeId,
        remote_host: remoteHostUrl,
        remote_model: remoteModel,
        cloud_provider: selectedProvider,
        cloud_model: cloudModel,
        cloud_api_key: apiKey,
        cloud_base_url: cloudBaseUrl,
        system_prompt: systemPrompt,
        temperature,
        max_tokens: maxTokens,
        fallback_enabled: fallbackEnabled,
        fallback_provider: 'local_ollama',
      };

      const res = await fetch(`/api/v5/nodes/${nodeId}/brain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3500);
    } catch (err: any) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 flex flex-col items-center justify-center text-slate-400 font-mono gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
        <span className="text-xs">Sincronizzazione stato cervello del nodo...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-mono text-slate-100">
      {/* Header Banner */}
      <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl shadow-cyan-950/10">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.2)]">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
                {t('title')}
                <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-normal">
                  v5.0 Mesh
                </span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">{t('description')}</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto justify-end">
          <button
            onClick={handleSaveConfig}
            disabled={saving}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-cyan-500/20 transition cursor-pointer disabled:opacity-50"
          >
            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? t('saving') : t('save')}
          </button>
        </div>
      </div>

      {saveSuccess && (
        <div className="bg-emerald-950/60 border border-emerald-500/40 p-3.5 rounded-xl flex items-center gap-3 text-xs text-emerald-300">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{t('saved')}</span>
        </div>
      )}

      {saveError && (
        <div className="bg-rose-950/60 border border-rose-500/40 p-3.5 rounded-xl flex items-center gap-3 text-xs text-rose-300">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{t('save_error')}: {saveError}</span>
        </div>
      )}

      {/* Mode Selection Cards */}
      <div className="space-y-3">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          {t('mode_title')}
        </div>
        <p className="text-[11px] text-slate-500">{t('mode_desc')}</p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Mode 1: Local Ollama */}
          <div
            onClick={() => setMode('local_ollama')}
            className={`p-4 rounded-xl border cursor-pointer transition flex flex-col justify-between ${
              mode === 'local_ollama'
                ? 'bg-cyan-950/30 border-cyan-500/60 shadow-[0_0_20px_rgba(6,182,212,0.15)] ring-1 ring-cyan-500/50'
                : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  <Cpu className="w-5 h-5" />
                </div>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                    localOnline
                      ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                      : 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                  }`}
                >
                  {localOnline ? 'ONLINE' : 'STANDBY'}
                </span>
              </div>
              <h3 className="text-sm font-bold text-white">{t('mode_local')}</h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">{t('mode_local_desc')}</p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/80 text-[10px] text-slate-500 flex items-center justify-between">
              <span>Port: 11434</span>
              <span>{localModels.length} modelli rilevati</span>
            </div>
          </div>

          {/* Mode 2: Remote Mesh LAN Ollama */}
          <div
            onClick={() => setMode('remote_ollama')}
            className={`p-4 rounded-xl border cursor-pointer transition flex flex-col justify-between ${
              mode === 'remote_ollama'
                ? 'bg-purple-950/30 border-purple-500/60 shadow-[0_0_20px_rgba(168,85,247,0.15)] ring-1 ring-purple-500/50'
                : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
                  <Server className="w-5 h-5" />
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-purple-500/15 text-purple-400 border border-purple-500/30">
                  LAN OFFLOAD
                </span>
              </div>
              <h3 className="text-sm font-bold text-white">{t('mode_remote')}</h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">{t('mode_remote_desc')}</p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/80 text-[10px] text-slate-500 flex items-center justify-between">
              <span>P2P Routing</span>
              <span>{remoteNodes.length} nodi calcolo LAN</span>
            </div>
          </div>

          {/* Mode 3: Cloud LLM API Key */}
          <div
            onClick={() => setMode('cloud_llm')}
            className={`p-4 rounded-xl border cursor-pointer transition flex flex-col justify-between ${
              mode === 'cloud_llm'
                ? 'bg-blue-950/30 border-blue-500/60 shadow-[0_0_20px_rgba(59,130,246,0.15)] ring-1 ring-blue-500/50'
                : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  <Cloud className="w-5 h-5" />
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-blue-500/15 text-blue-400 border border-blue-500/30">
                  API KEY
                </span>
              </div>
              <h3 className="text-sm font-bold text-white">{t('mode_cloud')}</h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">{t('mode_cloud_desc')}</p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/80 text-[10px] text-slate-500 flex items-center justify-between">
              <span>DeepSeek / OpenAI / Claude</span>
              <span>Zero carico GPU locale</span>
            </div>
          </div>
        </div>
      </div>

      {/* Mode Specific Configuration Panel */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-xl">
        {mode === 'local_ollama' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="text-xs font-semibold text-cyan-400 flex items-center gap-2">
                <Cpu className="w-4 h-4" />
                {t('local_settings')}
              </div>
              <div className="text-[11px] flex items-center gap-1.5 text-slate-400">
                <span className={`w-2 h-2 rounded-full ${localOnline ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
                {localOnline ? t('local_status_online') : t('local_status_offline')}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">{t('select_model')}</label>
                <select
                  value={selectedLocalModel}
                  onChange={(e) => setSelectedLocalModel(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-500"
                >
                  {localModels.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
                <p className="text-[10px] text-slate-500 mt-1">{t('vram_est')}: ~4.2 GB VRAM / RAM</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">{t('pull_model')}</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={pullInput}
                    onChange={(e) => setPullInput(e.target.value)}
                    placeholder="e.g. qwen2.5:7b, mistral:7b, deepseek-r1:1.5b"
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                  />
                  <button
                    onClick={handlePullModel}
                    disabled={isPulling || !pullInput.trim()}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 disabled:opacity-40"
                  >
                    {isPulling ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                    {isPulling ? t('pulling') : t('pull_btn')}
                  </button>
                </div>
                {pullFeedback && <p className="text-[11px] text-cyan-400 mt-1.5">{pullFeedback}</p>}
              </div>
            </div>
          </div>
        )}

        {mode === 'remote_ollama' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="text-xs font-semibold text-purple-400 flex items-center gap-2">
                <Server className="w-4 h-4" />
                {t('remote_settings')}
              </div>
              <span className="text-[11px] text-slate-400">P2P Low-Latency Offload</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">{t('select_remote_node')}</label>
                <select
                  value={selectedRemoteNodeId}
                  onChange={(e) => handleRemoteNodeSelect(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-purple-500"
                >
                  {remoteNodes.map((rn) => (
                    <option key={rn.id} value={rn.id}>
                      {rn.name} ({rn.ip})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">{t('custom_host_url')}</label>
                <input
                  type="text"
                  value={remoteHostUrl}
                  onChange={(e) => setRemoteHostUrl(e.target.value)}
                  placeholder="http://192.168.1.10:11434"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">{t('select_model')}</label>
                <input
                  type="text"
                  value={remoteModel}
                  onChange={(e) => setRemoteModel(e.target.value)}
                  placeholder="llama3.2:latest"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                />
              </div>
            </div>
          </div>
        )}

        {mode === 'cloud_llm' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="text-xs font-semibold text-blue-400 flex items-center gap-2">
                <Cloud className="w-4 h-4" />
                {t('cloud_settings')}
              </div>
              <span className="text-[11px] text-slate-400">High-Precision Cloud API</span>
            </div>

            {/* Provider Pills */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-2">{t('cloud_provider')}</label>
              <div className="flex flex-wrap gap-2">
                {cloudProviders.map((cp) => (
                  <button
                    key={cp.id}
                    onClick={() => handleProviderSelect(cp.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer border ${
                      selectedProvider === cp.id
                        ? 'bg-blue-600/20 text-blue-300 border-blue-500/60 shadow-[0_0_10px_rgba(59,130,246,0.2)]'
                        : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    {cp.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-slate-300 mb-1.5">{t('api_key')}</label>
                <div className="relative">
                  <input
                    type={showKey ? 'text' : 'password'}
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder={t('api_key_placeholder')}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-3.5 pr-10 py-2 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey(!showKey)}
                    className="absolute right-2.5 top-2.5 text-slate-500 hover:text-slate-300"
                  >
                    {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">{t('cloud_model')}</label>
                <input
                  type="text"
                  value={cloudModel}
                  onChange={(e) => setCloudModel(e.target.value)}
                  placeholder="deepseek-chat, gpt-4o-mini"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="md:col-span-3">
                <label className="block text-xs font-medium text-slate-400 mb-1">{t('base_url')}</label>
                <input
                  type="text"
                  value={cloudBaseUrl}
                  onChange={(e) => setCloudBaseUrl(e.target.value)}
                  placeholder="https://api.deepseek.com/v1"
                  className="w-full bg-slate-950 border border-slate-800/80 rounded-lg px-3.5 py-2 text-xs text-slate-300 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Node Personality & Hyperparameters */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          {t('system_prompt')}
        </div>

        <textarea
          rows={3}
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
          placeholder={t('system_prompt_placeholder')}
          className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
          <div>
            <div className="flex justify-between text-xs text-slate-300 mb-1.5">
              <span>{t('temperature')}</span>
              <span className="font-bold text-cyan-400">{temperature.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.5"
              step="0.05"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full accent-cyan-500 bg-slate-950 rounded-lg h-1.5 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 mt-1">
              <span>0.0 (Preciso / Deterministico)</span>
              <span>1.0 (Creativo)</span>
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs text-slate-300 mb-1.5">
              <span>{t('max_tokens')}</span>
              <span className="font-bold text-cyan-400">{maxTokens}</span>
            </div>
            <input
              type="range"
              min="256"
              max="8192"
              step="256"
              value={maxTokens}
              onChange={(e) => setMaxTokens(parseInt(e.target.value, 10))}
              className="w-full accent-cyan-500 bg-slate-950 rounded-lg h-1.5 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 mt-1">
              <span>256 token</span>
              <span>8192 token</span>
            </div>
          </div>
        </div>

        <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
          <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={fallbackEnabled}
              onChange={(e) => setFallbackEnabled(e.target.checked)}
              className="accent-cyan-500 rounded"
            />
            <span>{t('fallback_toggle')}</span>
          </label>
          <span className="text-[10px] text-emerald-400 flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5" /> Failover attivo
          </span>
        </div>
      </div>

      {/* Live Inference Diagnostic Terminal */}
      <div className="bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
        <div className="bg-slate-900/90 border-b border-slate-800 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-semibold text-slate-200">{t('test_section_title')}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setTestPrompt(t('preset_who'))}
              className="text-[10px] px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
            >
              Preset: Chi sei?
            </button>
            <button
              onClick={() => setTestPrompt(t('preset_latency'))}
              className="text-[10px] px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
            >
              Preset: Latenza
            </button>
          </div>
        </div>

        <div className="p-4 space-y-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={testPrompt}
              onChange={(e) => setTestPrompt(e.target.value)}
              placeholder={t('test_prompt_placeholder')}
              className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500"
            />
            <button
              onClick={handleRunInferenceTest}
              disabled={isTesting || !testPrompt.trim()}
              className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-lg shadow-cyan-600/20 disabled:opacity-50 cursor-pointer"
            >
              {isTesting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {isTesting ? t('testing') : t('test_btn')}
            </button>
          </div>

          {/* Cyber Terminal Output Screen */}
          <div className="bg-[#020617] border border-cyan-950/60 rounded-xl p-4 font-mono min-h-[120px] text-xs">
            {testResult ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2 text-[11px]">
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        testResult.success ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'
                      }`}
                    />
                    <span className={testResult.success ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                      {testResult.success ? '200 OK — RISPOSTA RICEVUTA' : 'TEST FALLITO'}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-slate-400">
                    <span className="flex items-center gap-1">
                      <Zap className="w-3 h-3 text-amber-400" />
                      {t('latency')}: <strong className="text-white">{testResult.latency_ms} ms</strong>
                    </span>
                    {typeof testResult.tokens === 'number' && (
                      <span className="flex items-center gap-1">
                        <Activity className="w-3 h-3 text-cyan-400" />
                        {t('tokens')}: <strong className="text-white">{testResult.tokens}</strong>
                      </span>
                    )}
                    {typeof testResult.tokens_per_sec === 'number' && (
                      <span className="text-slate-400">
                        {t('speed')}: <strong className="text-emerald-400">{testResult.tokens_per_sec} tok/s</strong>
                      </span>
                    )}
                  </div>
                </div>

                {testResult.success ? (
                  <div className="text-slate-200 leading-relaxed whitespace-pre-wrap selection:bg-cyan-500 selection:text-black">
                    {testResult.reply}
                  </div>
                ) : (
                  <div className="text-rose-400 bg-rose-950/30 p-2.5 rounded border border-rose-900/50 leading-relaxed">
                    {testResult.error}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-slate-600 flex items-center justify-center h-20 gap-2">
                <Terminal className="w-4 h-4" />
                <span>{t('term_waiting')}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default View;
