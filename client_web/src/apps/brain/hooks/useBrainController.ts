import { useEffect, useState } from 'react';
import {
  BrainTargetConfig,
  LlmProvider,
  OllamaMachine,
  DownloadableModel,
  DiscoveredOllamaModel,
  BrainGlobalDefault,
  HostHardwareInfo,
  LocalOllamaStatus,
} from '../types';
import {
  DEFAULT_BRAIN_TARGETS,
  DEFAULT_PROVIDERS,
  DEFAULT_OLLAMA_MACHINES,
  DOWNLOADABLE_MODELS_CATALOG,
  DEFAULT_GLOBAL_BRAIN,
  normalizeOllamaUrl,
  fetchOllamaModels,
  applyDefaultToAllTargets,
} from '../defaults';
import { buildLiveArbiterTarget } from '../arbiterApi';
import { getJson, sendJson } from '../../shared/http';
import { useRemoteServers } from './useRemoteServers';
import { CredentialsDraft } from '../components/ProviderCredentials';

const BRAIN_TARGET_IDS: readonly string[] = ['cognitive_arbiter', 'fast_conversation', 'reasoning', 'live_audio'];

interface PersistedBrainState {
  servers: any[];
  targets: BrainTargetConfig[];
  globalDefault: BrainGlobalDefault | null;
}

export const useBrainController = (t: (key: string) => string) => {
  const [globalDefault, setGlobalDefault] = useState<BrainGlobalDefault>(DEFAULT_GLOBAL_BRAIN);
  const [hydrated, setHydrated] = useState(false);
  const [localModels, setLocalModels] = useState<readonly DiscoveredOllamaModel[]>([]);
  const [targets, setTargets] = useState<readonly BrainTargetConfig[]>(() => [
    buildLiveArbiterTarget(DEFAULT_GLOBAL_BRAIN),
    ...DEFAULT_BRAIN_TARGETS.filter((item) => BRAIN_TARGET_IDS.includes(item.id)),
  ]);
  const [providers, setProviders] = useState<readonly LlmProvider[]>(DEFAULT_PROVIDERS);
  const [machines, setMachines] = useState<readonly OllamaMachine[]>(DEFAULT_OLLAMA_MACHINES);
  const [modelsCatalog] = useState<readonly DownloadableModel[]>(DOWNLOADABLE_MODELS_CATALOG);
  const [activeTarget, setActiveTarget] = useState<BrainTargetConfig | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'simple' | 'advanced'>('simple');
  const [wizardOpen, setWizardOpen] = useState(false);
  const [hardwareInfo, setHardwareInfo] = useState<HostHardwareInfo | null>(null);
  const [ollamaStatus, setOllamaStatus] = useState<LocalOllamaStatus | null>(null);
  const [testRunning, setTestRunning] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; latencyMs: number; message: string } | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((cur) => (cur === msg ? null : cur));
    }, 4000);
  };

  const persistState = (patch: Partial<PersistedBrainState>) => {
    if (!hydrated) return;
    sendJson('/api/v2/brain/state', 'PUT', patch).catch(() => {
      showToast(t('persist_failed'));
    });
  };

  const {
    remoteServers,
    setRemoteServers,
    handleAddRemoteServer,
    handleRemoveRemoteServer,
    handleReloadRemoteModels,
  } = useRemoteServers(persistState, showToast, t);

  useEffect(() => {
    let cancelled = false;
    const hydrate = async () => {
      let saved: PersistedBrainState = { servers: [], targets: [], globalDefault: null };
      let loadedFromServer = false;
      try {
        const res = await getJson<PersistedBrainState>('/api/v2/brain/state');
        saved = {
          servers: Array.isArray(res?.servers) ? res.servers : [],
          targets: Array.isArray(res?.targets) ? res.targets : [],
          globalDefault: res?.globalDefault ?? null,
        };
        loadedFromServer = true;
      } catch {}

      let effectiveGlobal: BrainGlobalDefault | null = saved.globalDefault
        ? { ...DEFAULT_GLOBAL_BRAIN, ...saved.globalDefault }
        : null;
      if (!effectiveGlobal) {
        try {
          const cfg = await getJson<{
            ollama_url?: string;
            active_model?: string;
            active?: { origin?: string; ref?: string };
          }>('/api/v2/brain/config');
          if (cfg?.ollama_url || cfg?.active_model) {
            const url = cfg.ollama_url || DEFAULT_GLOBAL_BRAIN.baseUrl;
            const isLocal = /\/\/(127\.0\.0\.1|localhost|\[::1\])(:|\/|$)/i.test(url);
            effectiveGlobal = {
              ...DEFAULT_GLOBAL_BRAIN,
              provider: cfg.active?.ref?.startsWith('cloud:')
                ? 'api_key'
                : isLocal
                  ? 'ollama_local'
                  : 'ollama_remote',
              serverId: cfg.active?.ref?.startsWith('cloud:')
                ? cfg.active.ref.slice(6).split('/')[0]
                : isLocal
                  ? 'local_workstation'
                  : null,
              baseUrl: url,
              modelName: cfg.active_model || DEFAULT_GLOBAL_BRAIN.modelName,
            };
          }
        } catch {}
      }
      if (cancelled) return;
      const resolvedGlobal = effectiveGlobal || DEFAULT_GLOBAL_BRAIN;
      if (saved.servers.length > 0) setRemoteServers(saved.servers);
      setGlobalDefault(resolvedGlobal);
      setTargets((prev) => {
        const merged = prev.map((dt) => {
          const found = saved.targets.find((p) => p.id === dt.id);
          return found ? { ...dt, ...found } : dt;
        });
        return merged.map((item) =>
          item.id === 'cognitive_arbiter' ? buildLiveArbiterTarget(resolvedGlobal, item) : item
        );
      });
      setHydrated(loadedFromServer);
    };
    void hydrate();

    getJson<{ providers: Array<{ id: string; configured: boolean; base_url?: string }> }>('/api/cloud')
      .then((res) =>
        setProviders((prev) =>
          prev.map((p) => {
            const remote = res.providers.find((v) => v.id === (p.id === 'google' ? 'gemini' : p.id));
            return {
              ...p,
              isConfigured: remote?.configured === true,
              endpointUrl: typeof remote?.base_url === 'string' ? remote.base_url : '',
            };
          })
        )
      )
      .catch(() => {});

    getJson<HostHardwareInfo>('/api/ollama/hardware')
      .then((info) => {
        if (!cancelled && info) setHardwareInfo(info);
      })
      .catch(() => {});

    getJson<LocalOllamaStatus>('/api/ollama/status')
      .then((status) => {
        if (!cancelled && status) setOllamaStatus(status);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setTargets((prev) =>
      prev.map((item) =>
        item.id === 'cognitive_arbiter' ? buildLiveArbiterTarget(globalDefault, item) : item
      )
    );
  }, [globalDefault]);

  useEffect(() => {
    getJson<{
      nodes?: Array<{
        id: string;
        name?: string;
        ip?: string;
        hostname?: string;
        online?: boolean;
        hardware?: { gpu?: string; os?: string };
      }>;
    }>('/api/nodes')
      .then((res) => {
        if (res && Array.isArray(res.nodes)) {
          const realMeshNodes: OllamaMachine[] = res.nodes
            .filter(
              (n) => n.online !== false && n.ip && n.ip !== '127.0.0.1' && n.ip !== 'localhost'
            )
            .map((n) => ({
              id: n.id,
              name: n.name || n.hostname || `Nodo Mesh (${n.ip})`,
              ip: n.ip || 'LAN',
              ramGb: 16,
              cores: 8,
              gpu: n.hardware?.gpu || 'GPU Dedicata',
              vramGb: 8,
              os: n.hardware?.os || 'Linux Node',
              isLocal: false,
              ollamaInstalled: true,
              ollamaVersion: '0.5.8',
              installedModels: [],
            }));

          if (realMeshNodes.length > 0) {
            setMachines((prev) => [...prev.filter((m) => m.isLocal), ...realMeshNodes]);
          }
        }
      })
      .catch(() => {});

    fetchOllamaModels('http://127.0.0.1:11434')
      .then((res) => {
        if (res.models.length > 0) setLocalModels(res.models);
      })
      .catch(() => {});
  }, [globalDefault]);

  useEffect(() => {
    if (!hydrated) return;
    const localCount = targets.filter((tItem) => tItem.method === 'ollama_local').length;
    sendJson('/api/v2/brain/ollama/hibernate', 'POST', {
      local_targets_count: localCount,
      local_host: 'http://127.0.0.1:11434',
    }).catch(() => {});
  }, [targets, hydrated]);

  const saveTargets = (updated: readonly BrainTargetConfig[]) => {
    setTargets(updated);
    persistState({ targets: updated as BrainTargetConfig[] });
  };

  const handleMakeDefaultForAll = async (payload: {
    provider: 'ollama_local' | 'ollama_remote' | 'api_key';
    serverId: string | null;
    baseUrl: string;
    modelName: string;
  }) => {
    if (!hydrated) {
      showToast(t('persist_failed'));
      return;
    }
    if (
      payload.provider === 'api_key' &&
      payload.serverId &&
      !(await handleSaveApiKey(payload.serverId))
    ) {
      return;
    }
    const newGlobal: BrainGlobalDefault = {
      provider: payload.provider,
      serverId: payload.serverId,
      baseUrl:
        payload.provider === 'api_key' ? payload.baseUrl : normalizeOllamaUrl(payload.baseUrl),
      modelName: payload.modelName,
      temperature: 0.7,
      contextWindow: '8192',
      mcpToolsEnabled: [],
    };
    setGlobalDefault(newGlobal);
    const updated = applyDefaultToAllTargets(targets, newGlobal);
    setTargets(updated);
    persistState({ globalDefault: newGlobal, targets: updated as BrainTargetConfig[] });
    try {
      await sendJson('/api/v2/brain/default', 'POST', {
        provider: newGlobal.provider,
        serverId: newGlobal.serverId,
        baseUrl: newGlobal.baseUrl,
        modelName: newGlobal.modelName,
      });
      showToast(t('synced_all_modules'));
    } catch {
      showToast(t('persist_failed'));
    }
  };

  const handleSyncAllModules = async () => {
    await handleMakeDefaultForAll({
      provider: globalDefault.provider,
      serverId: globalDefault.serverId,
      baseUrl: globalDefault.baseUrl,
      modelName: globalDefault.modelName,
    });
  };

  const handleRestoreTargetDefault = (targetId: string) => {
    const updated = targets.map((item) =>
      item.id === targetId ? { ...item, inheritsGlobalDefault: true } : item
    );
    saveTargets(applyDefaultToAllTargets(updated, globalDefault));
    showToast(t('restored_target_default'));
  };

  const handleReloadLocalModels = async () => {
    try {
      const res = await fetchOllamaModels('http://127.0.0.1:11434');
      setLocalModels(res.models);
      showToast(`${t('local_models_reloaded')} (${res.models.length})`);
    } catch {
      showToast(t('connection_failed'));
    }
  };

  const handleUpdateApiKey = (providerId: string, key: string) => {
    setProviders((prev) =>
      prev.map((p) => (p.id === providerId ? { ...p, apiKey: key } : p))
    );
  };

  const handleSaveCredentials = async (
    providerId: string,
    draft: CredentialsDraft
  ): Promise<boolean> => {
    try {
      const remoteId = providerId === 'google' ? 'gemini' : providerId;
      await sendJson('/api/cloud/keys', 'POST', {
        provider: remoteId,
        key: draft.key || '',
        base_url: draft.baseUrl || null,
      });
      setProviders((prev) =>
        prev.map((p) =>
          p.id === providerId
            ? {
                ...p,
                isConfigured: true,
                apiKey: draft.key ?? p.apiKey,
                endpointUrl: draft.baseUrl ?? p.endpointUrl,
              }
            : p
        )
      );
      showToast(t('credentials_saved'));
      return true;
    } catch {
      showToast(t('credentials_save_failed'));
      return false;
    }
  };

  const handleSaveApiKey = async (providerId: string): Promise<boolean> => {
    const prov = providers.find((p) => p.id === providerId);
    if (!prov?.apiKey) {
      showToast(t('api_key_empty'));
      return false;
    }
    return handleSaveCredentials(providerId, { key: prov.apiKey, baseUrl: prov.endpointUrl });
  };

  const handleSaveTarget = async (updatedTarget: BrainTargetConfig) => {
    if (
      updatedTarget.method === 'api_key' &&
      updatedTarget.providerId &&
      !(await handleSaveApiKey(updatedTarget.providerId))
    ) {
      return;
    }
    const updatedList = targets.map((tItem) =>
      tItem.id === updatedTarget.id ? { ...updatedTarget, inheritsGlobalDefault: false } : tItem
    );
    try {
      await sendJson('/api/v2/brain/assignments', 'POST', {
        targetId: updatedTarget.id,
        method: updatedTarget.method,
        assignedModel: updatedTarget.assignedModel,
        providerId: updatedTarget.providerId,
        baseUrl: updatedTarget.baseUrl || updatedTarget.remoteHost,
        mcpTools: updatedTarget.mcpToolsEnabled,
      });
      saveTargets(updatedList);
      setActiveTarget(null);
      showToast(`${t('saved_success_target')} "${updatedTarget.name}"!`);
    } catch {
      showToast(t('persist_failed'));
    }
  };

  const handleRunDiagnosticTest = async () => {
    setTestRunning(true);
    setTestResult(null);
    const start = performance.now();
    try {
      if (globalDefault.provider === 'ollama_local' || globalDefault.provider === 'ollama_remote') {
        const url = globalDefault.baseUrl || 'http://127.0.0.1:11434';
        await fetchOllamaModels(url);
      } else {
        await getJson('/api/cloud');
      }
      const latencyMs = Math.round(performance.now() - start);
      const res = {
        success: true,
        latencyMs,
        message: t('diagnostic_ok'),
      };
      setTestResult(res);
      showToast(`${t('diagnostic_ok')} (${latencyMs} ms)`);
    } catch {
      setTestResult({
        success: false,
        latencyMs: Math.round(performance.now() - start),
        message: t('diagnostic_fail'),
      });
      showToast(t('diagnostic_fail'));
    } finally {
      setTestRunning(false);
    }
  };

  return {
    globalDefault,
    remoteServers,
    hydrated,
    localModels,
    targets,
    providers,
    machines,
    modelsCatalog,
    activeTarget,
    setActiveTarget,
    toastMessage,
    viewMode,
    setViewMode,
    wizardOpen,
    setWizardOpen,
    hardwareInfo,
    ollamaStatus,
    testRunning,
    testResult,
    handleMakeDefaultForAll,
    handleSyncAllModules,
    handleRestoreTargetDefault,
    handleAddRemoteServer,
    handleRemoveRemoteServer,
    handleReloadRemoteModels,
    handleReloadLocalModels,
    handleUpdateApiKey,
    handleSaveApiKey,
    handleSaveCredentials,
    handleSaveTarget,
    handleRunDiagnosticTest,
    showToast,
  };
};
