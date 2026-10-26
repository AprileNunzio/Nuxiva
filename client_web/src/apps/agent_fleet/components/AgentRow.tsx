import React from 'react';
import { Bot, Sparkles, Wrench, LayoutGrid } from 'lucide-react';
import { Pill, Tone } from '../../shared/kit';
import { useFleetI18n } from '../scope';
import { AgentState, FleetAgent } from '../types';

const STATE_TONE: Readonly<Record<AgentState, Tone>> = { active: 'emerald', paused: 'amber', archived: 'slate' };

interface Props {
  readonly agent: FleetAgent;
  readonly selected: boolean;
  readonly onSelect: (id: string) => void;
}

export const AgentRow: React.FC<Props> = ({ agent, selected, onSelect }) => {
  const { t } = useFleetI18n();
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(agent.id)}
        aria-pressed={selected}
        className={`flex w-full flex-col gap-2 rounded-xl border px-3 py-2.5 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 sm:flex-row sm:items-center ${
          selected ? 'border-cyan-500/70 bg-cyan-500/10' : 'border-slate-800/70 bg-slate-950/50 hover:border-slate-600'
        }`}
      >
        <Bot className="hidden h-5 w-5 shrink-0 text-cyan-300 sm:block" aria-hidden="true" />
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            <b className="truncate text-sm text-slate-100">{agent.name}</b>
            <span className="font-mono text-[11px] text-slate-500">{agent.id}</span>
            {agent.origin === 'nuxiva' ? (
              <span className="inline-flex items-center gap-1 text-[11px] text-purple-300">
                <Sparkles className="h-3 w-3" aria-hidden="true" />
                {t('origin_nuxiva')}
              </span>
            ) : null}
          </span>
          {agent.description ? <span className="mt-0.5 block truncate text-xs text-slate-400">{agent.description}</span> : null}
        </span>
        <span className="flex shrink-0 flex-wrap items-center gap-2">
          <Pill>{t(`kind_${agent.kind}`)}</Pill>
          <span className="inline-flex items-center gap-1 text-[11px] text-slate-400" title={t('tools')}>
            <Wrench className="h-3 w-3" aria-hidden="true" />
            {agent.tools.length}
          </span>
          <span className="inline-flex items-center gap-1 text-[11px] text-slate-400" title={t('widgets')}>
            <LayoutGrid className="h-3 w-3" aria-hidden="true" />
            {agent.widgets.length}
          </span>
          <Pill tone={STATE_TONE[agent.state]}>{t(`state_${agent.state}`)}</Pill>
        </span>
      </button>
    </li>
  );
};
