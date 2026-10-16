import React, { useState, useId } from 'react';
import { Cpu, Layers, Scale, ShieldCheck, ChevronDown, Check } from 'lucide-react';
import { useI18n } from '../../shared/i18n/I18nContext';
import { useCognitiveEngine } from './useCognitiveEngine';
import { CognitiveEngineId, EngineStrategy } from './types';

export const CognitiveEngineSelector: React.FC = () => {
  const { t } = useI18n();
  const selectId = useId();
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const { configuredVersion, engines, isLoading, switchEngine } = useCognitiveEngine();
  const describe = (st: EngineStrategy) => `${t(st.kind === 'chat' ? 'engine_kind_chat' : 'engine_kind_deep')} · ${t(`engine_pick_${st.pick}` as any).replace('{n}', String(st.candidates)).replace('{wait}', String(st.wait_s))}`;

  const handleSelect = (version: CognitiveEngineId) => {
    switchEngine(version);
    setIsOpen(false);
  };

  const getBadgeKey = (id: CognitiveEngineId | null): any => {
    switch (id) {
      case 'nuxiva-4.2-legacy':
        return 'engine_legacy_badge';
      case 'nuxiva-5.0-veloce':
        return 'engine_veloce_badge';
      case 'nuxiva-5.0-empatico':
        return 'engine_empatico_badge';
      case 'nuxiva-6.0-pro':
        return 'engine_pro_badge';
      case 'nuxiva-6.5-ultra':
        return 'engine_ultra_badge';
      case 'nuxiva-6.5-auto':
      default:
        return 'engine_auto_badge';
    }
  };

  const activeProfile = engines.find((e) => e.id === configuredVersion);

  return (
    <div className="relative w-full sm:w-auto flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-4 p-2 sm:p-2.5 rounded-xl bg-slate-900/90 border border-cyan-500/30 backdrop-blur-md shadow-lg shadow-cyan-950/20">
      <div className="flex items-center justify-between sm:justify-start gap-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400">
            <Cpu className="w-4 h-4 sm:w-5 sm:h-5" aria-hidden="true" />
          </div>
          <div>
            <div className="text-[10px] sm:text-xs font-mono uppercase tracking-wider text-cyan-400 font-semibold">
              {t('engine_selector_badge')}
            </div>
            <div className="text-xs sm:text-sm font-bold text-slate-100 font-['Rajdhani']">
              {activeProfile ? activeProfile.name : t('engine_selector_title')}
            </div>
          </div>
        </div>

        <button
          type="button"
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          id={selectId}
          onClick={() => setIsOpen(!isOpen)}
          disabled={isLoading}
          className="sm:hidden flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs font-mono text-cyan-300"
        >
          <span>{t(getBadgeKey(configuredVersion))}</span>
          <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      </div>

      <div className="flex items-center gap-3 sm:gap-4 pt-1 sm:pt-0 border-t sm:border-t-0 sm:border-l border-slate-800 sm:pl-4 text-xs font-mono">
        {activeProfile && (
          <>
            <div className="flex items-center gap-1.5 text-emerald-400">
              <Layers className="w-3.5 h-3.5" aria-hidden="true" />
              <span>{describe(activeProfile.strategy)}</span>
            </div>
            {activeProfile.strategy.critic && (
              <div className="hidden md:flex items-center gap-1.5 text-indigo-300">
                <Scale className="w-3.5 h-3.5" aria-hidden="true" />
                <span>{t('engine_critic')}</span>
              </div>
            )}
          </>
        )}
      </div>

      <div className="hidden sm:block">
        <button
          type="button"
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          onClick={() => setIsOpen(!isOpen)}
          disabled={isLoading}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 border border-cyan-500/40 text-xs font-mono font-medium text-cyan-300 transition-all hover:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400"
        >
          <span>{t(getBadgeKey(configuredVersion))}</span>
          <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 sm:right-auto sm:left-auto sm:min-w-[320px] mt-2 p-1.5 rounded-xl bg-slate-900 border border-cyan-500/40 shadow-2xl backdrop-blur-xl z-50 animate-in fade-in zoom-in-95 duration-150">
          <div className="text-[10px] font-mono uppercase px-3 py-1.5 text-slate-400 border-b border-slate-800 flex items-center justify-between">
            <span>{t('engine_selector_title')}</span>
            <ShieldCheck className="w-3 h-3 text-cyan-400" />
          </div>
          <div className="mt-1 space-y-1 max-h-[280px] overflow-y-auto">
            {engines.map((engine) => {
              const isSelected = engine.id === configuredVersion;
              return (
                <button
                  key={engine.id}
                  type="button"
                  onClick={() => handleSelect(engine.id)}
                  className={`w-full flex items-center justify-between p-2.5 rounded-lg text-left transition-colors font-mono ${
                    isSelected
                      ? 'bg-cyan-500/15 border border-cyan-500/40 text-cyan-200'
                      : 'hover:bg-slate-800 text-slate-300'
                  }`}
                >
                  <div className="flex-1 min-w-0 pr-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-100 truncate">
                        {engine.name}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 border border-slate-700 text-cyan-400 font-semibold">
                        {t(getBadgeKey(engine.id))}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 truncate mt-0.5">
                      {engine.architecture}
                    </div>
                    <div className="text-[10px] text-slate-500 mt-1">{describe(engine.strategy)}</div>
                  </div>
                  {isSelected && <Check className="w-4 h-4 text-cyan-400 flex-shrink-0" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
