import React, { useState } from 'react';
import type { AgentAction } from '../types';
import { useStudioI18n } from '../scope';

interface ThoughtActionBlockProps {
  thought?: string;
  thinkingDuration?: string;
  actions?: AgentAction[];
  onOpenDiff?: (diffId?: string) => void;
}

export const ThoughtActionBlock: React.FC<ThoughtActionBlockProps> = ({
  thought,
  thinkingDuration,
  actions = [],
  onOpenDiff,
}) => {
  const { t } = useStudioI18n();
  const [isThoughtOpen, setIsThoughtOpen] = useState(false);
  const [expandedActionIds, setExpandedActionIds] = useState<Record<string, boolean>>({});

  const toggleActionDetail = (actionId: string) => {
    setExpandedActionIds((prev) => ({
      ...prev,
      [actionId]: !prev[actionId],
    }));
  };

  const hasThought = Boolean(thought && thought.trim().length > 0);
  const hasActions = actions.length > 0;

  if (!hasThought && !hasActions) {
    return null;
  }

  return (
    <div className="w-full max-w-2xl flex flex-col gap-1.5 my-1.5 text-xs text-slate-400 select-text">
      {hasThought && (
        <div className="flex flex-col">
          <button
            type="button"
            onClick={() => setIsThoughtOpen((prev) => !prev)}
            className="flex items-center gap-1.5 py-1 text-slate-400 hover:text-slate-200 transition-colors w-fit group"
          >
            <span className="font-medium text-slate-300">{t('tab_thinking')}</span>
            <span className="text-slate-500 font-mono text-[11px] group-hover:text-slate-400">
              {thinkingDuration}
            </span>
            <span className="text-slate-500 text-[10px] transition-transform duration-200">
              {isThoughtOpen ? '▲' : '▼'}
            </span>
          </button>

          {isThoughtOpen && (
            <div className="mt-1 p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-slate-300 font-mono text-xs whitespace-pre-wrap leading-relaxed shadow-inner">
              {thought}
            </div>
          )}
        </div>
      )}

      {hasActions && (
        <div className="flex flex-col gap-1 pl-1 border-l-2 border-slate-800/80 ml-1 py-0.5">
          {actions.map((act) => {
            const isEdit = act.kind === 'edit';
            const isAnalyze = act.kind === 'analyze';
            const isDetailOpen = Boolean(expandedActionIds[act.id]);

            return (
              <div key={act.id} className="flex flex-col">
                <div className="flex items-center gap-2 py-0.5 group">
                  {act.kind === 'wait' && (
                    <span className="text-slate-400 flex items-center gap-1.5">
                      <span className="text-slate-500">⏱</span>
                      <span>{act.label}</span>
                      <span className="text-slate-600">›</span>
                    </span>
                  )}

                  {act.kind === 'command' && (
                    <button
                      type="button"
                      onClick={() => toggleActionDetail(act.id)}
                      className="text-left text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition-colors"
                    >
                      <span className="text-slate-500">⚙</span>
                      <span>{act.label}</span>
                      <span className="text-slate-600">{isDetailOpen ? '˅' : '›'}</span>
                    </button>
                  )}

                  {act.kind === 'task' && (
                    <button
                      type="button"
                      onClick={() => toggleActionDetail(act.id)}
                      className="text-left text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition-colors"
                    >
                      <span className="text-slate-500">✓</span>
                      <span>{act.label}</span>
                    </button>
                  )}

                  {isAnalyze && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-400">{t('tab_analyzed')}</span>
                      {act.ext && (
                        <span className="px-1 py-0.2 rounded bg-cyan-950/80 border border-cyan-800/60 text-[10px] font-mono text-cyan-300 uppercase">
                          {act.ext}
                        </span>
                      )}
                      <span className="text-slate-300 font-mono">{act.target}</span>
                      {act.lines && (
                        <span className="text-slate-500 font-mono text-[11px]">{act.lines}</span>
                      )}
                    </div>
                  )}

                  {isEdit && (
                    <button
                      type="button"
                      onClick={() => onOpenDiff?.(act.diff_id)}
                      className="flex items-center gap-1.5 hover:text-slate-200 transition-colors cursor-pointer group/edit"
                      title={t('tab_diff_hint')}
                    >
                      <span className="text-slate-400 group-hover/edit:text-cyan-300">{t('tab_edited')}</span>
                      {act.ext && (
                        <span className="px-1 py-0.2 rounded bg-cyan-950/80 border border-cyan-800/60 text-[10px] font-mono text-cyan-300 uppercase">
                          {act.ext}
                        </span>
                      )}
                      <span className="text-slate-200 font-mono group-hover/edit:underline">
                        {act.target}
                      </span>
                      {act.added !== undefined && act.removed !== undefined && (
                        <div className="flex items-center gap-1 font-mono text-[11px] ml-1">
                          <span className="text-emerald-400">+{act.added}</span>
                          <span className="text-rose-400">-{act.removed}</span>
                        </div>
                      )}
                      <span className="text-cyan-400 text-[10px] opacity-0 group-hover/edit:opacity-100 transition-opacity ml-1">
                        [Diff ↗]
                      </span>
                    </button>
                  )}

                  {act.kind === 'think' && (
                    <span className="text-slate-500 flex items-center gap-1 italic">
                      <span>{t('tab_thinking_for')}</span>
                      <span className="font-mono">{act.duration}</span>
                    </span>
                  )}
                </div>

                {isDetailOpen && act.detail && (
                  <div className="ml-5 my-1 p-2 rounded-lg bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-300 whitespace-pre-wrap">
                    {act.detail}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
