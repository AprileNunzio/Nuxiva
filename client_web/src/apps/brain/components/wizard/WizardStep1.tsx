import React from 'react';
import { Shield, Zap, Server } from 'lucide-react';

interface WizardStep1Props {
  readonly selectedProviderType: 'ollama_local' | 'api_key' | 'ollama_remote';
  readonly onSelectType: (type: 'ollama_local' | 'api_key' | 'ollama_remote') => void;
  readonly t: (key: string) => string;
}

export const WizardStep1: React.FC<WizardStep1Props> = ({
  selectedProviderType,
  onSelectType,
  t,
}) => {
  return (
    <div className="space-y-4">
      <p className="text-xs sm:text-sm text-slate-600 font-medium">
        {t('wizard_step_1_desc')}
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 pt-2">
        <button
          type="button"
          onClick={() => onSelectType('ollama_local')}
          className={`p-4 rounded-2xl border text-left transition flex flex-col justify-between ${
            selectedProviderType === 'ollama_local'
              ? 'border-indigo-600 bg-indigo-50/50 ring-2 ring-indigo-600/20'
              : 'border-slate-200 bg-white hover:border-slate-300'
          }`}
        >
          <div>
            <div className="w-9 h-9 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center mb-3">
              <Shield className="w-5 h-5" />
            </div>
            <div className="text-sm font-black text-slate-900">
              {t('wizard_opt_local_title')}
            </div>
            <p className="text-xs text-slate-500 font-medium mt-1 leading-relaxed">
              {t('wizard_opt_local_desc')}
            </p>
          </div>
          <span className="mt-4 text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md inline-block w-fit">
            {t('badge_private_free')}
          </span>
        </button>

        <button
          type="button"
          onClick={() => onSelectType('api_key')}
          className={`p-4 rounded-2xl border text-left transition flex flex-col justify-between ${
            selectedProviderType === 'api_key'
              ? 'border-indigo-600 bg-indigo-50/50 ring-2 ring-indigo-600/20'
              : 'border-slate-200 bg-white hover:border-slate-300'
          }`}
        >
          <div>
            <div className="w-9 h-9 rounded-xl bg-indigo-100 text-indigo-800 flex items-center justify-center mb-3">
              <Zap className="w-5 h-5" />
            </div>
            <div className="text-sm font-black text-slate-900">
              {t('wizard_opt_cloud_title')}
            </div>
            <p className="text-xs text-slate-500 font-medium mt-1 leading-relaxed">
              {t('wizard_opt_cloud_desc')}
            </p>
          </div>
          <span className="mt-4 text-[10px] font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-md inline-block w-fit">
            {t('badge_ultra_fast')}
          </span>
        </button>

        <button
          type="button"
          onClick={() => onSelectType('ollama_remote')}
          className={`p-4 rounded-2xl border text-left transition flex flex-col justify-between ${
            selectedProviderType === 'ollama_remote'
              ? 'border-indigo-600 bg-indigo-50/50 ring-2 ring-indigo-600/20'
              : 'border-slate-200 bg-white hover:border-slate-300'
          }`}
        >
          <div>
            <div className="w-9 h-9 rounded-xl bg-purple-100 text-purple-800 flex items-center justify-center mb-3">
              <Server className="w-5 h-5" />
            </div>
            <div className="text-sm font-black text-slate-900">
              {t('wizard_opt_lan_title')}
            </div>
            <p className="text-xs text-slate-500 font-medium mt-1 leading-relaxed">
              {t('wizard_opt_lan_desc')}
            </p>
          </div>
          <span className="mt-4 text-[10px] font-bold uppercase tracking-wider text-purple-700 bg-purple-50 px-2 py-0.5 rounded-md inline-block w-fit">
            {t('badge_mesh_lan')}
          </span>
        </button>
      </div>
    </div>
  );
};
