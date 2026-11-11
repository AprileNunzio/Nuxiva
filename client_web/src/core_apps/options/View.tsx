import React, { useState, useMemo } from 'react';
import { Search, Sliders, CheckCircle2, XCircle, Cpu, Mic, Music, Check } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { OptionCategory } from './types';
import { loadStoredOptions, saveStoredOption } from './optionsState';
import { engineRegistry, getEnginesByFamily } from '../../engines/registry';
import { loadActiveEngines, saveActiveEngine, loadEngineOption, saveEngineOption } from '../../engines/engineState';
import type { EngineFamily, EngineManifest } from '../../engines/types';

export function View() {
  const { t, lang } = useScopedI18n('core_apps/options');
  const [activeMainTab, setActiveMainTab] = useState<'switches' | 'engines'>('switches');

  const [options, setOptions] = useState(loadStoredOptions);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<OptionCategory | 'all'>('all');

  const [activeEngines, setActiveEngines] = useState(loadActiveEngines);
  const [engineOptionsState, setEngineOptionsState] = useState<Record<string, Record<string, unknown>>>(() => {
    const initial: Record<string, Record<string, unknown>> = {};
    for (const engine of engineRegistry) {
      initial[engine.id] = {};
      for (const opt of engine.options || []) {
        const stored = loadEngineOption(engine.id, opt.id, opt.default);
        const map = initial[engine.id];
        if (map) {
          map[opt.id] = stored;
        }
      }
    }
    return initial;
  });

  const categories: Array<{ id: OptionCategory | 'all'; label: string }> = [
    { id: 'all', label: t('all_categories') },
    { id: 'multimedia', label: t('cat_multimedia') },
    { id: 'security', label: t('cat_security') },
    { id: 'ai_voice', label: t('cat_ai_voice') },
    { id: 'display', label: t('cat_display') },
    { id: 'privacy', label: t('cat_privacy') },
  ];

  const engineFamilies: Array<{ id: EngineFamily; titleKey: string; icon: React.ComponentType<{ className?: string }> }> = [
    { id: 'reasoning', titleKey: 'family_reasoning', icon: Cpu },
    { id: 'speech_recognition', titleKey: 'family_speech_recognition', icon: Mic },
    { id: 'music_recognition', titleKey: 'family_music_recognition', icon: Music },
  ];

  const handleToggle = (id: string) => {
    setOptions((current) =>
      current.map((opt) => {
        if (opt.id === id) {
          const nextVal = !opt.enabled;
          saveStoredOption(id, nextVal);
          return { ...opt, enabled: nextVal };
        }
        return opt;
      })
    );
  };

  const handleSelectActiveEngine = (family: EngineFamily, engineId: string) => {
    saveActiveEngine(family, engineId);
    setActiveEngines((prev) => ({
      ...prev,
      [family]: engineId,
    }));
  };

  const handleEngineOptionChange = (engineId: string, optionId: string, val: unknown) => {
    saveEngineOption(engineId, optionId, val);
    setEngineOptionsState((prev) => ({
      ...prev,
      [engineId]: {
        ...(prev[engineId] || {}),
        [optionId]: val,
      },
    }));
  };

  const filteredOptions = useMemo(() => {
    const q = search.trim().toLowerCase();
    return options.filter((opt) => {
      const matchCategory = selectedCategory === 'all' || opt.category === selectedCategory;
      if (!matchCategory) return false;
      if (!q) return true;

      const title = t(opt.titleKey).toLowerCase();
      const desc = t(opt.descriptionKey).toLowerCase();
      const matchTags = opt.tags.some((tag) => tag.toLowerCase().includes(q));

      return title.includes(q) || desc.includes(q) || matchTags;
    });
  }, [options, search, selectedCategory, t]);

  const activeCount = useMemo(() => options.filter((o) => o.enabled).length, [options]);

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-surface p-4 text-on-surface sm:p-6">
      <div className="mb-4 flex flex-col gap-2 border-b border-outline-variant/40 pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sliders className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-bold tracking-tight text-on-surface">{t('title')}</h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveMainTab('switches')}
              className={`rounded-xl px-3 py-1.5 text-xs font-bold transition-all ${
                activeMainTab === 'switches'
                  ? 'bg-primary text-on-primary shadow-xs'
                  : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
              }`}
            >
              {t('tab_switches')}
            </button>
            <button
              type="button"
              onClick={() => setActiveMainTab('engines')}
              className={`rounded-xl px-3 py-1.5 text-xs font-bold transition-all ${
                activeMainTab === 'engines'
                  ? 'bg-primary text-on-primary shadow-xs'
                  : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
              }`}
            >
              {t('tab_engines')}
            </button>
          </div>
        </div>
        <p className="text-xs text-on-surface-variant">{t('subtitle')}</p>
      </div>

      {activeMainTab === 'switches' ? (
        <>
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-on-surface-variant" />
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={t('search_placeholder')}
                className="w-full rounded-xl border border-outline-variant/60 bg-surface-container py-2 pl-9 pr-4 text-xs text-on-surface placeholder:text-outline focus:border-primary focus:outline-hidden"
              />
            </div>

            <div className="flex flex-wrap gap-1.5 overflow-x-auto pb-1 sm:pb-0">
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => setSelectedCategory(cat.id)}
                  className={`rounded-full px-3 py-1 text-xs font-semibold transition-all ${
                    selectedCategory === cat.id
                      ? 'bg-primary text-on-primary shadow-xs'
                      : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 space-y-2.5">
            {filteredOptions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center text-outline">
                <Sliders className="h-10 w-10 stroke-[1.5]" />
                <p className="mt-2 text-xs">{t('no_options_found')}</p>
              </div>
            ) : (
              filteredOptions.map((opt) => (
                <div
                  key={opt.id}
                  onClick={() => handleToggle(opt.id)}
                  className="flex cursor-pointer items-center justify-between gap-4 rounded-2xl border border-outline-variant/50 bg-surface-container p-3.5 shadow-2xs transition-all hover:border-primary/40 hover:bg-surface-container-high sm:p-4"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-on-surface">{t(opt.titleKey)}</h3>
                      {opt.enabled ? (
                        <span className="flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary">
                          <CheckCircle2 className="h-3 w-3" />
                          {t('active')}
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 rounded-full bg-surface-container-highest px-2 py-0.5 text-[10px] font-medium text-outline">
                          <XCircle className="h-3 w-3" />
                          {t('disabled')}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-on-surface-variant leading-relaxed">
                      {t(opt.descriptionKey)}
                    </p>
                  </div>

                  <div className="shrink-0">
                    <div
                      role="switch"
                      aria-checked={opt.enabled}
                      tabIndex={0}
                      className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors duration-200 ease-in-out focus:outline-hidden ${
                        opt.enabled ? 'bg-primary' : 'bg-surface-container-highest border border-outline-variant'
                      }`}
                    >
                      <span
                        className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-md transition duration-200 ease-in-out ${
                          opt.enabled ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      ) : (
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
                        onClick={() => handleSelectActiveEngine(fam.id, engine.id)}
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
                            handleSelectActiveEngine(fam.id, engine.id);
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
                                  onClick={() => handleEngineOptionChange(activeId, opt.id, !checked)}
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
                                    onChange={(e) => handleEngineOptionChange(activeId, opt.id, Number(e.target.value))}
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
      )}
    </div>
  );
}

export default View;
