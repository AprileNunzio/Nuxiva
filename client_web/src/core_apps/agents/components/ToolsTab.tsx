import React, { useMemo, useState } from 'react';
import { ShieldCheck, Trash2 } from 'lucide-react';
import { Agent, ToolInfo, deleteTool, updateTool } from '../data/teamApi';
import { TeamHandle } from '../hooks/useTeam';
import { chipClass, fieldClass, useAgentsI18n } from '../scope';

interface ToolsTabProps {
  readonly agent: Agent;
  readonly agents: readonly Agent[];
  readonly tools: readonly ToolInfo[];
  readonly handle: TeamHandle;
}

export const ToolsTab: React.FC<ToolsTabProps> = ({ agent, agents, tools, handle }) => {
  const { t } = useAgentsI18n();
  const [adding, setAdding] = useState('');
  const mine = useMemo(() => tools.filter((tool) => tool.owner === agent.id), [tools, agent.id]);
  const others = useMemo(() => tools.filter((tool) => tool.owner !== agent.id && !tool.name.startsWith('team_') && !tool.name.startsWith('agent_')), [tools, agent.id]);
  const busy = handle.busy !== null;
  const coordination = (name: string) => name.startsWith('team_') || name.startsWith('agent_');

  return (
    <div className="flex flex-col gap-3">
      {mine.length === 0 && <p className="text-sm text-slate-500">{t('tools_empty')}</p>}
      <ul className="flex flex-col gap-2">
        {mine.map((tool) => (
          <li key={tool.name} className={`rounded-xl border px-3 py-2.5 ${tool.enabled ? 'border-slate-800/80 bg-slate-950/40' : 'border-slate-800/60 bg-slate-950/20 opacity-70'}`}>
            <div className="flex flex-wrap items-start gap-2">
              <div className="min-w-0 flex-1">
                <p className="font-mono text-sm text-cyan-100">
                  {tool.name}
                  {tool.custom && <span className="ml-2 rounded border border-indigo-400/40 px-1 text-[10px] text-indigo-200">{t('custom')}</span>}
                </p>
                <p className="text-xs text-slate-400">{tool.description}</p>
                {Object.keys(tool.args).length > 0 && (
                  <p className="mt-1 font-mono text-[10px] text-slate-500">({Object.keys(tool.args).join(', ')})</p>
                )}
              </div>
              <label className="flex items-center gap-2 text-xs text-slate-300">
                {t('tool_enabled')}
                <input
                  type="checkbox"
                  role="switch"
                  disabled={busy || coordination(tool.name)}
                  checked={tool.enabled}
                  onChange={(event) => void handle.run(`tool:${tool.name}`, () => updateTool(tool.name, { enabled: event.target.checked }), 'team_tool_failed')}
                  className="h-5 w-9 accent-cyan-400"
                />
              </label>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
                <ShieldCheck className={`h-3.5 w-3.5 ${tool.confirm || tool.alwaysConfirm ? 'text-amber-300' : 'text-slate-600'}`} aria-hidden="true" />
                <input
                  type="checkbox"
                  disabled={busy}
                  checked={tool.alwaysConfirm}
                  onChange={(event) => void handle.run(`tool:${tool.name}`, () => updateTool(tool.name, { always_confirm: event.target.checked }), 'team_tool_failed')}
                  className="accent-amber-400"
                />
                {tool.confirm && !tool.alwaysConfirm ? t('confirm_builtin') : t('confirm_always')}
              </label>
              <label className="ml-auto flex items-center gap-1.5 text-[11px] text-slate-400">
                {t('owner')}
                <select
                  disabled={busy || coordination(tool.name)}
                  value={tool.owner}
                  onChange={(event) =>
                    void handle.run(`tool:${tool.name}`, () => updateTool(tool.name, { agent: event.target.value === tool.defaultOwner ? '' : event.target.value }), 'team_tool_failed')
                  }
                  className={`${fieldClass} py-1 text-xs`}
                >
                  {agents.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                      {a.id === tool.defaultOwner ? ` (${t('default_short')})` : ''}
                    </option>
                  ))}
                </select>
              </label>
              {tool.custom && (
                <button
                  type="button"
                  disabled={busy}
                  aria-label={t('delete_tool')}
                  onClick={() => void handle.run(`tool:${tool.name}`, () => deleteTool(tool.name), 'team_tool_failed')}
                  className="rounded-lg p-1.5 text-slate-500 transition hover:text-rose-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-300"
                >
                  <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
      <div className="flex gap-2 border-t border-slate-800/80 pt-3">
        <select value={adding} onChange={(event) => setAdding(event.target.value)} aria-label={t('assign_tool')} className={`${fieldClass} min-w-0 flex-1`}>
          <option value="">{t('assign_tool')}</option>
          {others.map((tool) => (
            <option key={tool.name} value={tool.name}>
              {tool.name} — {agents.find((a) => a.id === tool.owner)?.name ?? tool.owner}
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={busy || !adding}
          onClick={() => void handle.run('assign', () => updateTool(adding, { agent: agent.id }), 'team_tool_failed').then((ok) => ok && setAdding(''))}
          className={`${chipClass} border-cyan-400/50 bg-cyan-400/10 px-3 text-cyan-100`}
        >
          {t('assign')}
        </button>
      </div>
    </div>
  );
};
