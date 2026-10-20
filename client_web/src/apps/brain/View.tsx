import React, { useEffect, useState } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { BrainTargetConfig, LlmProvider, OllamaMachine, DownloadableModel } from './types';
import {
  DEFAULT_BRAIN_TARGETS,
  DEFAULT_PROVIDERS,
  DEFAULT_OLLAMA_MACHINES,
  DOWNLOADABLE_MODELS_CATALOG,
  MCP_TOOLS_CATALOG,
} from './defaults';
import { MainDashboard } from './components/MainDashboard';
import { StepWizard } from './components/StepWizard';
import { Brain, CheckCircle2, ShieldCheck, Activity } from 'lucide-react';
import { getJson, sendJson } from '../shared/http';

const STORAGE_TARGETS_KEY = 'nuxiva_brain_targets_v4';
const STORAGE_PROVIDERS_KEY = 'nuxiva_brain_providers_v4';
const STORAGE_MACHINES_KEY = 'nuxiva_brain_machines_v4';
const STORAGE_REMOTE_HOST_KEY = 'nuxiva_brain_remote_host';
const STORAGE_REMOTE_PORT_KEY = 'nuxiva_brain_remote_port';

export const View: React.FC = () => {
  const { t } = useScopedI18n('apps/brain');

  const [targets, setTargets] = useState<readonly BrainTargetConfig[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_TARGETS_KEY) || localStorage.getItem('nuxiva_brain_targets_v3');
      if (saved) {
        const parsed: BrainTargetConfig[] = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return DEFAULT_BRAIN_TARGETS.map((dt) => {
            const found = parsed.find((p) => p.id === dt.id);
            return found ? { ...dt, ...found } : dt;
          });
        }
      }
    } catch {}
    return DEFAULT_BRAIN_TARGETS;
  });

  const [providers, setProviders] = useState<readonly LlmProvider[]>(() => {
    // Read across all prior storage versions so no user API keys are ever lost
    const storageKeys = ['nuxiva_brain_providers_v4', 'nuxiva_brain_providers_v3', 'nuxiva_brain_providers_v2', 'nuxiva_brain_providers'];
    let mergedKeys: Record<string, { apiKey?: string; endpointUrl?: string }> = {};
    for (const sKey of storageKeys) {
      try {
        const raw = localStorage.getItem(sKey);
        if (raw) {
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed === 'object') {
            mergedKeys = { ...mergedKeys, ...parsed };
          }
        }
      } catch {}
    }

    return DEFAULT_PROVIDERS.map((p) => {
      const cfg = mergedKeys[p.id];
      const key = cfg?.apiKey ?? p.apiKey ?? '';
      return {
        ...p,
        apiKey: key,
        endpointUrl: cfg?.endpointUrl ?? p.endpointUrl,
        isConfigured: Boolean(key.trim()),
      };
    });
  });

  const [remoteHost, setRemoteHost] = useState<string>(() => {
    try {
      return (
        localStorage.getItem(STORAGE_REMOTE_HOST_KEY) ||
        targets.find((item) => item.remoteHost)?.remoteHost ||
        '192.168.86.143'
      );
    } catch {
      return '192.168.86.143';
    }
  });

  const [remotePort, setRemotePort] = useState<number>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_REMOTE_PORT_KEY);
      return saved ? Number(saved) : 11434;
    } catch {
      return 11434;
    }
  });

  const [machines, setMachines] = useState<readonly OllamaMachine[]>(() => {
    return DEFAULT_OLLAMA_MACHINES;
  });

  const [modelsCatalog] = useState<readonly DownloadableModel[]>(DOWNLOADABLE_MODELS_CATALOG);
  const [activeTarget, setActiveTarget] = useState<BrainTargetConfig | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Sync real nodes from /api/nodes and agents catalog
  useEffect(() => {
    // 1. Fetch real mesh nodes
    getJson<{ nodes?: Array<{ id: string; name?: string; ip?: string; hostname?: string; online?: boolean; hardware?: { gpu?: string; os?: string } }> }>(
      '/api/nodes'
    )
      .then((res) => {
        if (res && Array.isArray(res.nodes)) {
          const realMeshNodes: OllamaMachine[] = res.nodes
            .filter((n) => n.online !== false && n.ip && n.ip !== '127.0.0.1' && n.ip !== 'localhost')
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
              installedModels: ['llama3.3:70b', 'deepseek-r1:70b', 'qwen2.5:7b'],
            }));

          if (realMeshNodes.length > 0) {
            setMachines((prev) => {
              const localOnly = prev.filter((m) => m.isLocal);
              return [...localOnly, ...realMeshNodes];
            });
          }
        }
      })
      .catch(() => {});

    // 2. Fetch custom agents
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
                  method: 'ollama_local',
                  localMachineId: 'local_workstation',
                  assignedModel: 'llama3.2:3b',
                  temperature: 0.2,
                  contextWindow: '128.000 token',
                  status: 'ready',
                  avatarIcon: 'Brain',
                  accentColor: 'from-slate-50 via-white to-slate-100 border border-slate-200 text-slate-800',
                  mcpToolsEnabled: ['mcp_filesystem'],
                });
              }
            });
            return newAgents.length > 0 ? [...prev, ...newAgents] : prev;
          });
        }
      })
      .catch(() => {});
  }, []);

  // Save targets to localStorage
  const saveTargets = (updated: readonly BrainTargetConfig[]) => {
    setTargets(updated);
    try {
      localStorage.setItem(STORAGE_TARGETS_KEY, JSON.stringify(updated));
    } catch {}
  };

  const handleUpdateApiKey = (providerId: string, apiKey: string) => {
    const updated = providers.map((p) => (p.id === providerId ? { ...p, apiKey, isConfigured: Boolean(apiKey.trim()) } : p));
    setProviders(updated);
    try {
      const keysMap: Record<string, { apiKey?: string; endpointUrl?: string }> = {};
      updated.forEach((p) => {
        keysMap[p.id] = { apiKey: p.apiKey, endpointUrl: p.endpointUrl };
      });
      localStorage.setItem(STORAGE_PROVIDERS_KEY, JSON.stringify(keysMap));
      localStorage.setItem('nuxiva_brain_providers_v3', JSON.stringify(keysMap));
    } catch {}
  };

  const handleUpdateRemoteHost = (host: string) => {
    setRemoteHost(host);
    try {
      localStorage.setItem(STORAGE_REMOTE_HOST_KEY, host);
    } catch {}
  };

  const handleUpdateRemotePort = (port: number) => {
    setRemotePort(port);
    try {
      localStorage.setItem(STORAGE_REMOTE_PORT_KEY, String(port));
    } catch {}
  };

  const handleModelInstalledOnMachine = (machineId: string, modelName: string) => {
    const updated = machines.map((m) => {
      if (m.id === machineId) {
        const models = m.installedModels.includes(modelName) ? m.installedModels : [...m.installedModels, modelName];
        return { ...m, installedModels: models };
      }
      return m;
    });
    setMachines(updated);
    try {
      localStorage.setItem(STORAGE_MACHINES_KEY, JSON.stringify(updated));
    } catch {}
  };

  const handleSaveTarget = (updatedTarget: BrainTargetConfig) => {
    const updatedList = targets.map((tItem) => (tItem.id === updatedTarget.id ? updatedTarget : tItem));
    saveTargets(updatedList);
    setActiveTarget(null);

    // Also inform the backend if reachable
    sendJson('/api/v2/brain/assignments', 'POST', {
      targetId: updatedTarget.id,
      method: updatedTarget.method,
      assignedModel: updatedTarget.assignedModel,
      mcpTools: updatedTarget.mcpToolsEnabled,
    }).catch(() => {});

    showToast(`${t('saved_success_target')} "${updatedTarget.name}"!`);
  };

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((cur) => (cur === msg ? null : cur));
    }, 4000);
  };

  return (
    <div className="h-full flex flex-col bg-slate-50 text-slate-900 overflow-hidden select-none font-sans">
      {/* Native Desktop OS Application Toolbar */}
      <header className="shrink-0 flex items-center justify-between border-b border-slate-200/90 bg-white/95 backdrop-blur-md px-4 sm:px-6 lg:px-8 py-3.5 shadow-xs z-20">
        <div className="flex items-center gap-3.5">
          <div className="p-2.5 rounded-2xl bg-indigo-600 text-white shadow-md shadow-indigo-600/20 flex items-center justify-center">
            <Brain className="w-5 h-5 stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-base sm:text-lg font-black tracking-tight text-slate-950">{t('app_name')}</h1>
              <span className="text-[10px] font-black uppercase tracking-widest px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-900 border border-emerald-200 shadow-2xs">
                {t('status_operational')}
              </span>
            </div>
            <p className="text-xs text-slate-600 font-medium leading-none mt-1">{t('app_header_desc')}</p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <div className="hidden sm:flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-slate-200 bg-slate-100/70 text-slate-700">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-semibold text-xs">
              Mesh Hub: <strong className="text-slate-900 font-black">Attivo</strong>
            </span>
          </div>
        </div>
      </header>

      {/* Internal Scroll Area - True Desktop Window Ergonomics */}
      <main className="flex-1 min-h-0 overflow-y-auto px-4 sm:px-6 lg:px-8 xl:px-10 py-5 pb-32 w-full">
        {toastMessage && (
          <div className="mb-5 p-4 rounded-2xl bg-emerald-50 border border-emerald-300 text-emerald-950 text-xs sm:text-sm font-bold flex items-center gap-3 shadow-md animate-in fade-in slide-in-from-top-2 duration-300">
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
            defaultRemoteHost={remoteHost}
            defaultRemotePort={remotePort}
            onUpdateRemoteHost={handleUpdateRemoteHost}
            onUpdateRemotePort={handleUpdateRemotePort}
            onSaveTarget={handleSaveTarget}
            onUpdateApiKey={handleUpdateApiKey}
            onModelInstalledOnMachine={handleModelInstalledOnMachine}
            onCancel={() => setActiveTarget(null)}
            t={t}
          />
        ) : (
          <MainDashboard
            targets={targets}
            onSelectTarget={(target) => setActiveTarget(target)}
            t={t}
          />
        )}
      </main>
    </div>
  );
};
