import React from 'react';
import { Cpu, Mic, Music, Check } from 'lucide-react';
import { getEnginesByFamily } from '../../../engines/registry';
import type { EngineFamily, ActiveEnginesState } from '../../../engines/types';

interface EnginesTabProps {
  activeEngines: ActiveEnginesState;
  engineOptionsState: Record<string, Record<string, unknown>>;
  onSelectActiveEngine: (family: EngineFamily, engineId: string) => void;
  onEngineOptionChange: (engineId: string, optionId: string, val: unknown) => void;
  t: (k: string) => string;
}

export function EnginesTab({
  activeEngines,
  engineOptionsState,
  onSelectActiveEngine,
  onEngineOptionChange,
  t,
}: EnginesTabProps) {
  const engineFamilies: Array<{
    id: EngineFamily;
    titleKey: string;
    icon: React.ComponentType<{ className?: string }>;
  }> = [
    { id: 'reasoning', titleKey: 'family_reasoning', icon: Cpu },
    { id: 'speech_recognition', titleKey: 'family_speech_recognition', icon: Mic },
    { id: 'music_recognition', titleKey: 'family_music_recognition', icon: Music },
  ];

  return (
    <div className="flex-1 space-y-6">
      {engineFamilies.map((fam) => {
        const engines = getEnginesByFamily(fam.id);
        const activeId = activeEngines[fam.id] || engines[0]?.id;
        const Icon = fam.icon;

        return (
          <div
            key={fam.id}
            className="rounded-3xl border border-outline-variant/60 bg-surface-container p-4 shadow-xs sm:p-5"
          >
            <div className="mb-4 flex items-center justify-between border-b border-outline-variant/30 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="rounded-xl bg-primary/10 p-2 text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-on-surface">{t(fam.titleKey)}</h2>
                  <span className="text-[11px] text-on-surface-variant">
                    {engines.length} {engines.length === 1 ? 'motore installato' : 'motori installati'}
                  </span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
              {engines.map((engine) => {
                const isActive = engine.id === activeId;
                return (
                  <div
                    key={engine.id}
                    onClick={() => onSelectActiveEngine(fam.id, engine.id)}
                    className={`flex cursor-pointer flex-col justify-between rounded-2xl border p-4 transition-all ${
                      isActive
                        ? 'border-primary bg-primary/5 shadow-xs'
                        : 'border-outline-variant/50 bg-surface-container-high hover:border-primary/40'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <h3 className="text-sm font-bold text-on-surface">{engine.name}</h3>
                        {isActive ? (
                          <span className="flex items-center gap-1 rounded-full bg-primary px-2 py-0.5 text-[10px] font-bold text-on-primary">
                            <Check className="h-3 w-3 stroke-[2.5]" />
                            {t('active_engine_badge')}
                          </span>
                        ) : (
                          <span className="text-[10px] font-semibold text-outline">v{engine.version}</span>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-on-surface-variant leading-relaxed">
                        {engine.author || 'Nuxiva'}
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectActiveEngine(fam.id, engine.id);
                      }}
                      className={`mt-3 w-full rounded-xl py-1.5 text-xs font-bold transition-all ${
                        isActive
                          ? 'bg-primary text-on-primary'
                          : 'bg-surface-container-highest text-on-surface hover:bg-primary/20'
                      }`}
                    >
                      {isActive ? t('active_engine_badge') : t('select_engine_cta')}
                    </button>
                  </div>
                );
              })}
            </div>

            {activeId && (
              <div className="mt-4 rounded-2xl bg-surface-container-highest/60 p-4">
                <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-outline">
                  {t('engine_options_header')} ({activeId})
                </h4>
                {(() => {
                  const currentEngine = engines.find((e) => e.id === activeId);
                  const opts = currentEngine?.options || [];
                  if (opts.length === 0) {
                    return <p className="text-xs text-outline">{t('no_engine_options')}</p>;
                  }

                  return (
                    <div className="space-y-3">
                      {opts.map((opt) => {
                        const currentVal =
                          engineOptionsState[activeId]?.[opt.id] !== undefined
                            ? engineOptionsState[activeId]?.[opt.id]
                            : opt.default;

                        if (opt.type === 'boolean') {
                          const checked = Boolean(currentVal);
                          return (
                            <div
                              key={opt.id}
                              onClick={() => onEngineOptionChange(activeId, opt.id, !checked)}
                              className="flex cursor-pointer items-center justify-between rounded-xl bg-surface-container p-2.5"
                            >
                              <div>
                                <div className="text-xs font-bold text-on-surface">{opt.id}</div>
                              </div>
                              <div
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                                  checked ? 'bg-primary' : 'bg-surface-container-highest border border-outline-variant'
                                }`}
                              >
                                <span
                                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                                    checked ? 'translate-x-6' : 'translate-x-1'
                                  }`}
                                />
                              </div>
                            </div>
                          );
                        }

                        if (opt.type === 'range') {
                          const numVal = Number(currentVal);
                          return (
                            <div key={opt.id} className="rounded-xl bg-surface-container p-2.5">
                              <div className="flex items-center justify-between text-xs font-bold text-on-surface">
                                <span>{opt.id}</span>
                                <span className="text-primary font-mono">{numVal}</span>
                              </div>
                              <input
                                type="range"
                                min={opt.min || 0}
                                max={opt.max || 100}
                                value={numVal}
                                onChange={(e) => onEngineOptionChange(activeId, opt.id, Number(e.target.value))}
                                className="mt-2 w-full accent-primary"
                              />
                            </div>
                          );
                        }

                        return null;
                      })}
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
