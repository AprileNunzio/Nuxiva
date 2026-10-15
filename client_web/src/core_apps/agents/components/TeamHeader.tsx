import React from 'react';
import { Bot, Hammer, LayoutGrid, Plus, Sparkles, Wrench } from 'lucide-react';
import { TeamOverview } from '../data/teamApi';
import { chipClass, panelClass, useAgentsI18n } from '../scope';
import { isOperative } from './AgentList';

export type CreateKind = 'agent' | 'tool' | 'widget';

interface TeamHeaderProps {
  readonly team: TeamOverview;
  readonly busy: boolean;
  readonly onCreate: (kind: CreateKind) => void;
  readonly onAutonomy: (enabled: boolean) => void;
}

export const TeamHeader: React.FC<TeamHeaderProps> = ({ team, busy, onCreate, onAutonomy }) => {
  const { t } = useAgentsI18n();
  const forge = team.agents.find((a) => a.id === 'forge');
  const toolCount: Record<string, number> = {};
  team.tools.forEach((tool) => {
    toolCount[tool.owner] = (toolCount[tool.owner] ?? 0) + 1;
  });
  const operative = team.agents.filter((a) => isOperative(a, toolCount));
  const active = operative.filter((a) => a.enabled).length;
  const working = team.agents.filter((a) => a.doing).length;
  const stats = [
    [Bot, t('stat_agents'), `${active}/${operative.length}`],
    [Sparkles, t('stat_working'), String(working)],
    [Wrench, t('stat_tools'), String(team.tools.filter((x) => x.enabled).length)],
    [LayoutGrid, t('stat_widgets'), String(team.widgets.length)],
  ] as const;

  return (
    <section className={`${panelClass} relative overflow-hidden`} aria-labelledby="team-title">
      <div className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full bg-indigo-500/10 blur-3xl" aria-hidden="true" />
      <div className="relative flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 id="team-title" className="font-['Rajdhani'] text-3xl font-bold tracking-wide text-white">
            {t('title')}
          </h1>
          <p className="mt-1 text-sm text-slate-400">{t('description')}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => onCreate('agent')} className={`${chipClass} border-cyan-400/50 bg-cyan-400/10 py-2 text-cyan-100 hover:bg-cyan-400/20`}>
            <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            {t('new_agent')}
          </button>
          <button type="button" onClick={() => onCreate('tool')} className={`${chipClass} border-slate-700 py-2 text-slate-200 hover:border-cyan-400/50`}>
            <Hammer className="h-3.5 w-3.5" aria-hidden="true" />
            {t('new_tool')}
          </button>
          <button type="button" onClick={() => onCreate('widget')} className={`${chipClass} border-slate-700 py-2 text-slate-200 hover:border-cyan-400/50`}>
            <LayoutGrid className="h-3.5 w-3.5" aria-hidden="true" />
            {t('new_widget')}
          </button>
        </div>
      </div>
      <div className="relative mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {stats.map(([Icon, label, value]) => (
          <div key={label} className="rounded-xl border border-slate-800/80 bg-slate-950/50 px-3 py-2">
            <p className="flex items-center gap-1.5 text-[10px] uppercase tracking-[0.14em] text-slate-500">
              <Icon className="h-3.5 w-3.5 text-cyan-300" aria-hidden="true" />
              {label}
            </p>
            <p className="mt-1 font-mono text-xl text-white">{value}</p>
          </div>
        ))}
      </div>
      {forge && forge.toggle && (
        <label className="relative mt-3 flex cursor-pointer items-start justify-between gap-3 rounded-xl border border-indigo-400/30 bg-indigo-400/5 px-3 py-2.5">
          <span>
            <span className="block text-sm font-semibold text-indigo-100">{t('autonomy')}</span>
            <span className="block text-[11px] text-slate-400">{t('autonomy_hint')}</span>
          </span>
          <input
            type="checkbox"
            role="switch"
            disabled={busy}
            checked={forge.enabled}
            onChange={(event) => onAutonomy(event.target.checked)}
            className="mt-1 h-5 w-9 shrink-0 accent-indigo-400"
          />
        </label>
      )}
    </section>
  );
};
