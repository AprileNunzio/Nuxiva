import React from 'react';
import { Cpu, DownloadCloud, Key } from 'lucide-react';
import { DiscoveredOllamaModel, HostHardwareInfo, LlmProvider, RemoteOllamaServer } from '../../types';

interface WizardStep2Props {
  readonly selectedProviderType: 'ollama_local' | 'api_key' | 'ollama_remote';
  readonly selectedCloudProvider: string;
  readonly apiKeyInput: string;
  readonly selectedModel: string;
  readonly selectedRemoteServerId: string;
  readonly localModels: readonly DiscoveredOllamaModel[];
  readonly providers: readonly LlmProvider[];
  readonly remoteServers: readonly RemoteOllamaServer[];
  readonly hardwareInfo: HostHardwareInfo | null;
  readonly onSelectModel: (name: string) => void;
  readonly onSelectCloudProvider: (id: string) => void;
  readonly onChangeApiKey: (key: string) => void;
  readonly onSelectRemoteServerId: (id: string) => void;
  readonly t: (key: string) => string;
}

export const WizardStep2: React.FC<WizardStep2Props> = ({
  selectedProviderType,
  selectedCloudProvider,
  apiKeyInput,
  selectedModel,
  selectedRemoteServerId,
  localModels,
  providers,
  remoteServers,
  hardwareInfo,
  onSelectModel,
  onSelectCloudProvider,
  onChangeApiKey,
  onSelectRemoteServerId,
  t,
}) => {
  return (
    <div className="space-y-4">
      {selectedProviderType === 'ollama_local' && (
        <div>
          <h4 className="text-sm font-black text-slate-900 mb-1">
            {t('wizard_choose_local_model_title')}
          </h4>
          <p className="text-xs text-slate-500 mb-3">
            {t('wizard_choose_local_model_desc')}
          </p>
          {localModels.length > 0 ? (
            <div className="space-y-2">
              {localModels.map((m) => (
                <div
                  key={m.name}
                  onClick={() => onSelectModel(m.name)}
                  className={`p-3.5 rounded-xl border flex items-center justify-between cursor-pointer transition ${
                    selectedModel === m.name
                      ? 'border-indigo-600 bg-indigo-50/40 font-bold'
                      : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Cpu className="w-4 h-4 text-indigo-600" />
                    <span className="text-sm">{m.name}</span>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">
                    {m.parameterSize || 'Standard'}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200">
              <div className="flex items-start gap-3">
                <DownloadCloud className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-black text-amber-950 uppercase">
                    {t('wizard_no_models_installed_title')}
                  </div>
                  <p className="text-xs text-amber-800 mt-1">
                    {t('wizard_no_models_installed_desc')}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {hardwareInfo?.profile?.recommended_models?.map((rec) => (
                      <button
                        key={rec}
                        type="button"
                        onClick={() => onSelectModel(rec)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition ${
                          selectedModel === rec
                            ? 'bg-indigo-600 text-white border-indigo-600'
                            : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
                        }`}
                      >
                        {rec}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {selectedProviderType === 'api_key' && (
        <div className="space-y-4">
          <div>
            <label className="text-xs font-black uppercase text-slate-700 block mb-1">
              {t('wizard_select_provider_label')}
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {providers.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => {
                    onSelectCloudProvider(p.id);
                    if (p.models[0]) onSelectModel(p.models[0].name);
                  }}
                  className={`p-2.5 rounded-xl border text-xs font-bold truncate transition ${
                    selectedCloudProvider === p.id
                      ? 'border-indigo-600 bg-indigo-50 text-indigo-900'
                      : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  {p.name}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs font-black uppercase text-slate-700 block mb-1">
              {t('wizard_api_key_label')}
            </label>
            <div className="relative">
              <Key className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="password"
                value={apiKeyInput}
                onChange={(e) => onChangeApiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full pl-9 pr-3 py-2 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 font-mono"
              />
            </div>
          </div>
        </div>
      )}

      {selectedProviderType === 'ollama_remote' && (
        <div className="space-y-3">
          <label className="text-xs font-black uppercase text-slate-700 block mb-1">
            {t('wizard_select_remote_server')}
          </label>
          {remoteServers.map((s) => (
            <div
              key={s.id}
              onClick={() => onSelectRemoteServerId(s.id)}
              className={`p-3.5 rounded-xl border flex items-center justify-between cursor-pointer transition ${
                selectedRemoteServerId === s.id
                  ? 'border-indigo-600 bg-indigo-50 text-indigo-900 font-bold'
                  : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
              }`}
            >
              <span className="text-sm">{s.label || s.normalizedBaseUrl}</span>
              <span className="text-xs text-slate-400 font-mono">{s.normalizedBaseUrl}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
