import React, { useEffect, useState } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import {
  BrainTargetConfig,
  LlmProvider,
  OllamaMachine,
  DownloadableModel,
  RemoteOllamaServer,
  DiscoveredOllamaModel,
  BrainGlobalDefault,
} from './types';
import {
  DEFAULT_BRAIN_TARGETS,
  DEFAULT_PROVIDERS,
  DEFAULT_OLLAMA_MACHINES,
  DOWNLOADABLE_MODELS_CATALOG,
  MCP_TOOLS_CATALOG,
  RECOMMENDED_LOCAL_MODELS,
  DEFAULT_REMOTE_SERVERS,
  DEFAULT_GLOBAL_BRAIN,
  normalizeOllamaUrl,
  fetchOllamaModels,
  applyDefaultToAllTargets,
} from './defaults';
import { buildLiveArbiterTarget } from './arbiterApi';
import { MainDashboard } from './components/MainDashboard';
import { StepWizard } from './components/StepWizard';
import { Brain, CheckCircle2 } from 'lucide-react';
import { getJson, sendJson } from '../shared/http';

interface PersistedBrainState {
  servers: RemoteOllamaServer[];
  targets: BrainTargetConfig[];
  globalDefault: BrainGlobalDefault | null;
}

export const View: React.FC = () => {
  const { t } = useScopedI18n('apps/brain');

  const [globalDefault, setGlobalDefault] = useState<BrainGlobalDefault>(DEFAULT_GLOBAL_BRAIN);
  const [remoteServers, setRemoteServers] =
    useState<readonly RemoteOllamaServer[]>(DEFAULT_REMOTE_SERVERS);
  const [hydrated, setHydrated] = useState(false);
  const [localModels, setLocalModels] = useState<readonly DiscoveredOllamaModel[]>([]);
  const [targets, setTargets] = useState<readonly BrainTargetConfig[]>(() => [
    buildLiveArbiterTarget(DEFAULT_GLOBAL_BRAIN),
    ...DEFAULT_BRAIN_TARGETS,
  ]);
  const [providers, setProviders] = useState<readonly LlmProvider[]>(DEFAULT_PROVIDERS);
  const [machines, setMachines] = useState<readonly OllamaMachine[]>(DEFAULT_OLLAMA_MACHINES);
  const [modelsCatalog] = useState<readonly DownloadableModel[]>(DOWNLOADABLE_MODELS_CATALOG);
  const [activeTarget, setActiveTarget] = useState<BrainTargetConfig | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

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
      setRemoteServers(saved.servers);
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
    getJson<{ providers: Array<{ id: string; configured: boolean }> }>('/api/cloud')
      .then((res) =>
        setProviders((prev) =>
          prev.map((p) => ({
            ...p,
            isConfigured: res.providers.some(
              (v) => v.id === (p.id === 'google' ? 'gemini' : p.id) && v.configured
            ),
          }))
        )
      )
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

    getJson<{ catalog?: Array<{ id: string; name: string; description: string; avatar_icon: string }> }>(
      '/api/v1/agents/catalog'
    )
      .then((res) => {
        if (res && Array.isArray(res.catalog)) {
          setTargets((prev) => {
            const currentIds = new Set(prev.map((item) => item.id));
            const newAgents: BrainTargetConfig[] = [];
            res.catalog?.forEach((cat) => {
              if (!currentIds.has(cat.id)) {
                newAgents.push({
                  id: cat.id,
                  name: cat.name,
                  roleKey: 'agent_custom_role',
                  descriptionKey: 'agent_custom_desc',
                  category: 'agent',
                  method: globalDefault.provider,
                  serverId: globalDefault.serverId,
                  baseUrl: globalDefault.baseUrl,
                  assignedModel: globalDefault.modelName,
                  temperature: globalDefault.temperature,
                  contextWindow: globalDefault.contextWindow,
                  status: 'ready',
                  avatarIcon: 'Brain',
                  accentColor:
                    'from-slate-50 via-white to-slate-100 border border-slate-200 text-slate-800',
                  mcpToolsEnabled: globalDefault.mcpToolsEnabled,
                  inheritsGlobalDefault: true,
                });
              }
            });
            return newAgents.length > 0 ? [...prev, ...newAgents] : prev;
          });
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

  const persistState = (patch: Partial<PersistedBrainState>) => {
    if (!hydrated) return;
    sendJson('/api/v2/brain/state', 'PUT', patch).catch(() => {
      showToast(t('persist_failed'));
    });
  };

  const saveTargets = (updated: readonly BrainTargetConfig[]) => {
    setTargets(updated);
    persistState({ targets: updated as BrainTargetConfig[] });
  };

  const saveRemoteServers = (servers: readonly RemoteOllamaServer[]) => {
    setRemoteServers(servers);
    persistState({ servers: servers as RemoteOllamaServer[] });
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
      temperature: globalDefault.temperature,
      contextWindow: globalDefault.contextWindow,
      mcpToolsEnabled: globalDefault.mcpToolsEnabled,
    };
    const updatedTargets = applyDefaultToAllTargets(targets, payload);
    try {
      await sendJson('/api/v2/brain/assignments/batch', 'POST', {
        ...newGlobal,
        globalDefault: newGlobal,
        targets: updatedTargets,
      });
      setGlobalDefault(newGlobal);
      setTargets(updatedTargets);
      showToast(t('default_applied_success'));
    } catch {
      showToast(t('persist_failed'));
    }
  };

  const handleSyncAllModules = async () => {
    await handleMakeDefaultForAll(globalDefault);
  };

  const handleRestoreTargetDefault = (targetId: string) => {
    const updated = targets.map((target) =>
      target.id === targetId
        ? {
            ...target,
            inheritsGlobalDefault: true,
            method: globalDefault.provider,
            assignedModel: globalDefault.modelName,
            baseUrl: globalDefault.baseUrl,
            temperature: globalDefault.temperature,
            contextWindow: globalDefault.contextWindow,
            mcpToolsEnabled: globalDefault.mcpToolsEnabled,
            status: 'connected' as const,
          }
        : target
    );
    saveTargets(updated);
    showToast(`${t('saved_success_target')} "${targetId}"!`);
  };

  const handleAddRemoteServer = async (rawHost: string, label?: string) => {
    const normalized = normalizeOllamaUrl(rawHost);
    const newId = `remote_${Date.now()}`;
    const newServer: RemoteOllamaServer = {
      id: newId,
      label: label || `Server (${rawHost})`,
      rawInputHost: rawHost,
      normalizedBaseUrl: normalized,
      status: 'checking',
      latencyMs: null,
      lastCheckedAt: null,
      availableModels: [],
      selectedModel: '',
      errorMessage: null,
    };
    const nextList = [...remoteServers, newServer];
    saveRemoteServers(nextList);

    try {
      const probe = await fetchOllamaModels(normalized);
      saveRemoteServers(
        nextList.map((s) =>
          s.id === newId
            ? {
                ...s,
                status: 'online' as const,
                latencyMs: probe.latencyMs,
                availableModels: probe.models,
                selectedModel: probe.models[0]?.name || '',
                lastCheckedAt: new Date().toISOString(),
              }
            : s
        )
      );
    } catch (e: any) {
      saveRemoteServers(
        nextList.map((s) =>
          s.id === newId
            ? { ...s, status: 'offline' as const, errorMessage: String(e?.message || 'Offline') }
            : s
        )
      );
    }
  };

  const handleRemoveRemoteServer = (serverId: string) => {
    saveRemoteServers(remoteServers.filter((s) => s.id !== serverId));
  };

  const handleReloadRemoteModels = async (serverId: string) => {
    const target = remoteServers.find((s) => s.id === serverId);
    if (!target) return;
    try {
      const probe = await fetchOllamaModels(target.normalizedBaseUrl);
      saveRemoteServers(
        remoteServers.map((s) =>
          s.id === serverId
            ? {
                ...s,
                status: 'online' as const,
                latencyMs: probe.latencyMs,
                availableModels: probe.models,
                selectedModel: s.selectedModel || probe.models[0]?.name || '',
                lastCheckedAt: new Date().toISOString(),
                errorMessage: null,
              }
            : s
        )
      );
      showToast(
        probe.models.length > 0
          ? `${probe.models.length} ${t('models_loaded_count')}`
          : t('server_online_running')
      );
    } catch (e: any) {
      saveRemoteServers(
        remoteServers.map((s) =>
          s.id === serverId
            ? { ...s, status: 'offline' as const, errorMessage: String(e?.message || 'Error') }
            : s
        )
      );
    }
  };

  const handleReloadLocalModels = async () => {
    try {
      const probe = await fetchOllamaModels('http://127.0.0.1:11434');
      setLocalModels(probe.models);
      showToast(`${probe.models.length} ${t('models_loaded_count')}`);
    } catch {
      setLocalModels([]);
    }
  };

  const handleUpdateApiKey = (providerId: string, apiKey: string) => {
    setProviders((prev) => prev.map((p) => (p.id === providerId ? { ...p, apiKey } : p)));
  };

  const handleSaveApiKey = async (providerId: string): Promise<boolean> => {
    const draft = providers.find((p) => p.id === providerId)?.apiKey;
    if (draft === undefined) return true;
    try {
      const saved = await sendJson<{ configured: boolean }>(
        `/api/cloud/${providerId === 'google' ? 'gemini' : providerId}`,
        'PUT',
        { key: draft }
      );
      setProviders((prev) =>
        prev.map((p) =>
          p.id === providerId && p.apiKey === draft
            ? { ...p, apiKey: undefined, isConfigured: saved.configured }
            : p
        )
      );
      return true;
    } catch {
      showToast(t('persist_failed'));
      return false;
    }
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

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((cur) => (cur === msg ? null : cur));
    }, 4000);
  };

  return (
    <div className="h-full flex flex-col bg-slate-50 text-slate-900 overflow-hidden select-none font-sans">
      <header className="shrink-0 flex items-center justify-between border-b border-slate-200/90 bg-white/95 backdrop-blur-md px-4 sm:px-6 lg:px-8 py-3.5 shadow-xs z-20">
        <div className="flex items-center gap-3.5">
          <div className="p-2.5 rounded-2xl bg-indigo-600 text-white shadow-md shadow-indigo-600/20 flex items-center justify-center">
            <Brain className="w-5 h-5 stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-base sm:text-lg font-black tracking-tight text-slate-950">
                {t('app_name')}
              </h1>
              <span className="text-[10px] font-black uppercase tracking-widest px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-900 border border-emerald-200 shadow-2xs">
                {t('status_operational')}
              </span>
            </div>
            <p className="text-xs text-slate-600 font-medium leading-none mt-1">
              {t('app_header_desc')}
            </p>
          </div>
        </div>
      </header>

      <main className="flex-1 min-h-0 overflow-y-auto px-4 sm:px-6 lg:px-8 xl:px-10 py-5 pb-32 w-full">
        {toastMessage && (
          <div className="mb-5 p-4 rounded-2xl bg-emerald-50 border border-emerald-300 text-emerald-950 text-xs sm:text-sm font-bold flex items-center gap-3 shadow-md">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span className="flex-1">{toastMessage}</span>
          </div>
        )}

        {activeTarget ? (
          <StepWizard
            target={activeTarget}
            providers={providers}
            machines={machines}
            modelsCatalog={modelsCatalog}
            mcpCatalog={MCP_TOOLS_CATALOG}
            defaultRemoteHost={remoteServers[0]?.rawInputHost || ''}
            defaultRemotePort={11434}
            onUpdateRemoteHost={() => {}}
            onUpdateRemotePort={() => {}}
            onSaveTarget={handleSaveTarget}
            onUpdateApiKey={handleUpdateApiKey}
            onSaveApiKey={handleSaveApiKey}
            onModelInstalledOnMachine={() => {}}
            onCancel={() => setActiveTarget(null)}
            t={t}
          />
        ) : (
          <MainDashboard
            globalDefault={globalDefault}
            targets={targets}
            remoteServers={remoteServers}
            localModels={localModels}
            recommendedModels={RECOMMENDED_LOCAL_MODELS}
            providers={providers}
            mcpCatalog={MCP_TOOLS_CATALOG}
            onMakeDefaultForAll={handleMakeDefaultForAll}
            onSyncAllModules={handleSyncAllModules}
            onSelectTarget={(target) => setActiveTarget(target)}
            onRestoreTargetDefault={handleRestoreTargetDefault}
            onAddRemoteServer={handleAddRemoteServer}
            onRemoveRemoteServer={handleRemoveRemoteServer}
            onReloadRemoteModels={handleReloadRemoteModels}
            onReloadLocalModels={handleReloadLocalModels}
            onUpdateApiKey={handleUpdateApiKey}
            onSaveApiKey={handleSaveApiKey}
            t={t}
          />
        )}
      </main>
    </div>
  );
};
