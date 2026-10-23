import React, { useState } from 'react';
import { LlmProvider } from '../../types';
import { CredentialsDraft, ProviderCredentials } from '../ProviderCredentials';
import {
  Key,
  Globe,
  Sparkles,
  Cpu,
  Zap,
  Flame,
  ShieldCheck,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  Network,
  Loader2,
  Check,
  Layers,
} from 'lucide-react';

interface StepApiKeyConfigProps {
  readonly providers: readonly LlmProvider[];
  readonly selectedProviderId: string;
  readonly onSelectProvider: (providerId: string) => void;
  readonly onSaveCredentials: (providerId: string, draft: CredentialsDraft) => Promise<boolean>;
  readonly selectedModelId: string;
  readonly onSelectModel: (modelId: string, modelName: string) => void;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

export const StepApiKeyConfig: React.FC<StepApiKeyConfigProps> = ({
  providers,
  selectedProviderId,
  onSelectProvider,
  onSaveCredentials,
  selectedModelId,
  onSelectModel,
  t,
}) => {
  const [customModelInput, setCustomModelInput] = useState('');

  const currentProvider = providers.find((p) => p.id === selectedProviderId) || providers[0];

  const renderProviderIcon = (iconName: string) => {
    switch (iconName) {
      case 'Sparkles':
        return <Sparkles className="w-5 h-5 text-amber-600" />;
      case 'Cpu':
        return <Cpu className="w-5 h-5 text-indigo-600" />;
      case 'Globe':
        return <Globe className="w-5 h-5 text-emerald-600" />;
      case 'Zap':
        return <Zap className="w-5 h-5 text-blue-600" />;
      case 'Flame':
        return <Flame className="w-5 h-5 text-rose-600" />;
      case 'ShieldCheck':
        return <ShieldCheck className="w-5 h-5 text-indigo-600" />;
      case 'Eye':
        return <Eye className="w-5 h-5 text-purple-600" />;
      case 'Layers':
        return <Layers className="w-5 h-5 text-teal-600" />;
      default:
        return <Network className="w-5 h-5 text-slate-600" />;
    }
  };

  return (
    <div className="w-full space-y-7">
      {/* 1. Selezione Provider Cloud (Grid reattiva 16 provider reali) */}
      <div className="space-y-2.5 w-full">
        <label className="text-xs uppercase font-extrabold tracking-wider text-slate-700 block">
          1. {t('select_provider_label')} ({t('supported_cloud_services', { count: providers.length })})
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2.5 w-full">
          {providers.map((p) => {
            const isSelected = p.id === currentProvider.id;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => {
                  onSelectProvider(p.id);
                  if (p.models.length > 0) {
                    onSelectModel(p.models[0].id, p.models[0].name);
                  }
                                  }}
                className={`flex flex-col items-center justify-center p-3 rounded-2xl border text-center transition-all ${
                  isSelected
                    ? 'bg-amber-100 text-amber-950 font-black border-2 border-amber-400 shadow-xs ring-2 ring-amber-200'
                    : 'bg-white border-slate-200/90 hover:border-slate-300 hover:bg-slate-50 text-slate-800 shadow-2xs'
                }`}
              >
                <div className={`p-2 rounded-xl mb-1.5 transition-transform ${isSelected ? 'bg-white border border-amber-300' : 'bg-slate-50 border border-slate-200'}`}>
                  {renderProviderIcon(p.iconName)}
                </div>
                <div className="text-xs font-black truncate w-full">{p.name}</div>
                <div className={`text-[10px] mt-0.5 font-bold ${isSelected ? 'text-amber-950' : 'text-slate-500'}`}>
                  {p.models.length} modelli
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <ProviderCredentials provider={currentProvider} onSave={onSaveCredentials} t={t} />

      {/* 3. Selezione Modello Reale del Provider (Full-width Responsive Grid) */}
      <div className="space-y-4 w-full">
        <label className="text-xs uppercase font-extrabold tracking-wider text-slate-700 block">
          3. {t('select_model_catalog_for')} {currentProvider.name}
        </label>

        {/* Input personalizzabile per impostare qualsiasi modello liberamente */}
        <div className="p-4 rounded-2xl border-2 border-amber-300/80 bg-white shadow-xs space-y-2">
          <label className="text-xs font-black text-slate-900 flex items-center justify-between">
            <span>{t('assigned_model_hint')}</span>
            <span className="text-[11px] font-mono font-bold text-amber-900 bg-amber-50 px-2.5 py-0.5 rounded-md border border-amber-200">
              Attivo: {selectedModelId || 'Nessuno'}
            </span>
          </label>
          <div className="flex flex-col sm:flex-row items-center gap-2.5">
            <input
              type="text"
              value={selectedModelId}
              onChange={(e) => onSelectModel(e.target.value, e.target.value)}
              placeholder={t('assigned_model_placeholder', { provider: currentProvider.name })}
              className="flex-1 w-full px-3.5 py-2.5 text-xs sm:text-sm font-mono font-bold rounded-xl bg-slate-50 border border-slate-300 text-slate-950 focus:outline-none focus:border-amber-500 focus:bg-white focus:ring-2 focus:ring-amber-100"
            />
            {selectedModelId && (
              <span className="text-xs font-black text-amber-900 flex items-center gap-1.5 px-3 py-2 rounded-xl bg-amber-50 border border-amber-200">
                <Check className="w-4 h-4 stroke-[3]" />
                Assegnato
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3.5 w-full">
          {currentProvider.models.map((model) => {
            const isSelected = selectedModelId === model.id || selectedModelId === model.name || selectedModelId.endsWith(model.name);
            return (
              <div
                key={model.id}
                onClick={() => onSelectModel(model.id, model.name)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelectModel(model.id, model.name);
                  }
                }}
                className={`p-5 rounded-2xl border transition-all text-left cursor-pointer flex flex-col justify-between min-h-[170px] ${
                  isSelected
                    ? 'bg-gradient-to-br from-amber-50/80 via-white to-amber-50/30 border-2 border-amber-400 ring-2 ring-amber-200 shadow-xs'
                    : 'bg-white border-slate-200/90 hover:border-slate-300 hover:bg-slate-50/80 shadow-2xs'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-sm sm:text-base font-black text-slate-950">{model.name}</h4>
                    {isSelected && (
                      <span className="p-1 rounded-full bg-amber-500 text-white shrink-0">
                        <Check className="w-3.5 h-3.5 stroke-[3]" />
                      </span>
                    )}
                  </div>

                  <p className="text-xs font-medium text-slate-600 mt-1.5 line-clamp-3 leading-relaxed">
                    {model.notes}
                  </p>
                </div>

                <div className="mt-3.5 pt-2.5 border-t border-slate-200/90 flex items-center justify-between text-xs font-bold text-slate-600">
                  <span className="text-indigo-700 font-black">{model.contextWindow}</span>
                  <span>{model.latencyMs} ms</span>
                  {model.speedTokensSec && <span className="text-emerald-700 font-bold">{model.speedTokensSec} t/s</span>}
                </div>
              </div>
            );
          })}
        </div>

        {/* Custom model tag bar */}
        <div className="p-3.5 rounded-2xl border border-slate-200/90 bg-white shadow-2xs flex flex-col sm:flex-row items-center gap-2.5">
          <input
            type="text"
            placeholder={t('custom_model_tag_placeholder')}
            value={customModelInput}
            onChange={(e) => setCustomModelInput(e.target.value)}
            className="flex-1 w-full px-3.5 py-2 text-xs font-mono rounded-xl bg-slate-50 border border-slate-300 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-amber-500"
          />
          <button
            type="button"
            onClick={() => {
              if (customModelInput.trim()) {
                onSelectModel(customModelInput.trim(), customModelInput.trim());
                setCustomModelInput('');
              }
            }}
            className="w-full sm:w-auto px-4 py-2 text-xs font-bold rounded-xl bg-slate-900 hover:bg-slate-800 text-white transition shrink-0 shadow-2xs"
          >
            {t('use_custom_model_btn')}
          </button>
        </div>
      </div>
    </div>
  );
};
