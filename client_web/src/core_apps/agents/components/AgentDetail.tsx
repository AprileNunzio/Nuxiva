import React, { useState } from 'react';
import { Agent, TeamOverview } from '../data/teamApi';
import { TeamHandle } from '../hooks/useTeam';
import { panelClass, tone, useAgentsI18n } from '../scope';
import { OverviewTab } from './OverviewTab';
import { SettingsTab } from './SettingsTab';
import { ToolsTab } from './ToolsTab';
import { WidgetsTab } from './WidgetsTab';

const TABS = ['overview', 'settings', 'tools', 'widgets'] as const;
type Tab = (typeof TABS)[number];

interface AgentDetailProps {
  readonly agent: Agent;
  readonly team: TeamOverview;
  readonly handle: TeamHandle;
  readonly onDeleted: () => void;
}

export const AgentDetail: React.FC<AgentDetailProps> = ({ agent, team, handle, onDeleted }) => {
  const { t } = useAgentsI18n();
  const [tab, setTab] = useState<Tab>('overview');
  const counts: Record<Tab, number | null> = {
    overview: null,
    settings: agent.settings.length,
    tools: team.tools.filter((x) => x.owner === agent.id).length,
    widgets: team.widgets.filter((w) => w.agent === agent.id).length,
  };

  return (
    <section className={panelClass} aria-labelledby="agent-title">
      <header className="flex items-start gap-3">
        <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border border-cyan-400/40 bg-cyan-400/10 text-2xl shadow-[0_0_24px_rgba(34,211,238,0.2)]" aria-hidden="true">
          {agent.icon || '◆'}
        </span>
        <div className="min-w-0 flex-1">
          <h2 id="agent-title" className="font-['Rajdhani'] text-2xl font-bold text-white">
            {agent.name}
          </h2>
          <p className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <span className="font-mono">{agent.id}</span>
            <span className={`rounded-full border px-2 py-0.5 font-mono text-[10px] ${tone(agent.priority)}`}>p{agent.priority}</span>
            <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[10px]">{t(`category_${agent.category}`)}</span>
            {agent.source !== 'system' && <span className="rounded-full border border-indigo-400/40 px-2 py-0.5 text-[10px] text-indigo-200">{t(`source_${agent.source}`)}</span>}
          </p>
        </div>
      </header>
      <div role="tablist" aria-label={agent.name} className="mt-4 flex gap-1 overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/60 p-1">
        {TABS.map((id) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
              tab === id ? 'bg-cyan-400/15 text-cyan-100' : 'text-slate-400 hover:text-white'
            }`}
          >
            {t(`tab_${id}`)}
            {counts[id] !== null && <span className="ml-1.5 font-mono text-[10px] text-slate-500">{counts[id]}</span>}
          </button>
        ))}
      </div>
      <div className="mt-4" role="tabpanel">
        {tab === 'overview' && <OverviewTab agent={agent} handle={handle} onDeleted={onDeleted} />}
        {tab === 'settings' && <SettingsTab agent={agent} handle={handle} />}
        {tab === 'tools' && <ToolsTab agent={agent} agents={team.agents} tools={team.tools} handle={handle} />}
        {tab === 'widgets' && <WidgetsTab agent={agent} agents={team.agents} widgets={team.widgets} people={team.people} handle={handle} />}
      </div>
    </section>
  );
};
