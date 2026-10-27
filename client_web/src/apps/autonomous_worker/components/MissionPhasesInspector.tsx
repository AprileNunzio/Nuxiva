import React, { useState } from 'react';
import {
  AlertCircle,
  Brain,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Circle,
  FileCheck,
  ShieldCheck,
  Terminal,
} from 'lucide-react';
import { useAutonomousI18n } from '../scope';
import { Mission, Task } from '../types';

interface Props {
  mission: Mission;
}

export const MissionPhasesInspector: React.FC<Props> = ({ mission }) => {
  const { t } = useAutonomousI18n();
  const [expandedTaskIds, setExpandedTaskIds] = useState<Record<string, boolean>>({});

  function toggleTask(taskId: string) {
    setExpandedTaskIds((prev) => ({ ...prev, [taskId]: !prev[taskId] }));
  }

  function statusBadgeClass(status: string) {
    switch (status) {
      case 'done':
        return 'border-emerald-700/50 bg-emerald-950/50 text-emerald-300';
      case 'running':
        return 'border-cyan-500/60 bg-cyan-950/60 text-cyan-200 animate-pulse';
      case 'review':
        return 'border-amber-500/60 bg-amber-950/60 text-amber-200';
      case 'failed':
        return 'border-rose-700/60 bg-rose-950/60 text-rose-300';
      default:
        return 'border-slate-700 bg-slate-900 text-slate-400';
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
          {t('phases_title')}
        </h3>
        <span className="text-xs text-slate-400">{t('task_click_to_inspect')}</span>
      </div>

      {mission.phases.map((phase) => (
        <div
          key={phase.id}
          className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-4"
        >
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2.5">
            <div>
              <h4 className="font-bold text-slate-100">{phase.title}</h4>
              <p className="text-xs text-slate-400">{phase.description}</p>
            </div>
            <span className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 font-mono text-[10px] uppercase text-cyan-400">
              {phase.status}
            </span>
          </div>

          <div className="flex flex-col gap-2.5">
            {phase.tasks.map((task: Task) => {
              const isOpen =
                expandedTaskIds[task.id] ?? (task.status === 'running' || task.status === 'review');
              const stepsCount = task.reasoning_steps?.length || 0;
              const doubtsCount = task.doubts?.length || 0;

              return (
                <div
                  key={task.id}
                  className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/60 transition"
                >
                  <button
                    type="button"
                    onClick={() => toggleTask(task.id)}
                    className="flex w-full flex-wrap items-center justify-between gap-2 p-3.5 text-left hover:bg-slate-900/60"
                  >
                    <div className="flex items-center gap-2.5">
                      {isOpen ? (
                        <ChevronDown className="h-4 w-4 text-cyan-400" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-slate-400" />
                      )}
                      <span className="font-mono text-[11px] text-slate-500">{task.id}</span>
                      <span className="text-xs font-bold text-slate-100">{task.title}</span>
                      <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-cyan-400">
                        {task.specialist_role}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 text-[10px]">
                      {stepsCount > 0 && (
                        <span className="rounded border border-indigo-800/50 bg-indigo-950/40 px-2 py-0.5 text-indigo-300">
                          {stepsCount} {t('task_reasoning_badge')}
                        </span>
                      )}
                      {doubtsCount > 0 && (
                        <span className="rounded border border-amber-800/50 bg-amber-950/40 px-2 py-0.5 text-amber-300">
                          {doubtsCount} {t('task_doubts_badge')}
                        </span>
                      )}
                      <span className="font-mono text-slate-500">R{task.round}</span>
                      <span
                        className={`rounded border px-2 py-0.5 font-mono uppercase ${statusBadgeClass(
                          task.status
                        )}`}
                      >
                        {task.status}
                      </span>
                    </div>
                  </button>

                  {isOpen && (
                    <div className="flex flex-col gap-4 border-t border-slate-800/80 bg-slate-950/90 p-4 text-xs">
                      {task.description && (
                        <div>
                          <span className="font-semibold uppercase tracking-wider text-slate-400">
                            {t('task_description_label')}:
                          </span>
                          <p className="mt-1 text-slate-200">{task.description}</p>
                        </div>
                      )}

                      {task.criteria && task.criteria.length > 0 && (
                        <div>
                          <div className="mb-1.5 flex items-center gap-1.5 font-semibold uppercase tracking-wider text-slate-400">
                            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                            {t('task_acceptance_criteria')}
                          </div>
                          <div className="grid gap-1.5 sm:grid-cols-2">
                            {task.criteria.map((c, idx) => (
                              <div
                                key={idx}
                                className={`flex items-start gap-2 rounded-lg border p-2 ${
                                  c.verified
                                    ? 'border-emerald-900/40 bg-emerald-950/20 text-emerald-200'
                                    : 'border-slate-800 bg-slate-900/50 text-slate-300'
                                }`}
                              >
                                {c.verified ? (
                                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />
                                ) : (
                                  <Circle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" />
                                )}
                                <div>
                                  <div className="font-medium">{c.description}</div>
                                  {c.target && (
                                    <div className="text-[10px] text-slate-400">
                                      Target: {c.target}
                                    </div>
                                  )}
                                  {c.evidence && (
                                    <div className="mt-0.5 text-[10px] text-emerald-400">
                                      {c.evidence}
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {task.reasoning_steps && task.reasoning_steps.length > 0 && (
                        <div>
                          <div className="mb-2 flex items-center gap-1.5 font-semibold uppercase tracking-wider text-indigo-300">
                            <Brain className="h-3.5 w-3.5" />
                            {t('task_reasoning_chain')} ({task.reasoning_steps.length})
                          </div>
                          <div className="flex flex-col gap-2">
                            {task.reasoning_steps.map((step) => (
                              <div
                                key={step.step_index}
                                className="rounded-xl border border-indigo-900/30 bg-indigo-950/15 p-3"
                              >
                                <div className="flex items-center justify-between text-[10px] text-indigo-300">
                                  <span className="font-mono font-bold">
                                    Step #{step.step_index}
                                  </span>
                                  {step.tool_name && (
                                    <span className="flex items-center gap-1 rounded bg-slate-900 px-2 py-0.5 font-mono text-cyan-300">
                                      <Terminal className="h-3 w-3" />
                                      {step.tool_name}
                                    </span>
                                  )}
                                </div>
                                <p className="mt-1.5 text-slate-200">{step.thought}</p>
                                {step.doubt && (
                                  <p className="mt-1 rounded bg-amber-950/40 px-2 py-1 text-[11px] text-amber-300">
                                    {t('task_doubt_prefix')}: {step.doubt}
                                  </p>
                                )}
                                {step.tool_output && (
                                  <pre className="mt-2 max-h-32 overflow-x-auto rounded-lg border border-slate-800 bg-slate-950 p-2 font-mono text-[10px] text-slate-300">
                                    {step.tool_output}
                                  </pre>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {task.ceo_review_notes && task.ceo_review_notes.length > 0 && (
                        <div className="rounded-xl border border-cyan-900/40 bg-cyan-950/15 p-3">
                          <div className="mb-1 font-semibold uppercase tracking-wider text-cyan-300">
                            {t('task_ceo_review_notes')}
                          </div>
                          <ul className="flex flex-col gap-1 text-slate-200">
                            {task.ceo_review_notes.map((note, idx) => (
                              <li key={idx}>• {note}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {task.feedback && (
                        <div className="flex items-start gap-2 rounded-xl border border-amber-700/40 bg-amber-950/25 p-3 text-amber-200">
                          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
                          <div>
                            <span className="font-bold">{t('task_ceo_rework_feedback')}:</span>{' '}
                            {task.feedback}
                          </div>
                        </div>
                      )}

                      {task.result && (
                        <div>
                          <div className="mb-1.5 flex items-center gap-1.5 font-semibold uppercase tracking-wider text-emerald-300">
                            <FileCheck className="h-3.5 w-3.5" />
                            {t('task_executive_result')}
                          </div>
                          <pre className="max-h-72 overflow-y-auto whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-900/80 p-3 font-mono text-[11px] leading-relaxed text-slate-200">
                            {task.result}
                          </pre>
                        </div>
                      )}

                      {task.error && (
                        <div className="rounded-xl border border-rose-800/50 bg-rose-950/30 p-3 text-rose-300">
                          {task.error}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};
