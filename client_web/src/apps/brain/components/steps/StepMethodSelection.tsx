import React from 'react';
import { BrainTargetConfig, ComputeMethod } from '../../types';
import { Key, HardDrive, Server, ArrowRight, Sparkles, Check } from 'lucide-react';

interface StepMethodSelectionProps {
  readonly target: BrainTargetConfig;
  readonly selectedMethod: ComputeMethod;
  readonly onSelectMethod: (method: ComputeMethod) => void;
  readonly t: (key: string) => string;
}

export const StepMethodSelection: React.FC<StepMethodSelectionProps> = ({
  target,
  selectedMethod,
  onSelectMethod,
  t,
}) => {
  const methods = [
    {
      id: 'api_key' as ComputeMethod,
      title: t('method_api_title'),
      subtitle: t('method_api_subtitle'),
      badge: 'Cloud Frontier AI',
      badgeClass: 'bg-amber-100 text-amber-950 border border-amber-300 font-bold shadow-2xs',
      iconContainer: 'bg-amber-100 text-amber-900 border border-amber-200 shadow-2xs',
      icon: <Key className="w-7 h-7" />,
      features: [
        t('method_api_f1'),
        t('method_api_f2'),
        t('method_api_f3'),
      ],
      description: t('method_api_desc'),
      containerClass:
        'bg-gradient-to-b from-amber-50/80 via-white to-amber-50/20 border-2 border-amber-200 hover:border-amber-400 shadow-xs hover:shadow-lg',
      activeClass: 'border-amber-500 ring-4 ring-amber-200 shadow-md',
      btnClass: 'bg-amber-500 hover:bg-amber-600 text-white font-black',
    },
    {
      id: 'ollama_local' as ComputeMethod,
      title: t('method_local_title'),
      subtitle: t('method_local_subtitle'),
      badge: 'Privacy 100% Offline',
      badgeClass: 'bg-emerald-100 text-emerald-950 border border-emerald-300 font-bold shadow-2xs',
      iconContainer: 'bg-emerald-100 text-emerald-900 border border-emerald-200 shadow-2xs',
      icon: <HardDrive className="w-7 h-7" />,
      features: [
        t('method_local_f1'),
        t('method_local_f2'),
        t('method_local_f3'),
      ],
      description: t('method_local_desc'),
      containerClass:
        'bg-gradient-to-b from-emerald-50/80 via-white to-emerald-50/20 border-2 border-emerald-200 hover:border-emerald-400 shadow-xs hover:shadow-lg',
      activeClass: 'border-emerald-500 ring-4 ring-emerald-200 shadow-md',
      btnClass: 'bg-emerald-600 hover:bg-emerald-700 text-white font-black',
    },
    {
      id: 'ollama_remote' as ComputeMethod,
      title: t('method_remote_title'),
      subtitle: t('method_remote_subtitle'),
      badge: 'Workstation LAN Condivisa',
      badgeClass: 'bg-purple-100 text-purple-950 border border-purple-300 font-bold shadow-2xs',
      iconContainer: 'bg-purple-100 text-purple-900 border border-purple-200 shadow-2xs',
      icon: <Server className="w-7 h-7" />,
      features: [
        t('method_remote_f1'),
        t('method_remote_f2'),
        t('method_remote_f3'),
      ],
      description: t('method_remote_desc'),
      containerClass:
        'bg-gradient-to-b from-purple-50/80 via-white to-purple-50/20 border-2 border-purple-200 hover:border-purple-400 shadow-xs hover:shadow-lg',
      activeClass: 'border-purple-500 ring-4 ring-purple-200 shadow-md',
      btnClass: 'bg-purple-600 hover:bg-purple-700 text-white font-black',
    },
  ];

  return (
    <div className="w-full space-y-7">
      {/* Step Header with High Contrast Light Typography */}
      <div className="text-center max-w-3xl mx-auto space-y-2.5">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-indigo-100 border border-indigo-200 text-indigo-900 text-xs font-black tracking-wider uppercase shadow-2xs">
          <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
          <span>{t('step_1_badge')}</span>
        </div>

        <h2 className="text-xl sm:text-2xl lg:text-3xl font-black text-slate-950 tracking-tight leading-tight">
          {t('which_method_title')} <span className="text-indigo-600 underline decoration-indigo-300 underline-offset-4">{target.name}</span>?
        </h2>

        <p className="text-xs sm:text-sm font-medium text-slate-600 leading-relaxed max-w-2xl mx-auto">
          {t('which_method_desc')}
        </p>
      </div>

      {/* 3 Large Responsive MD3 Expressive Cards spanning the full display */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 w-full pt-1">
        {methods.map((m) => {
          const isSelected = selectedMethod === m.id;
          return (
            <div
              key={m.id}
              onClick={() => onSelectMethod(m.id)}
              role="button"
              tabIndex={0}
              aria-label={m.title}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelectMethod(m.id);
                }
              }}
              className={`relative flex flex-col justify-between rounded-3xl border p-6 sm:p-7 transition-all duration-300 cursor-pointer ${
                m.containerClass
              } ${isSelected ? m.activeClass : ''}`}
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className={`p-3.5 rounded-2xl shrink-0 transition-transform group-hover:scale-105 ${m.iconContainer}`}>
                    {m.icon}
                  </div>
                  <span className={`text-[11px] px-3 py-1 rounded-full ${m.badgeClass}`}>
                    {m.badge}
                  </span>
                </div>

                <div className="mt-5 space-y-1">
                  <h3 className="text-lg sm:text-xl font-black text-slate-950 tracking-tight">
                    {m.title}
                  </h3>
                  <p className="text-xs font-semibold text-slate-600">
                    {m.subtitle}
                  </p>
                </div>

                <p className="mt-3.5 text-xs sm:text-sm text-slate-700 leading-relaxed border-t border-slate-200/90 pt-3">
                  {m.description}
                </p>

                <div className="mt-4 space-y-2">
                  {m.features.map((feat, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-xs sm:text-sm text-slate-800">
                      <div className="p-0.5 rounded-full bg-slate-900 text-white mt-0.5 shrink-0">
                        <Check className="w-3 h-3 stroke-[3]" />
                      </div>
                      <span className="font-semibold leading-snug">{feat}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-200/90 flex items-center justify-between">
                <span className="text-xs font-bold text-slate-600">
                  {isSelected ? (
                    <span className="text-slate-950 font-black flex items-center gap-1.5">
                      <Check className="w-4 h-4 text-emerald-600 stroke-[3]" />
                      {t('selected_ready_step')}
                    </span>
                  ) : (
                    t('click_to_configure')
                  )}
                </span>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectMethod(m.id);
                  }}
                  className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs transition shadow-2xs hover:scale-102 active:scale-98 ${m.btnClass}`}
                >
                  <span>{t('select_btn')}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
