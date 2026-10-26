import React, { useState } from 'react';
import {
  BrainTargetConfig,
  ComputeMethod,
  LlmProvider,
  OllamaMachine,
  DownloadableModel,
  McpToolDefinition,
} from '../types';
import { CredentialsDraft } from './ProviderCredentials';
import { StepMethodSelection } from './steps/StepMethodSelection';
import { StepApiKeyConfig } from './steps/StepApiKeyConfig';
import { StepOllamaLocalConfig } from './steps/StepOllamaLocalConfig';
import { StepOllamaRemoteConfig } from './steps/StepOllamaRemoteConfig';
import { StepMcpAndParameters } from './steps/StepMcpAndParameters';
import {
  ArrowLeft,
  ArrowRight,
  Check,
} from 'lucide-react';

interface StepWizardProps {
  readonly target: BrainTargetConfig;
  readonly providers: readonly LlmProvider[];
  readonly machines: readonly OllamaMachine[];
  readonly modelsCatalog: readonly DownloadableModel[];
  readonly mcpCatalog: readonly McpToolDefinition[];
  readonly defaultRemoteHost?: string;
  readonly defaultRemotePort?: number;
  readonly onSaveTarget: (updatedTarget: BrainTargetConfig) => void;
  readonly onUpdateApiKey: (providerId: string, apiKey: string) => void;
  readonly onSaveApiKey: (providerId: string) => Promise<boolean>;
  readonly onSaveCredentials: (providerId: string, draft: CredentialsDraft) => Promise<boolean>;
  readonly onUpdateRemoteHost?: (host: string) => void;
  readonly onUpdateRemotePort?: (port: number) => void;
  readonly onModelInstalledOnMachine: (machineId: string, modelName: string) => void;
  readonly onCancel: () => void;
  readonly t: (key: string) => string;
}

export const StepWizard: React.FC<StepWizardProps> = ({
  target,
  providers,
  machines,
  modelsCatalog,
  mcpCatalog,
  defaultRemoteHost,
  defaultRemotePort,
  onSaveTarget,
  onUpdateApiKey,
  onSaveApiKey,
  onSaveCredentials,
  onUpdateRemoteHost,
  onUpdateRemotePort,
  onModelInstalledOnMachine,
  onCancel,
  t,
}) => {
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);
  const [chosenMethod, setChosenMethod] = useState<ComputeMethod>(target.method);

  // Draft state for Step 2 and Step 3
  const [providerId, setProviderId] = useState<string>(target.providerId || 'google');
  const [customEndpoint, setCustomEndpoint] = useState<string>('');
  const [machineId, setMachineId] = useState<string>(target.localMachineId || machines[0]?.id || 'local_workstation');
  const [remoteHost, setRemoteHost] = useState<string>(target.remoteHost || defaultRemoteHost || '');
  const [remotePort, setRemotePort] = useState<number>(target.remotePort || defaultRemotePort || 11434);
  const [assignedModel, setAssignedModel] = useState<string>(target.assignedModel);
  const [temperature, setTemperature] = useState<number>(target.temperature);
  const [enabledMcpTools, setEnabledMcpTools] = useState<readonly string[]>(target.mcpToolsEnabled);

  const selectedProvider = providers.find((p) => p.id === providerId) || providers[0];

  const handleToggleMcpTool = (toolId: string) => {
    setEnabledMcpTools((prev) =>
      prev.includes(toolId) ? prev.filter((id) => id !== toolId) : [...prev, toolId]
    );
  };

  const handleSelectMethod = (method: ComputeMethod) => {
    setChosenMethod(method);
    if (method === 'api_key') {
      const p = providers.find((pr) => pr.id === providerId) || providers[0];
      if (p.models[0]) {
        setAssignedModel(p.models[0].name);
      } else {
        setAssignedModel('gemini-2.0-flash');
      }
    } else if (method === 'ollama_remote') {
      setAssignedModel('deepseek-r1:70b');
    } else if (method === 'ollama_local') {
      setAssignedModel('qwen2.5-coder:32b');
    }
    setCurrentStep(2);
  };

  const handleSave = () => {
    const updated: BrainTargetConfig = {
      ...target,
      method: chosenMethod,
      assignedModel,
      providerId: chosenMethod === 'api_key' ? providerId : undefined,
      remoteHost: chosenMethod === 'ollama_remote' ? remoteHost : undefined,
      remotePort: chosenMethod === 'ollama_remote' ? remotePort : undefined,
      localMachineId: chosenMethod === 'ollama_local' ? machineId : undefined,
      temperature,
      mcpToolsEnabled: enabledMcpTools,
      status: 'connected',
    };
    onSaveTarget(updated);
  };

  const getMethodSummaryLabel = () => {
    switch (chosenMethod) {
      case 'api_key':
        return `API Key (${selectedProvider?.name || 'Cloud'})`;
      case 'ollama_remote':
        return `Ollama Remoto (${remoteHost}:${remotePort})`;
      case 'ollama_local':
        return `Ollama Locale (${machines.find((m) => m.id === machineId)?.name || 'Questo PC'})`;
    }
  };

  return (
    <div className="w-full space-y-6 pb-12">
      {/* Top Header Card (MD3 Expressive Light Surface) */}
      <div className="w-full rounded-2xl bg-white border border-slate-200/90 p-4 sm:p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <button
            type="button"
            onClick={onCancel}
            className="flex items-center gap-2 px-3.5 py-2 rounded-full border border-slate-300 bg-white hover:bg-slate-50 text-slate-800 font-bold text-xs transition shadow-2xs"
          >
            <ArrowLeft className="w-4 h-4 text-indigo-600" />
            <span>{t('back_to_dashboard')}</span>
          </button>

          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] uppercase font-bold tracking-wider text-slate-500">
                {t('configuring')}:
              </span>
              <h2 className="text-lg sm:text-xl font-black text-slate-950 tracking-tight">
                {target.name}
              </h2>
            </div>
            <p className="text-xs font-semibold text-indigo-700 mt-0.5">
              {t(target.roleKey) || target.name}
            </p>
          </div>
        </div>

        {/* MD3 Expressive Segmented Stepper */}
        <div className="flex items-center gap-1.5 p-1 rounded-full bg-slate-100 border border-slate-200 self-start md:self-auto">
          <button
            type="button"
            onClick={() => setCurrentStep(1)}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all ${
              currentStep === 1
                ? 'bg-indigo-600 text-white shadow-xs font-black'
                : 'text-slate-700 hover:text-slate-950 hover:bg-white/60'
            }`}
          >
            <span className={`w-5 h-5 rounded-full flex items-center justify-center font-black text-[10px] ${currentStep === 1 ? 'bg-white/25 text-white' : 'bg-slate-200 text-slate-800'}`}>
              1
            </span>
            <span>{t('step_1_method')}</span>
          </button>

          <span className="text-slate-300 font-bold">•</span>

          <button
            type="button"
            onClick={() => setCurrentStep(2)}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all ${
              currentStep === 2
                ? 'bg-indigo-600 text-white shadow-xs font-black'
                : 'text-slate-700 hover:text-slate-950 hover:bg-white/60'
            }`}
          >
            <span className={`w-5 h-5 rounded-full flex items-center justify-center font-black text-[10px] ${currentStep === 2 ? 'bg-white/25 text-white' : 'bg-slate-200 text-slate-800'}`}>
              2
            </span>
            <span>{t('step_2_details')}</span>
          </button>

          <span className="text-slate-300 font-bold">•</span>

          <button
            type="button"
            onClick={() => setCurrentStep(3)}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all ${
              currentStep === 3
                ? 'bg-indigo-600 text-white shadow-xs font-black'
                : 'text-slate-700 hover:text-slate-950 hover:bg-white/60'
            }`}
          >
            <span className={`w-5 h-5 rounded-full flex items-center justify-center font-black text-[10px] ${currentStep === 3 ? 'bg-white/25 text-white' : 'bg-slate-200 text-slate-800'}`}>
              3
            </span>
            <span>{t('step_3_mcp')}</span>
          </button>
        </div>
      </div>

      {/* Main Step Content Container */}
      <div className="w-full min-h-[460px]">
        {currentStep === 1 && (
          <StepMethodSelection
            target={target}
            selectedMethod={chosenMethod}
            onSelectMethod={handleSelectMethod}
            t={t}
          />
        )}

        {currentStep === 2 && (
          <div className="space-y-5 w-full">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3.5 p-4 rounded-2xl bg-white border border-slate-200/90 shadow-2xs">
              <div>
                <h3 className="text-lg sm:text-xl font-black text-slate-950 tracking-tight">
                  {chosenMethod === 'api_key' && t('api_step_title')}
                  {chosenMethod === 'ollama_local' && t('local_step_title')}
                  {chosenMethod === 'ollama_remote' && t('remote_step_title')}
                </h3>
                <p className="text-xs font-medium text-slate-600 mt-0.5">
                  {chosenMethod === 'api_key' && t('api_step_desc')}
                  {chosenMethod === 'ollama_local' && t('local_step_desc')}
                  {chosenMethod === 'ollama_remote' && t('remote_step_desc')}
                </p>
              </div>

              <div className="flex items-center gap-2.5 shrink-0">
                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="px-3.5 py-1.5 rounded-full border border-slate-300 bg-white text-xs font-bold text-slate-800 hover:bg-slate-50 transition shadow-2xs"
                >
                  {t('change_method_btn')}
                </button>
                <button
                  type="button"
                  onClick={() => setCurrentStep(3)}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-xs transition"
                >
                  <span>{t('continue_to_mcp_btn')}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {chosenMethod === 'api_key' && (
              <StepApiKeyConfig
                providers={providers}
                selectedProviderId={providerId}
                onSelectProvider={setProviderId}
                onSaveCredentials={onSaveCredentials}
                selectedModelId={assignedModel}
                onSelectModel={(_id, name) => setAssignedModel(name)}
                t={t}
              />
            )}

            {chosenMethod === 'ollama_local' && (
              <StepOllamaLocalConfig
                machines={machines}
                selectedMachineId={machineId}
                onSelectMachine={setMachineId}
                catalog={modelsCatalog}
                selectedModelName={assignedModel}
                onSelectModel={setAssignedModel}
                onModelInstalled={onModelInstalledOnMachine}
                t={t}
              />
            )}

            {chosenMethod === 'ollama_remote' && (
              <StepOllamaRemoteConfig
                remoteHost={remoteHost}
                onUpdateRemoteHost={(host) => {
                  setRemoteHost(host);
                  onUpdateRemoteHost?.(host);
                }}
                remotePort={remotePort}
                onUpdateRemotePort={(port) => {
                  setRemotePort(port);
                  onUpdateRemotePort?.(port);
                }}
                selectedModelName={assignedModel}
                onSelectModel={setAssignedModel}
                t={t}
              />
            )}
          </div>
        )}

        {currentStep === 3 && (
          <div className="space-y-5 w-full">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3.5 p-4 rounded-2xl bg-white border border-slate-200/90 shadow-2xs">
              <div>
                <h3 className="text-lg sm:text-xl font-black text-slate-950 tracking-tight">{t('step_3_title')}</h3>
                <p className="text-xs font-medium text-slate-600 mt-0.5">{t('step_3_desc')}</p>
              </div>
              <button
                type="button"
                onClick={() => setCurrentStep(2)}
                className="px-3.5 py-1.5 rounded-full border border-slate-300 bg-white text-xs font-bold text-slate-800 hover:bg-slate-50 transition shadow-2xs shrink-0"
              >
                {t('back_to_model_step')}
              </button>
            </div>

            <StepMcpAndParameters
              target={target}
              temperature={temperature}
              onUpdateTemperature={setTemperature}
              mcpCatalog={mcpCatalog}
              enabledMcpTools={enabledMcpTools}
              onToggleMcpTool={handleToggleMcpTool}
              assignedModelName={assignedModel}
              methodLabel={getMethodSummaryLabel()}
              onConfirmSave={handleSave}
              t={t}
            />
          </div>
        )}
      </div>

      {/* Floating Bottom Navigation Bar */}
      <div className="w-full p-3.5 rounded-2xl bg-white border border-slate-200/90 shadow-xs flex items-center justify-between">
        <button
          type="button"
          onClick={() => {
            if (currentStep > 1) {
              setCurrentStep((prev) => (prev - 1) as any);
            } else {
              onCancel();
            }
          }}
          className="flex items-center gap-2 px-4 py-2 rounded-full border border-slate-300 bg-white text-xs sm:text-sm font-bold text-slate-800 hover:bg-slate-50 transition shadow-2xs"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>{currentStep === 1 ? t('cancel') : t('previous_step')}</span>
        </button>

        {currentStep < 3 ? (
          <button
            type="button"
            onClick={() => setCurrentStep((prev) => (prev + 1) as any)}
            className="flex items-center gap-2 px-5 py-2 rounded-full text-xs sm:text-sm font-black bg-indigo-600 hover:bg-indigo-700 text-white transition shadow-sm"
          >
            <span>{t('next_step')}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        ) : (
          <button
            type="button"
            onClick={handleSave}
            className="flex items-center gap-2 px-6 py-2 rounded-full text-xs sm:text-sm font-black bg-emerald-600 hover:bg-emerald-700 text-white transition shadow-sm"
          >
            <Check className="w-4 h-4 stroke-[3]" />
            <span>{t('confirm_and_save')}</span>
          </button>
        )}
      </div>
    </div>
  );
};
