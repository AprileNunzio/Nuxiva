import React, { useState } from 'react';
import { Sliders } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { OptionCategory } from './types';
import { loadStoredOptions, saveStoredOption } from './optionsState';
import { engineRegistry } from '../../engines/registry';
import {
  loadActiveEngines,
  saveActiveEngine,
  loadEngineOption,
  saveEngineOption,
} from '../../engines/engineState';
import type { EngineFamily } from '../../engines/types';
import { SwitchesTab } from './components/SwitchesTab';
import { EnginesTab } from './components/EnginesTab';
import { EcosystemTab } from './components/EcosystemTab';

export function View() {
  const { t } = useScopedI18n('core_apps/options');
  const [activeMainTab, setActiveMainTab] = useState<'switches' | 'engines' | 'ecosystem'>('switches');

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
            <button
              type="button"
              onClick={() => setActiveMainTab('ecosystem')}
              className={`rounded-xl px-3 py-1.5 text-xs font-bold transition-all ${
                activeMainTab === 'ecosystem'
                  ? 'bg-primary text-on-primary shadow-xs'
                  : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
              }`}
            >
              {t('tab_ecosystem')}
            </button>
          </div>
        </div>
        <p className="text-xs text-on-surface-variant">{t('subtitle')}</p>
      </div>

      {activeMainTab === 'switches' ? (
        <SwitchesTab
          options={options}
          search={search}
          setSearch={setSearch}
          selectedCategory={selectedCategory}
          setSelectedCategory={setSelectedCategory}
          categories={categories}
          onToggle={handleToggle}
          t={t}
        />
      ) : activeMainTab === 'engines' ? (
        <EnginesTab
          activeEngines={activeEngines}
          engineOptionsState={engineOptionsState}
          onSelectActiveEngine={handleSelectActiveEngine}
          onEngineOptionChange={handleEngineOptionChange}
          t={t}
        />
      ) : (
        <EcosystemTab t={t} />
      )}
    </div>
  );
}

export default View;
