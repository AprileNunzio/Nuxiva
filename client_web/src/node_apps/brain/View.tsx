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
  Plus,
  Trash2,
  Wifi,
  ExternalLink,
  Brain,
  Sliders,
  Check,
  X,
  Radio,
} from 'lucide-react';
import {
  CloudProvider,
  RemoteOllamaInstance,
  CloudSlotConfig,
  LocalOllamaStatus,
  TestResult,
} from './types';
import {
  fetchBrainData,
  saveBrainConfig,
  installLocalOllama,
  uninstallLocalOllama,
  testRemoteMeshInstance,
  saveRemoteMeshInstances,
  testBrainInference,
  pullBrainModel,
} from './api';

interface Props {
  nodeId?: string;
}

export const View: React.FC<Props> = ({ nodeId = 'node-01' }) => {
  const { t } = useScopedI18n('node_apps/brain');

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Architecture Mode: local_ollama | remote_ollama | cloud_llm
  const [mode, setMode] = useState<'local_ollama' | 'remote_ollama' | 'cloud_llm'>('local_ollama');

  // Local Ollama State
  const [localStatus, setLocalStatus] = useState<LocalOllamaStatus>({
    installed: false,
    running: false,
    models: [],
    catalog: ['llama3.2:latest', 'qwen2.5:1.5b', 'deepseek-r1:1.5b'],
  });
  const [selectedLocalModel, setSelectedLocalModel] = useState('llama3.2:latest');
  const [pullInput, setPullInput] = useState('');
  const [isPulling, setIsPulling] = useState(false);
  const [pullFeedback, setPullFeedback] = useState<string | null>(null);
  const [isInstallingOllama, setIsInstallingOllama] = useState(false);
  const [installMsg, setInstallMsg] = useState<string | null>(null);
  const [isUninstallingOllama, setIsUninstallingOllama] = useState(false);

  // Remote Mesh Ollama Instances
  const [remoteInstances, setRemoteInstances] = useState<RemoteOllamaInstance[]>([]);
  const [isAddingInstance, setIsAddingInstance] = useState(false);
  const [newInstanceName, setNewInstanceName] = useState('');
  const [newInstanceHost, setNewInstanceHost] = useState('http://192.168.1.10:11434');
  const [newInstanceModel, setNewInstanceModel] = useState('llama3.2:latest');
  const [newInstanceTask, setNewInstanceTask] = useState('fast_chat');
  const [isTestingRemote, setIsTestingRemote] = useState(false);
  const [remoteTestResult, setRemoteTestResult] = useState<any>(null);

  // Cloud Providers & Multi-Role Slots
  const [cloudProviders, setCloudProviders] = useState<CloudProvider[]>([]);
  const [cloudSlots, setCloudSlots] = useState<{
    fast_chat: CloudSlotConfig;
    deep_reasoning: CloudSlotConfig;
    vision: CloudSlotConfig;
  }>({
    fast_chat: {
      provider: 'gemini',
      model: 'gemini-2.0-flash',
      api_key: '',
      base_url: 'https://generativelanguage.googleapis.com/v1beta',
    },
    deep_reasoning: {
      provider: 'deepseek',
      model: 'deepseek-reasoner',
      api_key: '',
      base_url: 'https://api.deepseek.com/v1',
    },
    vision: {
      provider: 'openai',
      model: 'gpt-4o',
      api_key: '',
      base_url: 'https://api.openai.com/v1',
    },
  });

  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({
    fast_chat: false,
    deep_reasoning: false,
    vision: false,
  });

  // Hyperparameters & Personality
  const [systemPrompt, setSystemPrompt] = useState(`Sei l'assistente IA di Nuxiva dedicato per il nodo ${nodeId}.`);
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(2048);
  const [fallbackEnabled, setFallbackEnabled] = useState(true);

  // Test Inference state
  const [testPrompt, setTestPrompt] = useState('Chi sei e su quale nodo sei in esecuzione?');
  const [testSlot, setTestSlot] = useState<string>('fast_chat');
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await fetchBrainData(nodeId);

      if (data.local_ollama) {
        setLocalStatus(data.local_ollama);
        if (data.local_ollama.models && data.local_ollama.models.length > 0) {
          setSelectedLocalModel(data.local_ollama.models[0]);
        }
      }

      if (data.cloud_providers) {
        setCloudProviders(data.cloud_providers);
      }

      const cfg = data.config || {};
      if (cfg.mode) setMode(cfg.mode);
      if (cfg.local_model) setSelectedLocalModel(cfg.local_model);
      if (cfg.system_prompt) setSystemPrompt(cfg.system_prompt);
      if (cfg.temperature !== undefined) setTemperature(cfg.temperature);
      if (cfg.max_tokens !== undefined) setMaxTokens(cfg.max_tokens);
      if (cfg.fallback_enabled !== undefined) setFallbackEnabled(cfg.fallback_enabled);

      if (cfg.cloud_slots) {
        setCloudSlots(cfg.cloud_slots);
      }

      if (cfg.remote_mesh_instances) {
        setRemoteInstances(cfg.remote_mesh_instances);
      }
    } catch (err: any) {
      console.error('Failed to load brain config:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [nodeId]);

  // Install Ollama handler
  const handleInstallOllama = async () => {
    try {
      setIsInstallingOllama(true);
      setInstallMsg(t('installing_ollama') || 'Installazione avviata...');
      const res = await installLocalOllama(nodeId);
      if (res.message) {
        setInstallMsg(res.message);
      }
      // Poll every 3 seconds for 15 seconds to check if installed
      let attempts = 0;
      const interval = setInterval(async () => {
        attempts++;
        const check = await fetchBrainData(nodeId);
        if (check.local_ollama?.installed) {
          setLocalStatus(check.local_ollama);
          setIsInstallingOllama(false);
          setInstallMsg(null);
          clearInterval(interval);
        }
        if (attempts > 5) {
          setIsInstallingOllama(false);
          clearInterval(interval);
        }
      }, 3000);
    } catch (err: any) {
      setInstallMsg(`Errore: ${err.message}`);
      setIsInstallingOllama(false);
    }
  };

  // Uninstall Ollama handler
  const handleUninstallOllama = async () => {
    if (!window.confirm(t('uninstall_confirm') || 'Sei sicuro di voler disinstallare Ollama?')) {
      return;
    }
    try {
      setIsUninstallingOllama(true);
      await uninstallLocalOllama(nodeId);
      await loadData();
    } catch (err: any) {
      console.error('Error uninstalling Ollama:', err);
    } finally {
      setIsUninstallingOllama(false);
    }
  };

  // Pull new model handler
  const handlePullModel = async (modelToPull?: string) => {
    const target = (modelToPull || pullInput).trim();
    if (!target) return;
    try {
      setIsPulling(true);
      setPullFeedback(t('pulling') || 'Download in corso...');
      const res = await pullBrainModel(nodeId, target);
      if (res.success) {
        setPullFeedback(t('pull_success') || 'Modello scaricato con successo!');
        setPullInput('');
        await loadData();
      } else {
        setPullFeedback(`${t('pull_error')}: ${res.error}`);
      }
    } catch (err: any) {
      setPullFeedback(`Errore: ${err.message}`);
    } finally {
      setIsPulling(false);
      setTimeout(() => setPullFeedback(null), 4000);
    }
  };

  // Add Remote Mesh instance handler
  const handleAddRemoteInstance = async () => {
    if (!newInstanceHost.trim()) return;
    const newInst: RemoteOllamaInstance = {
      id: `inst-${Date.now()}`,
      name: newInstanceName.trim() || `Ollama-${newInstanceHost.replace('http://', '').split(':')[0]}`,
      host_url: newInstanceHost.trim(),
      model: newInstanceModel.trim() || 'llama3.2:latest',
      task: newInstanceTask,
      status: 'online',
      latency_ms: remoteTestResult?.latency_ms || 2.4,
    };
    const updated = [...remoteInstances, newInst];
    setRemoteInstances(updated);
    setIsAddingInstance(false);
    setNewInstanceName('');
    setRemoteTestResult(null);
    await saveRemoteMeshInstances(nodeId, updated);
  };

  // Remove Remote Mesh instance
  const handleRemoveRemoteInstance = async (id: string) => {
    const updated = remoteInstances.filter((inst) => inst.id !== id);
    setRemoteInstances(updated);
    await saveRemoteMeshInstances(nodeId, updated);
  };

  // Test remote host connectivity
  const handleTestRemoteHost = async (host: string, model?: string) => {
    try {
      setIsTestingRemote(true);
      const res = await testRemoteMeshInstance(nodeId, host, model);
      setRemoteTestResult(res);
    } catch (err: any) {
      setRemoteTestResult({ online: false, error: err.message });
    } finally {
      setIsTestingRemote(false);
    }
  };

  // Save all settings handler
  const handleSave = async () => {
    try {
      setSaving(true);
      setSaveError(null);
      const payload = {
        node_id: nodeId,
        mode,
        local_model: selectedLocalModel,
        cloud_provider: cloudSlots.fast_chat.provider,
        cloud_model: cloudSlots.fast_chat.model,
        cloud_api_key: cloudSlots.fast_chat.api_key,
        cloud_base_url: cloudSlots.fast_chat.base_url,
        system_prompt: systemPrompt,
        temperature,
        max_tokens: maxTokens,
        fallback_enabled: fallbackEnabled,
        fallback_provider: 'local_ollama',
        cloud_slots: cloudSlots,
        remote_mesh_instances: remoteInstances,
      };

      await saveBrainConfig(nodeId, payload);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  };

  // Run Test Inference
  const handleRunTest = async (overrideRoleSlot?: string) => {
    try {
      setIsTesting(true);
      setTestResult(null);

      let payload: any = {
        prompt: testPrompt,
        mode,
      };

      if (mode === 'local_ollama') {
        payload.host = 'http://127.0.0.1:11434';
        payload.model = selectedLocalModel;
      } else if (mode === 'remote_ollama') {
        const primary = remoteInstances[0];
        payload.host = primary ? primary.host_url : 'http://192.168.1.10:11434';
        payload.model = primary ? primary.model : 'llama3.2:latest';
      } else if (mode === 'cloud_llm') {
        const slotKey = overrideRoleSlot || testSlot;
        const slot = cloudSlots[slotKey as keyof typeof cloudSlots] || cloudSlots.fast_chat;
        payload.cloud_provider = slot.provider;
        payload.cloud_model = slot.model;
        payload.cloud_api_key = slot.api_key;
        payload.cloud_base_url = slot.base_url;
        payload.model = slot.model;
        payload.slot = slotKey;
      }

      const res = await testBrainInference(nodeId, payload);
      setTestResult(res);
    } catch (err: any) {
      setTestResult({
        success: false,
        latency_ms: 0,
        error: err.message,
      });
    } finally {
      setIsTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 w-full flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-4 text-cyan-400">
          <RefreshCw className="w-8 h-8 animate-spin" />
          <span className="text-sm font-mono tracking-widest uppercase">
            Inizializzazione Motore Cognitivo LLM...
          </span>
        </div>
      </div>
    );
  }

  const isLocalReady = localStatus.installed;

  return (
    <div className="w-full min-h-full font-mono text-slate-100 flex flex-col space-y-6">
      {/* Futuristic Banner Header */}
      <div className="relative overflow-hidden rounded-2xl border border-cyan-500/40 bg-slate-900/80 backdrop-blur-xl p-6 shadow-[0_0_35px_rgba(6,182,212,0.15)]">
        <div className="absolute -right-16 -top-16 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="p-3.5 rounded-2xl bg-cyan-500/10 border border-cyan-400/40 text-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.3)]">
              <Brain className="w-8 h-8" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl lg:text-3xl font-extrabold tracking-tight text-white flex items-center gap-2">
                  {t('title')}
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-normal">
                    v5.2 Neural Node
                  </span>
                </h1>
              </div>
              <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
                {t('description')}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {saveSuccess && (
              <span className="text-xs text-emerald-400 flex items-center gap-1.5 bg-emerald-500/15 border border-emerald-500/30 px-3 py-1.5 rounded-lg">
                <CheckCircle2 className="w-4 h-4" />
                {t('saved')}
              </span>
            )}
            {saveError && (
              <span className="text-xs text-rose-400 flex items-center gap-1.5 bg-rose-500/15 border border-rose-500/30 px-3 py-1.5 rounded-lg">
                <AlertTriangle className="w-4 h-4" />
                {saveError}
              </span>
            )}
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs shadow-lg shadow-cyan-600/25 transition cursor-pointer disabled:opacity-50"
            >
              <Save className={`w-4 h-4 ${saving ? 'animate-spin' : ''}`} />
              <span>{saving ? t('saving') : t('save')}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Architecture Tabs: 1) Ollama Locale, 2) Ollama Remoto Mesh, 3) Cloud Provider */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Tab 1: Ollama Locale */}
        <button
          onClick={() => setMode('local_ollama')}
          className={`p-4 rounded-xl border text-left transition flex flex-col justify-between ${
            mode === 'local_ollama'
              ? 'bg-slate-900 border-cyan-500 shadow-[0_0_20px_rgba(6,182,212,0.2)]'
              : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2.5">
              <Cpu className={`w-5 h-5 ${mode === 'local_ollama' ? 'text-cyan-400' : 'text-slate-400'}`} />
              <span className="font-bold text-sm text-white">{t('mode_local')}</span>
            </div>
            {isLocalReady ? (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                INSTALLATO
              </span>
            ) : (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30">
                NON INSTALLATO
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-400 leading-snug">{t('mode_local_desc')}</p>
        </button>

        {/* Tab 2: Ollama Remoto Mesh */}
        <button
          onClick={() => setMode('remote_ollama')}
          className={`p-4 rounded-xl border text-left transition flex flex-col justify-between ${
            mode === 'remote_ollama'
              ? 'bg-slate-900 border-cyan-500 shadow-[0_0_20px_rgba(6,182,212,0.2)]'
              : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2.5">
              <Server className={`w-5 h-5 ${mode === 'remote_ollama' ? 'text-cyan-400' : 'text-slate-400'}`} />
              <span className="font-bold text-sm text-white">{t('mode_remote')}</span>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
              {remoteInstances.length} Istanze
            </span>
          </div>
          <p className="text-[11px] text-slate-400 leading-snug">{t('mode_remote_desc')}</p>
        </button>

        {/* Tab 3: Cloud Provider & API Key */}
        <button
          onClick={() => setMode('cloud_llm')}
          className={`p-4 rounded-xl border text-left transition flex flex-col justify-between ${
            mode === 'cloud_llm'
              ? 'bg-slate-900 border-cyan-500 shadow-[0_0_20px_rgba(6,182,212,0.2)]'
              : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2.5">
              <Cloud className={`w-5 h-5 ${mode === 'cloud_llm' ? 'text-cyan-400' : 'text-slate-400'}`} />
              <span className="font-bold text-sm text-white">{t('mode_cloud')}</span>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              Multi-Ruolo
            </span>
          </div>
          <p className="text-[11px] text-slate-400 leading-snug">{t('mode_cloud_desc')}</p>
        </button>
      </div>

      {/* ================================================================= */}
      {/* MODE 1: OLLAMA LOCALE                                             */}
      {/* ================================================================= */}
      {mode === 'local_ollama' && (
        <div className="space-y-6">
          {/* If NOT Installed: Big Warning + Automated Install Button */}
          {!isLocalReady ? (
            <div className="p-6 rounded-2xl border border-rose-500/40 bg-rose-950/20 backdrop-blur-md flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-[0_0_30px_rgba(244,63,94,0.15)]">
              <div className="flex items-center gap-4">
                <div className="p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/40 text-rose-400 animate-pulse">
                  <AlertTriangle className="w-8 h-8" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">{t('ollama_not_installed')}</h3>
                  <p className="text-xs text-slate-300 mt-1 max-w-xl leading-relaxed">
                    {t('ollama_not_installed_desc')}
                  </p>
                  <p className="text-[11px] text-rose-300/80 mt-1.5 font-semibold">
                    {t('disabled_notice')}
                  </p>
                  {installMsg && (
                    <div className="mt-2 text-xs font-mono text-cyan-300 bg-slate-900/80 px-3 py-1.5 rounded-lg border border-cyan-500/30">
                      {installMsg}
                    </div>
                  )}
                </div>
              </div>

              <button
                onClick={handleInstallOllama}
                disabled={isInstallingOllama}
                className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-emerald-600 hover:from-cyan-500 hover:to-emerald-500 text-white font-bold text-xs shadow-lg shadow-cyan-600/30 transition cursor-pointer disabled:opacity-50 shrink-0"
              >
                <Download className={`w-4 h-4 ${isInstallingOllama ? 'animate-bounce' : ''}`} />
                <span>{isInstallingOllama ? t('installing_ollama') : t('install_ollama_btn')}</span>
              </button>
            </div>
          ) : (
            /* If Installed: Green banner + Uninstall Button */
            <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <div>
                  <div className="text-xs font-bold text-emerald-300 flex items-center gap-2">
                    {t('ollama_installed_ready')}
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-200">
                      v{localStatus.version || '0.4.x'}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {t('ollama_binary_found')}: <code className="text-slate-300">{localStatus.binary_path || '/usr/local/bin/ollama'}</code>
                  </div>
                </div>
              </div>

              <button
                onClick={handleUninstallOllama}
                disabled={isUninstallingOllama}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-rose-500/60 hover:text-rose-400 text-xs text-slate-400 transition cursor-pointer disabled:opacity-50"
                title={t('uninstall_ollama_btn')}
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{isUninstallingOllama ? t('uninstalling_ollama') : t('uninstall_ollama_btn')}</span>
              </button>
            </div>
          )}

          {/* Local Controls (Disabled if not installed) */}
          <div className={`grid grid-cols-1 xl:grid-cols-2 gap-6 transition ${
            !isLocalReady ? 'opacity-35 pointer-events-none select-none blur-[0.5px]' : ''
          }`}>
            {/* Installed Models Select */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 flex flex-col justify-between">
              <div>
                <h3 className="text-sm font-bold text-cyan-300 flex items-center gap-2 mb-2">
                  <Cpu className="w-4 h-4 text-cyan-400" />
                  {t('select_model')}
                </h3>
                <p className="text-xs text-slate-400 mb-4">
                  Scegli il modello attualmente caricato in memoria per l'inferenza del nodo.
                </p>

                <select
                  value={selectedLocalModel}
                  onChange={(e) => setSelectedLocalModel(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  {(localStatus.models.length > 0 ? localStatus.models : localStatus.catalog || []).map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>

              <div className="mt-4 pt-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
                <span>Modelli Rilevati in Locale:</span>
                <span className="font-bold text-cyan-300">{localStatus.models.length}</span>
              </div>
            </div>

            {/* Pull Model Card */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 flex flex-col justify-between">
              <div>
                <h3 className="text-sm font-bold text-cyan-300 flex items-center gap-2 mb-2">
                  <Download className="w-4 h-4 text-cyan-400" />
                  {t('pull_model')}
                </h3>
                <p className="text-xs text-slate-400 mb-4">
                  Scarica modelli open source direttamente dalla libreria Ollama.
                </p>

                <div className="flex gap-2">
                  <input
                    type="text"
                    value={pullInput}
                    onChange={(e) => setPullInput(e.target.value)}
                    placeholder="es. deepseek-r1:1.5b, llama3.2:3b, qwen2.5:1.5b"
                    className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                  <button
                    onClick={() => handlePullModel()}
                    disabled={isPulling || !pullInput.trim()}
                    className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs transition disabled:opacity-50"
                  >
                    {isPulling ? t('pulling') : t('pull_btn')}
                  </button>
                </div>

                {pullFeedback && (
                  <div className="mt-3 text-xs text-cyan-400 font-mono">
                    {pullFeedback}
                  </div>
                )}
              </div>

              {/* Quick Presets */}
              <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap gap-2 items-center">
                <span className="text-[10px] text-slate-500 uppercase tracking-widest">Rapidi:</span>
                {['deepseek-r1:1.5b', 'llama3.2:3b', 'qwen2.5:1.5b', 'mistral:7b'].map((name) => (
                  <button
                    key={name}
                    onClick={() => handlePullModel(name)}
                    disabled={isPulling}
                    className="text-[10px] px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                  >
                    + {name}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* MODE 2: OLLAMA REMOTO SU RETE MESH (MULTI-ISTANZA & COMPITI)      */}
      {/* ================================================================= */}
      {mode === 'remote_ollama' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Server className="w-5 h-5 text-cyan-400" />
                {t('remote_mesh_instances_title')}
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                {t('remote_mesh_instances_desc')}
              </p>
            </div>

            <button
              onClick={() => setIsAddingInstance(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs shadow-md shadow-cyan-600/20 transition cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>{t('add_remote_instance_btn')}</span>
            </button>
          </div>

          {/* Modal / Card to add new instance */}
          {isAddingInstance && (
            <div className="p-6 rounded-2xl border border-cyan-500/50 bg-slate-900/90 backdrop-blur-xl shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-sm font-bold text-cyan-300 flex items-center gap-2">
                  <Plus className="w-4 h-4" />
                  {t('add_remote_instance_btn')}
                </h3>
                <button
                  onClick={() => setIsAddingInstance(false)}
                  className="p-1 rounded text-slate-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">{t('instance_name')}</label>
                  <input
                    type="text"
                    value={newInstanceName}
                    onChange={(e) => setNewInstanceName(e.target.value)}
                    placeholder="es. PC-Workstation-i9"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">{t('instance_host')}</label>
                  <input
                    type="text"
                    value={newInstanceHost}
                    onChange={(e) => setNewInstanceHost(e.target.value)}
                    placeholder="http://192.168.1.10:11434"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">{t('task_label')}</label>
                  <select
                    value={newInstanceTask}
                    onChange={(e) => setNewInstanceTask(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="fast_chat">{t('task_fast_chat')}</option>
                    <option value="deep_reasoning">{t('task_deep_reasoning')}</option>
                    <option value="vision">{t('task_vision')}</option>
                    <option value="coder">{t('task_coder')}</option>
                    <option value="audio_transcription">{t('task_audio')}</option>
                    <option value="embeddings">{t('task_embeddings')}</option>
                    <option value="batch_worker">{t('task_batch')}</option>
                  </select>
                </div>

                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">{t('instance_model')}</label>
                  <input
                    type="text"
                    value={newInstanceModel}
                    onChange={(e) => setNewInstanceModel(e.target.value)}
                    placeholder="llama3.2:latest"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              {remoteTestResult && (
                <div className={`p-3 rounded-lg text-xs font-mono ${
                  remoteTestResult.online
                    ? 'bg-emerald-950/40 border border-emerald-500/30 text-emerald-300'
                    : 'bg-rose-950/40 border border-rose-500/30 text-rose-300'
                }`}>
                  {remoteTestResult.online ? (
                    <div>
                      Connesso con successo in <strong>{remoteTestResult.latency_ms} ms</strong>! Modelli trovati:{' '}
                      {remoteTestResult.models?.join(', ') || 'Nessuno'}
                    </div>
                  ) : (
                    <div>Errore connessione: {remoteTestResult.error}</div>
                  )}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={() => handleTestRemoteHost(newInstanceHost, newInstanceModel)}
                  disabled={isTestingRemote || !newInstanceHost.trim()}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition"
                >
                  <RefreshCw className={`w-3.5 h-3.5 inline mr-1.5 ${isTestingRemote ? 'animate-spin' : ''}`} />
                  {t('instance_ping_test')}
                </button>
                <button
                  onClick={handleAddRemoteInstance}
                  className="px-5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold transition shadow-md shadow-cyan-600/30"
                >
                  Salva Istanza Remota
                </button>
              </div>
            </div>
          )}

          {/* Cards of configured instances */}
          {remoteInstances.length === 0 ? (
            <div className="p-8 rounded-2xl border border-slate-800 bg-slate-900/40 text-center text-slate-500 text-xs">
              {t('no_remote_instances')}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {remoteInstances.map((inst) => {
                const isReasoning = inst.task === 'deep_reasoning';
                const isVision = inst.task === 'vision';
                const isCoder = inst.task === 'coder';
                const isFast = inst.task === 'fast_chat';

                const badgeColor = isReasoning
                  ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                  : isVision
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                  : isCoder
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                  : isFast
                  ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                  : 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40';

                return (
                  <div
                    key={inst.id}
                    className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md flex flex-col justify-between shadow-xl"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <span className="font-bold text-sm text-white truncate max-w-[180px]">
                          {inst.name}
                        </span>
                        <span className={`text-[10px] px-2.5 py-0.5 rounded-full border uppercase tracking-wider font-bold ${badgeColor}`}>
                          {t(`task_${inst.task}`) || inst.task}
                        </span>
                      </div>

                      <div className="space-y-1.5 text-xs text-slate-400">
                        <div className="flex items-center justify-between">
                          <span>Endpoint:</span>
                          <code className="text-cyan-300 font-mono">{inst.host_url}</code>
                        </div>
                        <div className="flex items-center justify-between">
                          <span>Modello:</span>
                          <code className="text-slate-200 font-bold">{inst.model}</code>
                        </div>
                        <div className="flex items-center justify-between">
                          <span>Latenza P2P:</span>
                          <span className="text-emerald-400 font-bold">{inst.latency_ms || 2.4} ms</span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-5 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                      <button
                        onClick={() => handleTestRemoteHost(inst.host_url, inst.model)}
                        className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-semibold"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        <span>Ping</span>
                      </button>

                      <button
                        onClick={() => handleRemoveRemoteInstance(inst.id)}
                        className="text-xs text-rose-400 hover:text-rose-300 flex items-center gap-1 font-semibold"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>{t('remove_instance')}</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ================================================================= */}
      {/* MODE 3: CLOUD PROVIDERS & MULTI-ROLE SPECIALIZED ARCHITECTURE     */}
      {/* ================================================================= */}
      {mode === 'cloud_llm' && (
        <div className="space-y-6">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Cloud className="w-5 h-5 text-indigo-400" />
              {t('cloud_multi_role_title')}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {t('cloud_multi_role_desc')}
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {/* Slot 1: Conversazione Veloce */}
            <div className="p-6 rounded-2xl border border-cyan-500/30 bg-slate-900/60 backdrop-blur-md flex flex-col justify-between shadow-xl">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2.5">
                    <Zap className="w-5 h-5 text-cyan-400" />
                    <div>
                      <h3 className="text-sm font-bold text-white">{t('role_fast_chat')}</h3>
                      <span className="text-[10px] text-cyan-400 font-mono">Target: &lt; 300 ms response</span>
                    </div>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-bold uppercase">
                    Slot Veloce
                  </span>
                </div>

                <div className="space-y-4">
                  {/* Provider Dropdown */}
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">{t('select_provider')}</label>
                    <select
                      value={cloudSlots.fast_chat.provider}
                      onChange={(e) => {
                        const prov = cloudProviders.find((p) => p.id === e.target.value);
                        setCloudSlots((prev) => ({
                          ...prev,
                          fast_chat: {
                            ...prev.fast_chat,
                            provider: e.target.value,
                            base_url: prov?.base_url || prev.fast_chat.base_url,
                            model: prov?.default_model || prev.fast_chat.model,
                          },
                        }));
                      }}
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                    >
                      {cloudProviders.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Cascading Model Dropdown */}
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">{t('select_cloud_model')}</label>
                    <select
                      value={cloudSlots.fast_chat.model}
                      onChange={(e) =>
                        setCloudSlots((prev) => ({
                          ...prev,
                          fast_chat: { ...prev.fast_chat, model: e.target.value },
                        }))
                      }
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                    >
                      {(
                        cloudProviders.find((p) => p.id === cloudSlots.fast_chat.provider)?.models || [
                          'gemini-2.0-flash',
                          'gpt-4o-mini',
                          'llama-3.3-70b-versatile',
                          'claude-3-5-haiku-20241022',
                          'sonar',
                        ]
                      ).map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* API Key */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-[11px] text-slate-400">{t('api_key')}</label>
                      <button
                        type="button"
                        onClick={() => setShowKeys((prev) => ({ ...prev, fast_chat: !prev.fast_chat }))}
                        className="text-[10px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
                      >
                        {showKeys.fast_chat ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                        <span>{showKeys.fast_chat ? 'Nascondi' : 'Mostra'}</span>
                      </button>
                    </div>
                    <input
                      type={showKeys.fast_chat ? 'text' : 'password'}
                      value={cloudSlots.fast_chat.api_key}
                      onChange={(e) =>
                        setCloudSlots((prev) => ({
                          ...prev,
                          fast_chat: { ...prev.fast_chat, api_key: e.target.value },
                        }))
                      }
                      placeholder={t('api_key_placeholder') || 'sk-...'}
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                </div>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-800 flex justify-end">
                <button
                  onClick={() => handleRunTest('fast_chat')}
                  className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-500/40 text-xs font-semibold transition"
                >
                  <Play className="w-3.5 h-3.5 inline mr-1" />
                  {t('test_role_inference')}
                </button>
              </div>
            </div>

            {/* Slot 2: Ragionamento Complesso & Planner */}
            <div className="p-6 rounded-2xl border border-purple-500/30 bg-slate-900/60 backdrop-blur-md flex flex-col justify-between shadow-xl">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2.5">
                    <Sparkles className="w-5 h-5 text-purple-400" />
                    <div>
                      <h3 className="text-sm font-bold text-white">{t('role_deep_reasoning')}</h3>
                      <span className="text-[10px] text-purple-400 font-mono">Cognitive Chain of Thought (CoT)</span>
                    </div>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 font-bold uppercase">
                    Slot Ragionamento
                  </span>
                </div>

                <div className="space-y-4">
                  {/* Provider Dropdown */}
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">{t('select_provider')}</label>
                    <select
                      value={cloudSlots.deep_reasoning.provider}
                      onChange={(e) => {
                        const prov = cloudProviders.find((p) => p.id === e.target.value);
                        setCloudSlots((prev) => ({
                          ...prev,
                          deep_reasoning: {
                            ...prev.deep_reasoning,
                            provider: e.target.value,
                            base_url: prov?.base_url || prev.deep_reasoning.base_url,
                            model: prov?.default_model || prev.deep_reasoning.model,
                          },
                        }));
                      }}
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
                    >
                      {cloudProviders.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Cascading Model Dropdown */}
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">{t('select_cloud_model')}</label>
                    <select
                      value={cloudSlots.deep_reasoning.model}
                      onChange={(e) =>
                        setCloudSlots((prev) => ({
                          ...prev,
                          deep_reasoning: { ...prev.deep_reasoning, model: e.target.value },
                        }))
                      }
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
                    >
                      {(
                        cloudProviders.find((p) => p.id === cloudSlots.deep_reasoning.provider)?.models || [
                          'deepseek-reasoner',
                          'o3-mini',
                          'claude-3-7-sonnet-20250219',
                          'gemini-2.0-pro-exp-02-05',
                          'sonar-reasoning-pro',
                        ]
                      ).map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* API Key */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-[11px] text-slate-400">{t('api_key')}</label>
                      <button
                        type="button"
                        onClick={() => setShowKeys((prev) => ({ ...prev, deep_reasoning: !prev.deep_reasoning }))}
                        className="text-[10px] text-purple-400 hover:text-purple-300 flex items-center gap-1"
                      >
                        {showKeys.deep_reasoning ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                        <span>{showKeys.deep_reasoning ? 'Nascondi' : 'Mostra'}</span>
                      </button>
                    </div>
                    <input
                      type={showKeys.deep_reasoning ? 'text' : 'password'}
                      value={cloudSlots.deep_reasoning.api_key}
                      onChange={(e) =>
                        setCloudSlots((prev) => ({
                          ...prev,
                          deep_reasoning: { ...prev.deep_reasoning, api_key: e.target.value },
                        }))
                      }
                      placeholder={t('api_key_placeholder') || 'sk-...'}
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-purple-500"
                    />
                  </div>
                </div>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-800 flex justify-end">
                <button
                  onClick={() => handleRunTest('deep_reasoning')}
                  className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-purple-300 border border-purple-500/40 text-xs font-semibold transition"
                >
                  <Play className="w-3.5 h-3.5 inline mr-1" />
                  {t('test_role_inference')}
                </button>
              </div>
            </div>

            {/* Slot 3: Visione, Multimodale & OCR */}
            <div className="p-6 rounded-2xl border border-emerald-500/30 bg-slate-900/60 backdrop-blur-md flex flex-col justify-between shadow-xl">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2.5">
                    <Eye className="w-5 h-5 text-emerald-400" />
                    <div>
                      <h3 className="text-sm font-bold text-white">{t('role_vision')}</h3>
                      <span className="text-[10px] text-emerald-400 font-mono">Vision & Camera OCR Multimodal</span>
                    </div>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold uppercase">
                    Slot Visione
                  </span>
                </div>

                <div className="space-y-4">
                  {/* Provider Dropdown */}
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">{t('select_provider')}</label>
                    <select
                      value={cloudSlots.vision.provider}
                      onChange={(e) => {
                        const prov = cloudProviders.find((p) => p.id === e.target.value);
                        setCloudSlots((prev) => ({
                          ...prev,
                          vision: {
                            ...prev.vision,
                            provider: e.target.value,
                            base_url: prov?.base_url || prev.vision.base_url,
                            model: prov?.default_model || prev.vision.model,
                          },
                        }));
                      }}
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                    >
                      {cloudProviders.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Cascading Model Dropdown */}
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">{t('select_cloud_model')}</label>
                    <select
                      value={cloudSlots.vision.model}
                      onChange={(e) =>
                        setCloudSlots((prev) => ({
                          ...prev,
                          vision: { ...prev.vision, model: e.target.value },
                        }))
                      }
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                    >
                      {(
                        cloudProviders.find((p) => p.id === cloudSlots.vision.provider)?.models || [
                          'gpt-4o',
                          'gemini-2.0-flash',
                          'claude-3-7-sonnet-20250219',
                          'pixtral-large-latest',
                          'grok-2-vision-latest',
                        ]
                      ).map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* API Key */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-[11px] text-slate-400">{t('api_key')}</label>
                      <button
                        type="button"
                        onClick={() => setShowKeys((prev) => ({ ...prev, vision: !prev.vision }))}
                        className="text-[10px] text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
                      >
                        {showKeys.vision ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                        <span>{showKeys.vision ? 'Nascondi' : 'Mostra'}</span>
                      </button>
                    </div>
                    <input
                      type={showKeys.vision ? 'text' : 'password'}
                      value={cloudSlots.vision.api_key}
                      onChange={(e) =>
                        setCloudSlots((prev) => ({
                          ...prev,
                          vision: { ...prev.vision, api_key: e.target.value },
                        }))
                      }
                      placeholder={t('api_key_placeholder') || 'sk-...'}
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                </div>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-800 flex justify-end">
                <button
                  onClick={() => handleRunTest('vision')}
                  className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-emerald-500/40 text-xs font-semibold transition cursor-pointer"
                >
                  <Play className="w-3.5 h-3.5 inline mr-1" />
                  {t('test_role_inference')}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* SYSTEM PROMPT, HYPERPARAMETERS & FALLBACK                         */}
      {/* ================================================================= */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        {/* System Prompt (7 Cols) */}
        <div className="xl:col-span-7 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-2">
              <Brain className="w-4 h-4 text-cyan-400" />
              {t('system_prompt')}
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Istruzioni fondamentali, memoria contestuale e regole operative dell'assistente per questo nodo.
            </p>
            <textarea
              rows={4}
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder={t('system_prompt_placeholder') || 'Definisci il ruolo...'}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-slate-200 leading-relaxed focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <span>Caratteri: <strong className="text-cyan-300">{systemPrompt.length}</strong></span>
            <span className="text-[11px] text-slate-500">Persistenza sincronizzata via CRDT</span>
          </div>
        </div>

        {/* Hyperparameters & Fallback (5 Cols) */}
        <div className="xl:col-span-5 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 flex flex-col justify-between space-y-4">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
              <Sliders className="w-4 h-4 text-cyan-400" />
              Parametri di Risposta & Failsafe
            </h3>

            {/* Temperature Slider */}
            <div className="space-y-1.5 mb-4">
              <div className="flex justify-between text-xs text-slate-300">
                <span>{t('temperature')}</span>
                <span className="text-cyan-400 font-bold">{temperature}</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.5"
                step="0.05"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full accent-cyan-400 cursor-pointer"
              />
            </div>

            {/* Max Tokens Slider */}
            <div className="space-y-1.5 mb-4">
              <div className="flex justify-between text-xs text-slate-300">
                <span>{t('max_tokens')}</span>
                <span className="text-purple-400 font-bold">{maxTokens}</span>
              </div>
              <input
                type="range"
                min="256"
                max="8192"
                step="256"
                value={maxTokens}
                onChange={(e) => setMaxTokens(parseInt(e.target.value, 10))}
                className="w-full accent-purple-400 cursor-pointer"
              />
            </div>

            {/* Fallback Checkbox */}
            <label className="flex items-center gap-3 p-3 rounded-xl bg-slate-950/60 border border-slate-800 cursor-pointer hover:border-slate-700 transition">
              <input
                type="checkbox"
                checked={fallbackEnabled}
                onChange={(e) => setFallbackEnabled(e.target.checked)}
                className="w-4 h-4 rounded text-cyan-500 focus:ring-cyan-500/20 bg-slate-900 border-slate-700"
              />
              <span className="text-xs text-slate-300">{t('fallback_toggle')}</span>
            </label>
          </div>
        </div>
      </div>

      {/* ================================================================= */}
      {/* INFERENCE TESTING & LIVE TERMINAL COCKPIT                         */}
      {/* ================================================================= */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 backdrop-blur-md p-6 space-y-4 shadow-2xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <Terminal className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">{t('test_section_title')}</h3>
              <p className="text-xs text-slate-400">{t('term_header')}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {mode === 'cloud_llm' && (
              <select
                value={testSlot}
                onChange={(e) => setTestSlot(e.target.value)}
                className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200"
              >
                <option value="fast_chat">Slot Veloce (Voice)</option>
                <option value="deep_reasoning">Slot Ragionamento (Deep)</option>
              </select>
            )}

            <button
              onClick={() => handleRunTest()}
              disabled={isTesting}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs shadow-lg shadow-cyan-600/30 transition cursor-pointer disabled:opacity-50"
            >
              <Play className={`w-3.5 h-3.5 ${isTesting ? 'animate-spin' : ''}`} />
              <span>{isTesting ? t('testing') : t('test_btn')}</span>
            </button>
          </div>
        </div>

        {/* Input prompt with quick chips */}
        <div className="space-y-2">
          <input
            type="text"
            value={testPrompt}
            onChange={(e) => setTestPrompt(e.target.value)}
            placeholder={t('test_prompt_placeholder') || 'Scrivi domanda test...'}
            className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
          />

          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-[10px] text-slate-500 uppercase tracking-widest">Preset:</span>
            {[
              { label: t('preset_who'), text: 'Chi sei e su quale nodo sei in esecuzione?' },
              { label: t('preset_latency'), text: 'Verifica latenza e calcola 2+2.' },
              { label: t('preset_summary'), text: 'Riassumi lo stato del cluster mesh in una riga.' },
            ].map((p, idx) => (
              <button
                key={idx}
                onClick={() => setTestPrompt(p.text)}
                className="text-[10px] px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Cyberpunk Terminal Window */}
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 font-mono text-xs overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3 text-slate-400 text-[11px]">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <span className="ml-2 text-slate-500">nuxiva-neural-inference-console</span>
            </div>
            {testResult && (
              <div className="flex items-center gap-4">
                <span className="text-cyan-400">
                  {t('latency')}: <strong>{testResult.latency_ms} ms</strong>
                </span>
                {testResult.tokens && (
                  <span className="text-purple-400">
                    {t('tokens')}: <strong>{testResult.tokens}</strong>
                  </span>
                )}
                {testResult.tokens_per_sec && (
                  <span className="text-emerald-400">
                    {t('speed')}: <strong>{testResult.tokens_per_sec} t/s</strong>
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="min-h-[90px] text-slate-300 leading-relaxed whitespace-pre-wrap">
            {isTesting ? (
              <div className="flex items-center gap-2 text-cyan-400 animate-pulse">
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Esecuzione inferenza neurale e misurazione token throughput...</span>
              </div>
            ) : testResult ? (
              testResult.success ? (
                <div className="space-y-2">
                  <div className="text-[11px] text-slate-500">
                    [HOST: {testResult.host || testResult.provider || 'cloud'}] [MODEL: {testResult.model || selectedLocalModel}]
                  </div>
                  <div className="text-slate-100 font-sans text-sm">{testResult.reply}</div>
                </div>
              ) : (
                <div className="text-rose-400">
                  <strong>{t('err_prefix')}:</strong> {testResult.error}
                </div>
              )
            ) : (
              <div className="text-slate-600 italic">{t('term_waiting')}</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default View;
