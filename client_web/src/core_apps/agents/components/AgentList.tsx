import React, { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { Agent } from '../data/teamApi';
import { fieldClass, tone, useAgentsI18n } from '../scope';

interface AgentListProps {
  readonly agents: readonly Agent[];
  readonly selected: string | null;
  readonly toolCount: Readonly<Record<string, number>>;
  readonly onSelect: (id: string) => void;
}

const CORE_AGENTS = new Set(['ceo', 'agent', 'forge']);

export function isOperative(agent: Agent): boolean {
  return CORE_AGENTS.has(agent.id) || agent.source !== 'system' || Boolean(agent.instructions);
}

export const AgentList: React.FC<AgentListProps> = ({ agents, selected, toolCount, onSelect }) => {
  const { t } = useAgentsI18n();
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('all');
  const categories = useMemo(() => ['all', ...Array.from(new Set(agents.map((a) => a.category))).sort()], [agents]);
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return agents.filter(
      (a) =>
        (category === 'all' || a.category === category) &&
        (!q || `${a.id} ${a.name} ${a.description}`.toLowerCase().includes(q)),
    );
  }, [agents, query, category]);

  return (
    <div className="flex min-h-0 flex-col gap-3">
      <label className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t('search')}
          aria-label={t('search')}
          className={`${fieldClass} w-full pl-9`}
        />
      </label>
      <div className="flex gap-1.5 overflow-x-auto pb-1" role="tablist" aria-label={t('categories')}>
        {categories.map((c) => (
          <button
            key={c}
            type="button"
            role="tab"
            aria-selected={category === c}
            onClick={() => setCategory(c)}
            className={`shrink-0 rounded-full border px-3 py-1 text-xs transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
              category === c ? 'border-cyan-400/60 bg-cyan-400/15 text-cyan-100' : 'border-slate-700 text-slate-400 hover:text-white'
            }`}
          >
            {t(`category_${c}`)}
          </button>
        ))}
      </div>
      <ul className="flex max-h-[70vh] flex-col gap-1.5 overflow-y-auto pr-1">
        {visible.map((agent) => (
          <li key={agent.id}>
            <button
              type="button"
              onClick={() => onSelect(agent.id)}
              aria-current={selected === agent.id}
              className={`flex w-full items-center gap-3 rounded-xl border px-3 py-2 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                selected === agent.id ? 'border-cyan-400/60 bg-cyan-400/10' : 'border-slate-800/80 bg-slate-950/40 hover:border-slate-600'
              }`}
            >
              <span className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-700 bg-slate-900 text-lg">
                <span aria-hidden="true">{agent.icon || '◆'}</span>
                <span
                  className={`absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border border-slate-950 ${
                    agent.doing ? 'animate-pulse bg-cyan-300' : agent.enabled ? 'bg-emerald-400' : 'bg-slate-600'
                  }`}
                  aria-hidden="true"
                />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold text-slate-100">{agent.name}</span>
                <span className="block truncate text-[11px] text-slate-500">
                  {agent.doing ? t('doing', { what: agent.doing }) : t('tools_count', { count: toolCount[agent.id] ?? 0 })}
                </span>
              </span>
              <span className={`shrink-0 rounded-full border px-2 py-0.5 font-mono text-[10px] ${tone(agent.priority)}`}>p{agent.priority}</span>
            </button>
          </li>
        ))}
        {visible.length === 0 && <li className="px-3 py-6 text-center text-sm text-slate-500">{t('no_results')}</li>}
      </ul>
    </div>
  );
};
