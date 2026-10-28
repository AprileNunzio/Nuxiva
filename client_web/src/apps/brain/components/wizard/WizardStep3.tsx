import React from 'react';
import { CheckCircle2 } from 'lucide-react';

interface WizardStep3Props {
  readonly completed: boolean;
  readonly selectedProviderType: string;
  readonly selectedModel: string;
  readonly t: (key: string) => string;
}

export const WizardStep3: React.FC<WizardStep3Props> = ({
  completed,
  selectedProviderType,
  selectedModel,
  t,
}) => {
  return (
    <div className="space-y-4">
      {completed ? (
        <div className="py-8 text-center space-y-3">
          <div className="w-14 h-14 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-inner">
            <CheckCircle2 className="w-8 h-8 stroke-[2.5]" />
          </div>
          <h4 className="text-lg font-black text-slate-900">
            {t('wizard_completed_title')}
          </h4>
          <p className="text-xs sm:text-sm text-slate-600 max-w-md mx-auto">
            {t('wizard_completed_desc')}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <h4 className="text-sm font-black text-slate-900">
            {t('wizard_confirm_title')}
          </h4>
          <p className="text-xs text-slate-600 leading-relaxed">
            {t('wizard_confirm_desc')}
          </p>
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500 font-bold">{t('wizard_summary_origin')}:</span>
              <span className="font-black text-slate-800">{selectedProviderType}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 font-bold">{t('wizard_summary_model')}:</span>
              <span className="font-black text-indigo-700">{selectedModel}</span>
            </div>
            <div className="flex justify-between border-t border-slate-200/60 pt-2">
              <span className="text-slate-500 font-bold">{t('wizard_summary_targets')}:</span>
              <span className="font-bold text-emerald-700">{t('wizard_all_targets_auto')}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
