import React, { useState } from 'react';
import {
  X,
  Check,
  AlertCircle,
  ArrowRight,
  ArrowLeft,
  Sparkles,
} from 'lucide-react';
import {
  BrainGlobalDefault,
  DiscoveredOllamaModel,
  HostHardwareInfo,
  LlmProvider,
  RemoteOllamaServer,
} from '../types';
import { WizardStep1 } from './wizard/WizardStep1';
import { WizardStep2 } from './wizard/WizardStep2';
import { WizardStep3 } from './wizard/WizardStep3';

interface AutopilotWizardModalProps {
  readonly isOpen: boolean;
  readonly globalDefault: BrainGlobalDefault;
  readonly localModels: readonly DiscoveredOllamaModel[];
  readonly providers: readonly LlmProvider[];
  readonly remoteServers: readonly RemoteOllamaServer[];
  readonly hardwareInfo: HostHardwareInfo | null;
  readonly onClose: () => void;
  readonly onApply: (payload: {
    provider: 'ollama_local' | 'ollama_remote' | 'api_key';
    serverId: string | null;
    baseUrl: string;
    modelName: string;
  }) => Promise<void>;
  readonly onSaveApiKey: (providerId: string, apiKey: string) => Promise<boolean>;
  readonly t: (key: string) => string;
}

export const AutopilotWizardModal: React.FC<AutopilotWizardModalProps> = ({
  isOpen,
  globalDefault,
  localModels,
  providers,
  remoteServers,
  hardwareInfo,
  onClose,
  onApply,
  onSaveApiKey,
  t,
}) => {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [selectedProviderType, setSelectedProviderType] = useState<
    'ollama_local' | 'api_key' | 'ollama_remote'
  >(globalDefault.provider);
  const [selectedCloudProvider, setSelectedCloudProvider] = useState<string>(
    globalDefault.serverId || 'gemini'
  );
  const [apiKeyInput, setApiKeyInput] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>(globalDefault.modelName);
  const [selectedRemoteServerId, setSelectedRemoteServerId] = useState<string>(
    remoteServers[0]?.id || ''
  );
  const [isApplying, setIsApplying] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleNextFromStep1 = () => {
    setErrorMsg(null);
    if (selectedProviderType === 'ollama_local') {
      const defaultRec = hardwareInfo?.profile?.recommended_models?.[0] || 'qwen2.5:7b';
      if (!selectedModel || selectedModel === globalDefault.modelName) {
        setSelectedModel(localModels[0]?.name || defaultRec);
      }
    } else if (selectedProviderType === 'api_key') {
      const prov = providers.find((p) => p.id === selectedCloudProvider);
      if (prov && prov.models[0]) {
        setSelectedModel(prov.models[0].name);
      }
    }
    setStep(2);
  };

  const handleNextFromStep2 = async () => {
    setErrorMsg(null);
    if (selectedProviderType === 'api_key') {
      const prov = providers.find((p) => p.id === selectedCloudProvider);
      if (!prov?.isConfigured && !apiKeyInput.trim()) {
        setErrorMsg(t('wizard_error_api_key_required'));
        return;
      }
      if (apiKeyInput.trim()) {
        const ok = await onSaveApiKey(selectedCloudProvider, apiKeyInput.trim());
        if (!ok) {
          setErrorMsg(t('wizard_error_api_key_invalid'));
          return;
        }
      }
    }
    setStep(3);
  };

  const handleFinish = async () => {
    setIsApplying(true);
    setErrorMsg(null);
    try {
      let baseUrl = 'http://127.0.0.1:11434';
      let serverId: string | null = null;

      if (selectedProviderType === 'api_key') {
        serverId = selectedCloudProvider;
        baseUrl = providers.find((p) => p.id === selectedCloudProvider)?.endpointUrl || '';
      } else if (selectedProviderType === 'ollama_remote') {
        const srv = remoteServers.find((s) => s.id === selectedRemoteServerId);
        baseUrl = srv?.normalizedBaseUrl || 'http://127.0.0.1:11434';
        serverId = srv?.id || null;
      }

      await onApply({
        provider: selectedProviderType,
        serverId,
        baseUrl,
        modelName: selectedModel,
      });
      setCompleted(true);
    } catch {
      setErrorMsg(t('wizard_error_apply_failed'));
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-md">
      <div className="relative w-full max-w-2xl bg-white rounded-3xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div>
            <span className="text-xs font-black uppercase tracking-widest text-indigo-700">
              {t('wizard_modal_subtitle')}
            </span>
            <h3 className="text-lg sm:text-xl font-black text-slate-900 mt-0.5">
              {t('wizard_modal_title')}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-full text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 pt-4 pb-2 border-b border-slate-100 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-xs font-bold">
            <span
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                step >= 1 ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-400'
              }`}
            >
              1
            </span>
            <span className={step === 1 ? 'text-indigo-900 font-black' : 'text-slate-500'}>
              {t('wizard_step_1_title')}
            </span>
          </div>
          <div className="h-0.5 flex-1 bg-slate-200" />
          <div className="flex items-center gap-2 text-xs font-bold">
            <span
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                step >= 2 ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-400'
              }`}
            >
              2
            </span>
            <span className={step === 2 ? 'text-indigo-900 font-black' : 'text-slate-500'}>
              {t('wizard_step_2_title')}
            </span>
          </div>
          <div className="h-0.5 flex-1 bg-slate-200" />
          <div className="flex items-center gap-2 text-xs font-bold">
            <span
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                step >= 3 ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-400'
              }`}
            >
              3
            </span>
            <span className={step === 3 ? 'text-indigo-900 font-black' : 'text-slate-500'}>
              {t('wizard_step_3_title')}
            </span>
          </div>
        </div>

        <div className="p-6 overflow-y-auto flex-1 min-h-[300px]">
          {errorMsg && (
            <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs font-bold flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {step === 1 && (
            <WizardStep1
              selectedProviderType={selectedProviderType}
              onSelectType={setSelectedProviderType}
              t={t}
            />
          )}

          {step === 2 && (
            <WizardStep2
              selectedProviderType={selectedProviderType}
              selectedCloudProvider={selectedCloudProvider}
              apiKeyInput={apiKeyInput}
              selectedModel={selectedModel}
              selectedRemoteServerId={selectedRemoteServerId}
              localModels={localModels}
              providers={providers}
              remoteServers={remoteServers}
              hardwareInfo={hardwareInfo}
              onSelectModel={setSelectedModel}
              onSelectCloudProvider={setSelectedCloudProvider}
              onChangeApiKey={setApiKeyInput}
              onSelectRemoteServerId={setSelectedRemoteServerId}
              t={t}
            />
          )}

          {step === 3 && (
            <WizardStep3
              completed={completed}
              selectedProviderType={selectedProviderType}
              selectedModel={selectedModel}
              t={t}
            />
          )}
        </div>

        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
          {step > 1 && !completed ? (
            <button
              type="button"
              onClick={() => setStep((s) => (s === 3 ? 2 : 1))}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:text-slate-900 transition"
            >
              <ArrowLeft className="w-4 h-4" />
              {t('back_btn')}
            </button>
          ) : (
            <div />
          )}

          {step === 1 && (
            <button
              type="button"
              onClick={handleNextFromStep1}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-extrabold shadow-md shadow-indigo-600/20 transition active:scale-98"
            >
              {t('continue_btn')}
              <ArrowRight className="w-4 h-4" />
            </button>
          )}

          {step === 2 && (
            <button
              type="button"
              onClick={handleNextFromStep2}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-extrabold shadow-md shadow-indigo-600/20 transition active:scale-98"
            >
              {t('continue_btn')}
              <ArrowRight className="w-4 h-4" />
            </button>
          )}

          {step === 3 && (
            completed ? (
              <button
                type="button"
                onClick={onClose}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold shadow-md shadow-emerald-600/20 transition active:scale-98"
              >
                <Check className="w-4 h-4" />
                {t('finish_btn')}
              </button>
            ) : (
              <button
                type="button"
                disabled={isApplying}
                onClick={handleFinish}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-extrabold shadow-md shadow-indigo-600/20 transition active:scale-98"
              >
                <Sparkles className="w-4 h-4" />
                {isApplying ? t('applying_config') : t('apply_all_btn')}
              </button>
            )
          )}
        </div>
      </div>
    </div>
  );
};
