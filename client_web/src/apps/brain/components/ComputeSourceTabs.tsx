import React, { useState } from 'react';
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Copy,
  Edit3,
  Plus,
  RefreshCw,
  Trash2,
  Zap,
} from 'lucide-react';
import {
  BrainGlobalDefault,
  DiscoveredOllamaModel,
  LlmProvider,
  RecommendedLocalModel,
  RemoteOllamaServer,
} from '../types';

interface ComputeSourceTabsProps {
  readonly activeTab: 'remote_ollama' | 'local_ollama' | 'cloud_api';
  readonly globalDefault: BrainGlobalDefault;
  readonly remoteServers: readonly RemoteOllamaServer[];
  readonly localModels: readonly DiscoveredOllamaModel[];
  readonly recommendedModels: readonly RecommendedLocalModel[];
  readonly providers: readonly LlmProvider[];
  readonly onMakeDefaultForAll: (payload: {
    provider: 'ollama_local' | 'ollama_remote' | 'api_key';
    serverId: string | null;
    baseUrl: string;
    modelName: string;
  }) => void;
  readonly onAddRemoteServer: (rawHost: string, label?: string) => void;
  readonly onRemoveRemoteServer: (serverId: string) => void;
  readonly onReloadRemoteModels: (serverId: string) => Promise<void>;
  readonly onReloadLocalModels: () => Promise<void>;
  readonly onUpdateApiKey: (providerId: string, apiKey: string) => void;
  readonly onSaveApiKey: (providerId: string) => Promise<boolean>;
  readonly t: (key: string) => string;
}

export const ComputeSourceTabs: React.FC<ComputeSourceTabsProps> = ({
  activeTab,
  globalDefault,
  remoteServers,
  localModels,
  recommendedModels,
  providers,
  onMakeDefaultForAll,
  onAddRemoteServer,
  onRemoveRemoteServer,
  onReloadRemoteModels,
  onReloadLocalModels,
  onUpdateApiKey,
  onSaveApiKey,
  t,
}) => {
  const [selectedRemoteId, setSelectedRemoteId] = useState<string>(
    () => remoteServers[0]?.id || 'remote_primary'
  );
  const [newServerIp, setNewServerIp] = useState('');
  const [newServerLabel, setNewServerLabel] = useState('');
  const [selectedRemoteModel, setSelectedRemoteModel] = useState<string>('');
  const [manualModelInput, setManualModelInput] = useState('');
  const [selectedLocalModel, setSelectedLocalModel] = useState<string>(
    () => localModels[0]?.name || globalDefault.modelName
  );
  const [selectedCloudProviderId, setSelectedCloudProviderId] = useState<string>(() => {
    if (globalDefault.provider === 'api_key' && globalDefault.serverId) {
      return globalDefault.serverId;
    }
    return providers[0]?.id || 'google';
  });
  const [selectedCloudModel, setSelectedCloudModel] = useState<string>(() => {
    if (globalDefault.provider === 'api_key' && globalDefault.modelName) {
      return globalDefault.modelName.replace(/^cloud:[^/]+\//, '');
    }
    return providers[0]?.models[0]?.name || '';
  });
  const [isReloading, setIsReloading] = useState(false);
  const [copiedCommand, setCopiedCommand] = useState<string | null>(null);

  const activeRemote =
    remoteServers.find((s) => s.id === selectedRemoteId) || remoteServers[0];
  const topRecommended = recommendedModels[0];

  const handleCopyCommand = (command: string) => {
    navigator.clipboard.writeText(command).catch(() => {});
    setCopiedCommand(command);
    setTimeout(() => {
      setCopiedCommand((prev) => (prev === command ? null : prev));
    }, 2500);
  };

  const handleCreateServer = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newServerIp.trim()) return;
    onAddRemoteServer(newServerIp.trim(), newServerLabel.trim() || undefined);
    setNewServerIp('');
    setNewServerLabel('');
  };

  const handleReloadRemote = async () => {
    if (!activeRemote) return;
    setIsReloading(true);
    try {
      await onReloadRemoteModels(activeRemote.id);
    } finally {
      setIsReloading(false);
    }
  };

  const handleReloadLocal = async () => {
    setIsReloading(true);
    try {
      await onReloadLocalModels();
    } finally {
      setIsReloading(false);
    }
  };

  if (activeTab === 'remote_ollama') {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-5 space-y-4">
          <form
            onSubmit={handleCreateServer}
            className="p-4 rounded-2xl border border-slate-200 bg-slate-50 space-y-3"
          >
            <div className="flex items-center gap-2 font-black text-xs text-slate-800">
              <Plus className="w-3.5 h-3.5" />
              {t('add_server_btn')}
            </div>
            <input
              type="text"
              value={newServerIp}
              onChange={(e) => setNewServerIp(e.target.value)}
              placeholder={t('add_server_ip_placeholder')}
              className="w-full px-3 py-2 rounded-xl text-xs border border-slate-300 bg-white font-mono"
            />
            <input
              type="text"
              value={newServerLabel}
              onChange={(e) => setNewServerLabel(e.target.value)}
              placeholder={t('server_label_placeholder')}
              className="w-full px-3 py-2 rounded-xl text-xs border border-slate-300 bg-white"
            />
            <button
              type="submit"
              className="w-full py-2 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-black text-xs transition"
            >
              {t('add_server_btn')}
            </button>
          </form>

          <div className="space-y-2">
            {remoteServers.map((server) => {
              const isSelected = activeRemote?.id === server.id;
              return (
                <div
                  key={server.id}
                  onClick={() => setSelectedRemoteId(server.id)}
                  className={`p-3.5 rounded-2xl border transition cursor-pointer flex items-center justify-between ${
                    isSelected
                      ? 'border-purple-400 bg-purple-50/70 shadow-2xs'
                      : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-black text-xs text-slate-900">{server.label}</span>
                      {server.status === 'online' ? (
                        <span className="px-2 py-0.5 rounded-full text-[9px] font-black bg-emerald-100 text-emerald-800">
                          Online
                        </span>
                      ) : server.status === 'offline' ? (
                        <span className="px-2 py-0.5 rounded-full text-[9px] font-black bg-rose-100 text-rose-800">
                          Offline
                        </span>
                      ) : null}
                    </div>
                    <div className="text-[11px] font-mono text-slate-600">
                      {server.normalizedBaseUrl}
                    </div>
                    {server.selectedModel && (
                      <div className="text-[10px] font-bold text-purple-700 truncate max-w-[12rem]">
                        {server.selectedModel}
                      </div>
                    )}
                    {server.latencyMs !== null && (
                      <div className="text-[10px] font-bold text-emerald-700">
                        {server.latencyMs} {t('latency_ms')}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRemoveRemoteServer(server.id);
                      }}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 transition"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="lg:col-span-7 p-5 rounded-2xl border border-purple-200 bg-gradient-to-br from-purple-50/30 to-white space-y-5">
          {activeRemote ? (
            <>
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-purple-100 pb-4">
                <div>
                  <h3 className="font-black text-base text-purple-950">{activeRemote.label}</h3>
                  <span className="text-xs font-mono text-slate-600">
                    {activeRemote.normalizedBaseUrl}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleReloadRemote}
                  disabled={isReloading}
                  className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-purple-100 hover:bg-purple-200 text-purple-900 font-bold text-xs transition"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isReloading ? 'animate-spin' : ''}`} />
                  {t('reload_models_btn')}
                </button>
              </div>

              <div className="p-3 rounded-xl bg-purple-50/80 border border-purple-200 flex flex-wrap items-center justify-between gap-2 text-xs">
                <span className="text-purple-900 font-bold">{t('currently_selected_model')}:</span>
                <span className="font-mono font-black text-purple-950 px-2 py-0.5 rounded-lg bg-white border border-purple-200">
                  {selectedRemoteModel ||
                    activeRemote.selectedModel ||
                    activeRemote.availableModels[0]?.name ||
                    manualModelInput.trim() ||
                    globalDefault.modelName ||
                    t('none_selected')}
                </span>
              </div>

              <div className="space-y-3">
                <div className="font-bold text-xs text-slate-700">
                  {t('discovered_models_title')} ({activeRemote.availableModels.length})
                </div>
                {activeRemote.availableModels.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-60 overflow-y-auto">
                    {activeRemote.availableModels.map((m) => {
                      const isSel =
                        (selectedRemoteModel || activeRemote.selectedModel) === m.name;
                      return (
                        <div
                          key={m.name}
                          onClick={() => setSelectedRemoteModel(m.name)}
                          className={`p-3 rounded-xl border text-xs cursor-pointer transition ${
                            isSel
                              ? 'border-purple-600 bg-purple-100/70 font-black text-purple-950'
                              : 'border-slate-200 bg-white hover:border-purple-300 text-slate-800'
                          }`}
                        >
                          <div className="truncate font-bold">{m.name}</div>
                          <div className="text-[10px] text-slate-500 mt-0.5">
                            {m.parameterSize || 'Auto'} • {m.quantizationLevel || 'Q4'}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : activeRemote.status === 'online' ? (
                  <div className="p-4 rounded-2xl bg-emerald-50/90 border border-emerald-200 text-emerald-950 text-xs space-y-2">
                    <div className="flex items-center gap-2 font-bold text-emerald-900">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span>{t('server_online_running')}</span>
                    </div>
                    <p className="text-slate-600 leading-relaxed text-[11px]">
                      {t('server_online_no_models_hint')}
                    </p>
                  </div>
                ) : (
                  <div className="p-4 rounded-2xl bg-amber-50/90 border border-amber-200 text-amber-950 text-xs space-y-2">
                    <div className="flex items-center gap-2 font-bold text-amber-900">
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                      <span>{t('no_models_found')}</span>
                    </div>
                    <p className="text-slate-600 leading-relaxed text-[11px]">
                      {t('ollama_connectivity_hint')}
                    </p>
                  </div>
                )}
              </div>

              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
                <div className="font-bold text-xs text-slate-800 flex items-center gap-2">
                  <Edit3 className="w-3.5 h-3.5 text-purple-600" />
                  <span>{t('manual_model_input_title')}</span>
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={manualModelInput}
                    onChange={(e) => setManualModelInput(e.target.value)}
                    placeholder={t('manual_model_placeholder')}
                    className="flex-1 px-3 py-2 rounded-xl text-xs border border-slate-300 bg-white font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (manualModelInput.trim()) setSelectedRemoteModel(manualModelInput.trim());
                    }}
                    className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs transition"
                  >
                    {t('apply_manual_model_btn')}
                  </button>
                </div>
              </div>

              <button
                type="button"
                onClick={() => {
                  const targetModel =
                    selectedRemoteModel ||
                    manualModelInput.trim() ||
                    activeRemote.selectedModel ||
                    activeRemote.availableModels[0]?.name ||
                    globalDefault.modelName;
                  if (!targetModel) return;
                  onMakeDefaultForAll({
                    provider: 'ollama_remote',
                    serverId: activeRemote.id,
                    baseUrl: activeRemote.normalizedBaseUrl,
                    modelName: targetModel,
                  });
                }}
                className="w-full py-3.5 rounded-2xl bg-purple-600 hover:bg-purple-700 text-white font-black text-xs sm:text-sm shadow-md shadow-purple-600/20 transition flex items-center justify-center gap-2"
              >
                <Zap className="w-4 h-4" />
                {t('make_default_for_all_btn')}
              </button>
            </>
          ) : null}
        </div>
      </div>
    );
  }

  if (activeTab === 'local_ollama') {
    return (
      <div className="space-y-6">
        {topRecommended && (
          <div className="p-6 rounded-3xl border-2 border-emerald-300 bg-gradient-to-br from-emerald-50 via-white to-teal-50 shadow-xs space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-1">
                <h3 className="text-lg sm:text-xl font-black text-slate-950">
                  {topRecommended.name}
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleCopyCommand(topRecommended.cliCommand)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white border border-emerald-300 text-emerald-950 font-bold text-xs hover:bg-emerald-50 transition"
                >
                  {copiedCommand === topRecommended.cliCommand ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                      {t('cli_command_copied')}
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5 text-slate-600" />
                      {t('copy_cli_command')}
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedLocalModel(topRecommended.name);
                    onMakeDefaultForAll({
                      provider: 'ollama_local',
                      serverId: 'local_workstation',
                      baseUrl: 'http://127.0.0.1:11434',
                      modelName: topRecommended.name,
                    });
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-black text-xs shadow-xs transition"
                >
                  <Zap className="w-3.5 h-3.5" />
                  {t('make_default_for_all_btn')}
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50 space-y-3">
            <div className="font-black text-xs text-slate-800">{t('recommended_models_title')}</div>
            <div className="space-y-2">
              {recommendedModels.map((item) => (
                <div
                  key={item.id}
                  className="p-3 rounded-xl border border-slate-200 bg-white flex items-center justify-between text-xs"
                >
                  <div>
                    <div className="font-bold text-slate-900">{item.name}</div>
                    <div className="text-[10px] text-slate-500 font-mono">
                      {item.parameters} • {item.recommendedVramGb}GB VRAM
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleCopyCommand(item.cliCommand)}
                    className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 transition"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50 space-y-3">
            <div className="flex items-center justify-between">
              <div className="font-black text-xs text-slate-800">
                {t('discovered_models_title')} ({localModels.length})
              </div>
              <button
                type="button"
                onClick={handleReloadLocal}
                disabled={isReloading}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-100 text-emerald-950 font-bold text-[11px] transition"
              >
                <RefreshCw className={`w-3 h-3 ${isReloading ? 'animate-spin' : ''}`} />
                {t('reload_models_btn')}
              </button>
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {localModels.map((m) => (
                <div
                  key={m.name}
                  onClick={() => setSelectedLocalModel(m.name)}
                  className={`p-2.5 rounded-xl border text-xs cursor-pointer transition ${
                    selectedLocalModel === m.name
                      ? 'border-emerald-600 bg-emerald-50 font-black text-emerald-950'
                      : 'border-slate-200 bg-white hover:border-slate-300 text-slate-800'
                  }`}
                >
                  <div className="truncate font-bold">{m.name}</div>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={() => {
                const chosen =
                  selectedLocalModel ||
                  localModels[0]?.name ||
                  globalDefault.modelName ||
                  topRecommended?.name;
                if (!chosen) return;
                onMakeDefaultForAll({
                  provider: 'ollama_local',
                  serverId: 'local_workstation',
                  baseUrl: 'http://127.0.0.1:11434',
                  modelName: chosen,
                });
              }}
              className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-black text-xs transition mt-2"
            >
              {t('make_default_for_all_btn')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  const activeProviderObj =
    providers.find((p) => p.id === selectedCloudProviderId) || providers[0];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
      <div className="space-y-3">
        <div className="font-bold text-xs text-slate-700">{t('select_provider_label')}</div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {providers.map((p) => {
            const isSel = selectedCloudProviderId === p.id;
            return (
              <div
                key={p.id}
                onClick={() => {
                  setSelectedCloudProviderId(p.id);
                  if (p.models[0]) setSelectedCloudModel(p.models[0].name);
                }}
                className={`p-3 rounded-xl border text-xs cursor-pointer transition ${
                  isSel
                    ? 'border-amber-500 bg-amber-50 font-black text-amber-950'
                    : 'border-slate-200 bg-white hover:border-slate-300 text-slate-800'
                }`}
              >
                <div className="font-bold truncate">{p.name}</div>
              </div>
            );
          })}
        </div>

        {activeProviderObj && (
          <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50 space-y-3">
            <div className="text-xs font-bold text-slate-800">
              {t('credentials_for')} {activeProviderObj.name}
            </div>
            <input
              type="password"
              value={activeProviderObj.apiKey || ''}
              onChange={(e) => onUpdateApiKey(activeProviderObj.id, e.target.value)}
              onBlur={() => {
                void onSaveApiKey(activeProviderObj.id);
              }}
              placeholder="sk-..."
              className="w-full px-3 py-2 rounded-xl text-xs border border-slate-300 bg-white"
            />
          </div>
        )}
      </div>

      <div className="space-y-4 p-5 rounded-2xl border border-amber-200 bg-amber-50/30">
        <div className="space-y-2">
          <div className="font-bold text-xs text-slate-800">{t('assigned_llm')}</div>
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {(activeProviderObj?.models || []).map((m) => (
              <div
                key={m.id}
                onClick={() => setSelectedCloudModel(m.name)}
                className={`p-2.5 rounded-xl border text-xs cursor-pointer transition ${
                  selectedCloudModel === m.name
                    ? 'border-amber-600 bg-amber-100/70 font-black text-amber-950'
                    : 'border-slate-200 bg-white text-slate-800'
                }`}
              >
                <div className="font-bold">{m.name}</div>
                <div className="text-[10px] text-slate-500">{m.contextWindow}</div>
              </div>
            ))}
          </div>
        </div>

        <button
          type="button"
          onClick={() => {
            const chosenModel =
              selectedCloudModel || activeProviderObj?.models[0]?.name || globalDefault.modelName;
            if (!chosenModel || !activeProviderObj) return;
            onMakeDefaultForAll({
              provider: 'api_key',
              serverId: activeProviderObj.id,
              baseUrl: activeProviderObj.defaultEndpoint || 'https://api.cloud',
              modelName: chosenModel,
            });
          }}
          className="w-full py-3 rounded-2xl bg-amber-600 hover:bg-amber-700 text-white font-black text-xs sm:text-sm shadow-xs transition"
        >
          {t('make_default_for_all_btn')}
        </button>
      </div>
    </div>
  );
};
