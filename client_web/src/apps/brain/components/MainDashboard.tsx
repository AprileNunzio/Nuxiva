import React, { useState } from 'react';
import {
  BrainTargetConfig,
  BrainGlobalDefault,
  RemoteOllamaServer,
  DiscoveredOllamaModel,
  RecommendedLocalModel,
  LlmProvider,
  McpToolDefinition,
} from '../types';
import { CredentialsDraft } from './ProviderCredentials';
import { TargetCard } from './TargetCard';
import { ComputeSourceTabs } from './ComputeSourceTabs';
import { ProbabilisticArbiterPanel } from './ProbabilisticArbiterPanel';
import {
  Activity,
  Brain,
  HardDrive,
  Key,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

interface MainDashboardProps {
  readonly globalDefault: BrainGlobalDefault;
  readonly targets: readonly BrainTargetConfig[];
  readonly remoteServers: readonly RemoteOllamaServer[];
  readonly localModels: readonly DiscoveredOllamaModel[];
  readonly recommendedModels: readonly RecommendedLocalModel[];
  readonly providers: readonly LlmProvider[];
  readonly mcpCatalog: readonly McpToolDefinition[];
  readonly onMakeDefaultForAll: (payload: {
    provider: 'ollama_local' | 'ollama_remote' | 'api_key';
    serverId: string | null;
    baseUrl: string;
    modelName: string;
  }) => void;
  readonly onSyncAllModules: () => void;
  readonly onSelectTarget: (target: BrainTargetConfig) => void;
  readonly onRestoreTargetDefault: (targetId: string) => void;
  readonly onAddRemoteServer: (rawHost: string, label?: string) => void;
  readonly onRemoveRemoteServer: (serverId: string) => void;
  readonly onReloadRemoteModels: (serverId: string) => Promise<void>;
  readonly onReloadLocalModels: () => Promise<void>;
  readonly onUpdateApiKey: (providerId: string, apiKey: string) => void;
  readonly onSaveApiKey: (providerId: string) => Promise<boolean>;
  readonly onSaveCredentials: (providerId: string, draft: CredentialsDraft) => Promise<boolean>;
  readonly t: (key: string) => string;
}

export const MainDashboard: React.FC<MainDashboardProps> = ({
  globalDefault,
  targets,
  remoteServers,
  localModels,
  recommendedModels,
  providers,
  onMakeDefaultForAll,
  onSyncAllModules,
  onSelectTarget,
  onRestoreTargetDefault,
  onAddRemoteServer,
  onRemoveRemoteServer,
  onReloadRemoteModels,
  onReloadLocalModels,
  onUpdateApiKey,
  onSaveApiKey,
  onSaveCredentials,
  t,
}) => {
  const [activeTab, setActiveTab] = useState<
    'arbiter_lab' | 'remote_ollama' | 'local_ollama' | 'cloud_api'
  >('arbiter_lab');
  const [filterQuery, setFilterQuery] = useState('');
  const [methodFilter] = useState<'all' | 'api_key' | 'ollama_local' | 'ollama_remote'>('all');

  const localCount = targets.filter((item) => item.method === 'ollama_local').length;

  const filteredTargets = targets.filter((target) => {
    const matchesQuery =
      target.name.toLowerCase().includes(filterQuery.toLowerCase()) ||
      target.assignedModel.toLowerCase().includes(filterQuery.toLowerCase()) ||
      target.id.toLowerCase().includes(filterQuery.toLowerCase());
    const matchesMethod = methodFilter === 'all' || target.method === methodFilter;
    return matchesQuery && matchesMethod;
  });

  return (
    <div className="w-full space-y-8 pb-12">
      <section className="rounded-3xl border-2 border-indigo-200/90 bg-gradient-to-br from-indigo-50/70 via-white to-slate-50 p-6 sm:p-8 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-3">
              <div className="p-2 rounded-xl bg-indigo-600 text-white shadow-xs">
                <Brain className="w-5 h-5" />
              </div>
              <h2 className="text-xl sm:text-2xl font-black text-slate-950 tracking-tight">
                {t('global_brain_header_title')}
              </h2>
              <button
                type="button"
                onClick={() => setActiveTab('arbiter_lab')}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-violet-100 hover:bg-violet-200 text-violet-950 border border-violet-300 shadow-2xs transition"
              >
                <Sparkles className="w-3.5 h-3.5 text-violet-700" />
                {t('arbiter_tab_title')}
              </button>
              {localCount === 0 ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-emerald-100 text-emerald-950 border border-emerald-300 shadow-2xs">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  {t('hibernated_zero_ram_badge')}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-blue-100 text-blue-950 border border-blue-300 shadow-2xs">
                  <Activity className="w-3.5 h-3.5 text-blue-600 animate-pulse" />
                  {t('local_active_badge')} ({localCount})
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs font-medium text-slate-600">
              <div>
                <span className="text-slate-400 font-bold uppercase tracking-wider block text-[10px]">
                  {t('global_model_label')}
                </span>
                <span className="text-sm font-black text-indigo-950">
                  {globalDefault.modelName}
                </span>
              </div>
              <div className="h-6 w-px bg-slate-200 hidden sm:block" />
              <div>
                <span className="text-slate-400 font-bold uppercase tracking-wider block text-[10px]">
                  {t('global_provider_label')}
                </span>
                <span className="text-sm font-black text-slate-900 uppercase">
                  {globalDefault.provider.replace('_', ' ')}
                </span>
              </div>
              <div className="h-6 w-px bg-slate-200 hidden sm:block" />
              <div>
                <span className="text-slate-400 font-bold uppercase tracking-wider block text-[10px]">
                  Endpoint
                </span>
                <span className="text-sm font-bold text-slate-700">{globalDefault.baseUrl}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={onSyncAllModules}
              className="inline-flex items-center gap-2 px-5 py-3 rounded-2xl bg-indigo-600 hover:bg-indigo-700 text-white font-black text-xs sm:text-sm shadow-md shadow-indigo-600/20 transition active:scale-95"
            >
              <RefreshCw className="w-4 h-4" />
              {t('sync_all_modules_btn')}
            </button>
          </div>
        </div>

        {localCount === 0 && (
          <div className="mt-5 p-3.5 rounded-2xl bg-emerald-50/80 border border-emerald-200 text-emerald-950 text-xs font-semibold flex items-center gap-3">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{t('hibernated_zero_ram_desc')}</span>
          </div>
        )}
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 sm:p-8 shadow-xs space-y-6">
        <div className="flex items-center border-b border-slate-200 pb-4 gap-2 sm:gap-4 overflow-x-auto">
          <button
            type="button"
            onClick={() => setActiveTab('arbiter_lab')}
            className={`px-4 py-2.5 rounded-2xl text-xs sm:text-sm font-black transition flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'arbiter_lab'
                ? 'bg-violet-600 text-white border border-violet-700 shadow-xs'
                : 'text-slate-700 hover:bg-violet-50 border border-violet-200'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            {t('arbiter_tab_title')}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('remote_ollama')}
            className={`px-4 py-2.5 rounded-2xl text-xs sm:text-sm font-black transition flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'remote_ollama'
                ? 'bg-purple-100 text-purple-950 border border-purple-300 shadow-2xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Server className="w-4 h-4" />
            {t('remote_ollama_tab')} ({remoteServers.length})
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('local_ollama')}
            className={`px-4 py-2.5 rounded-2xl text-xs sm:text-sm font-black transition flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'local_ollama'
                ? 'bg-emerald-100 text-emerald-950 border border-emerald-300 shadow-2xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <HardDrive className="w-4 h-4" />
            {t('local_ollama_tab')}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('cloud_api')}
            className={`px-4 py-2.5 rounded-2xl text-xs sm:text-sm font-black transition flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'cloud_api'
                ? 'bg-amber-100 text-amber-950 border border-amber-300 shadow-2xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Key className="w-4 h-4" />
            {t('cloud_api_tab')}
          </button>
        </div>

        {activeTab === 'arbiter_lab' ? (
          <ProbabilisticArbiterPanel
            globalDefault={globalDefault}
            targets={targets}
            onSyncAllModules={onSyncAllModules}
            t={t}
          />
        ) : (
          <ComputeSourceTabs
            activeTab={activeTab}
            globalDefault={globalDefault}
            remoteServers={remoteServers}
            localModels={localModels}
            recommendedModels={recommendedModels}
            providers={providers}
            onMakeDefaultForAll={onMakeDefaultForAll}
            onAddRemoteServer={onAddRemoteServer}
            onRemoveRemoteServer={onRemoveRemoteServer}
            onReloadRemoteModels={onReloadRemoteModels}
            onReloadLocalModels={onReloadLocalModels}
            onUpdateApiKey={onUpdateApiKey}
            onSaveApiKey={onSaveApiKey}
            onSaveCredentials={onSaveCredentials}
            t={t}
          />
        )}
      </section>

      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-black text-base text-slate-950">{t('total_assigned')}</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-200 font-bold text-slate-800">
              {filteredTargets.length}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={filterQuery}
                onChange={(e) => setFilterQuery(e.target.value)}
                placeholder={t('search_agent_or_model')}
                className="pl-8 pr-3 py-1.5 rounded-xl text-xs border border-slate-300 bg-white w-48 sm:w-64"
              />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTargets.map((target) => (
            <TargetCard
              key={target.id}
              target={target}
              isHero={target.category === 'core_brain'}
              onConfigure={onSelectTarget}
              onRestoreDefault={onRestoreTargetDefault}
              t={t}
            />
          ))}
        </div>
      </section>
    </div>
  );
};
