import React, { useState } from 'react';
import { Bot, Wrench, Puzzle, Brain, Shield, ChevronRight } from 'lucide-react';
import {
  getAgents,
  getSkills,
  getPlugins,
  getBrains,
} from '../../../ecosystem/registry';
import type { EcosystemManifest, EcosystemKind } from '../../../ecosystem/types';

interface EcosystemTabProps {
  t: (k: string) => string;
}

export function EcosystemTab({ t }: EcosystemTabProps) {
  const [selectedKind, setSelectedKind] = useState<EcosystemKind | 'all'>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const sections: Array<{
    kind: EcosystemKind;
    titleKey: string;
    icon: React.ComponentType<{ className?: string }>;
    items: EcosystemManifest[];
  }> = [
    { kind: 'agent', titleKey: 'ecosystem_agents', icon: Bot, items: getAgents() },
    { kind: 'skill', titleKey: 'ecosystem_skills', icon: Wrench, items: getSkills() },
    { kind: 'plugin', titleKey: 'ecosystem_plugins', icon: Puzzle, items: getPlugins() },
    { kind: 'brain', titleKey: 'ecosystem_brains', icon: Brain, items: getBrains() },
  ];

  const visibleSections =
    selectedKind === 'all'
      ? sections
      : sections.filter((s) => s.kind === selectedKind);

  return (
    <div className="flex-1 space-y-6">
      <div className="flex flex-wrap gap-1.5 overflow-x-auto pb-1 sm:pb-0">
        <button
          type="button"
          onClick={() => setSelectedKind('all')}
          className={`rounded-full px-3 py-1 text-xs font-semibold transition-all ${
            selectedKind === 'all'
              ? 'bg-primary text-on-primary shadow-xs'
              : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
          }`}
        >
          {t('all_categories')}
        </button>
        {sections.map((s) => (
          <button
            key={s.kind}
            type="button"
            onClick={() => setSelectedKind(s.kind)}
            className={`rounded-full px-3 py-1 text-xs font-semibold transition-all ${
              selectedKind === s.kind
                ? 'bg-primary text-on-primary shadow-xs'
                : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
            }`}
          >
            {t(s.titleKey)}
          </button>
        ))}
      </div>

      {visibleSections.map((sec) => {
        const Icon = sec.icon;
        return (
          <div
            key={sec.kind}
            className="rounded-3xl border border-outline-variant/60 bg-surface-container p-4 shadow-xs sm:p-5"
          >
            <div className="mb-4 flex items-center justify-between border-b border-outline-variant/30 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="rounded-xl bg-primary/10 p-2 text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-on-surface">{t(sec.titleKey)}</h2>
                  <span className="text-[11px] text-on-surface-variant">
                    {sec.items.length} moduli autonomi registrati
                  </span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {sec.items.map((entity) => {
                const isExpanded = expandedId === entity.id;
                return (
                  <div
                    key={entity.id}
                    className="flex flex-col justify-between rounded-2xl border border-outline-variant/50 bg-surface-container-high p-4 transition-all hover:border-primary/40"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-bold text-on-surface">{entity.name}</h3>
                          {entity.role && (
                            <span className="rounded-full bg-secondary-container px-2 py-0.5 text-[10px] font-bold text-on-secondary-container uppercase">
                              {entity.role}
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] font-semibold text-outline">v{entity.version}</span>
                      </div>

                      <p className="mt-1 text-xs text-on-surface-variant leading-relaxed">
                        {entity.author} • <span className="font-mono text-[11px]">{entity.scope}</span>
                      </p>

                      <div className="mt-3 flex flex-wrap gap-1">
                        {entity.capabilities.map((cap) => (
                          <span
                            key={cap}
                            className="inline-flex items-center gap-1 rounded-md bg-surface-container-highest px-2 py-0.5 text-[10px] font-mono text-on-surface-variant"
                          >
                            <Shield className="h-2.5 w-2.5 text-primary" />
                            {cap}
                          </span>
                        ))}
                      </div>
                    </div>

                    {entity.options && entity.options.length > 0 && (
                      <div className="mt-4 border-t border-outline-variant/20 pt-3">
                        <button
                          type="button"
                          onClick={() => setExpandedId(isExpanded ? null : entity.id)}
                          className="flex w-full items-center justify-between text-xs font-semibold text-primary"
                        >
                          <span>{entity.options.length} parametri configurabili</span>
                          <ChevronRight
                            className={`h-4 w-4 transform transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                          />
                        </button>

                        {isExpanded && (
                          <div className="mt-2 space-y-2 rounded-xl bg-surface-container p-2.5">
                            {entity.options.map((opt) => (
                              <div
                                key={opt.id}
                                className="flex items-center justify-between text-xs text-on-surface"
                              >
                                <span className="font-mono text-[11px]">{opt.id}</span>
                                <span className="font-semibold text-outline">{String(opt.default)}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
