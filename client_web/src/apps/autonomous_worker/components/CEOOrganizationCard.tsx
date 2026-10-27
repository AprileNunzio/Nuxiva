import React from 'react';
import { Award, Bot, CheckCircle2, Compass, ShieldAlert, Sparkles, Users, Wrench } from 'lucide-react';
import { useAutonomousI18n } from '../scope';
import { Mission, Specialist } from '../types';

interface Props {
  mission: Mission;
}

export const CEOOrganizationCard: React.FC<Props> = ({ mission }) => {
  const { t } = useAutonomousI18n();
  const council = mission.council_verdict;
  const allTasks = mission.phases.flatMap((p) => p.tasks);
  const feasibilityPct = Math.round(((council?.feasibility_score ?? 0.95) * 100));

  function getSpecialistActiveTask(spec: Specialist) {
    return allTasks.find(
      (tk) =>
        (tk.specialist_id === spec.id || tk.specialist_role === spec.role) &&
        (tk.status === 'running' || tk.status === 'review')
    );
  }

  function getSpecialistDoneCount(spec: Specialist) {
    return allTasks.filter(
      (tk) =>
        (tk.specialist_id === spec.id || tk.specialist_role === spec.role) &&
        tk.status === 'done'
    ).length;
  }

  return (
    <div className="flex flex-col gap-5 rounded-2xl border border-cyan-900/40 bg-gradient-to-br from-slate-900/80 via-slate-900/50 to-cyan-950/20 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-cyan-500/15 p-2.5 text-cyan-400">
            <Compass className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-cyan-200">
              {t('ceo_org_title')}
            </h3>
            <p className="text-xs text-slate-400">{t('ceo_org_subtitle')}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-lg border border-emerald-700/50 bg-emerald-950/40 px-2.5 py-1 text-xs font-semibold text-emerald-300">
            {t('ceo_feasibility')}: {feasibilityPct}%
          </span>
          <span className="rounded-lg border border-cyan-700/50 bg-cyan-950/40 px-2.5 py-1 text-xs font-mono text-cyan-300">
            {council?.architecture_pattern || 'Clean Architecture'}
          </span>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-amber-900/30 bg-amber-950/10 p-3.5">
          <div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-300">
            <ShieldAlert className="h-4 w-4" />
            {t('ceo_identified_risks')}
          </div>
          {council?.identified_risks && council.identified_risks.length > 0 ? (
            <ul className="flex flex-col gap-1.5 text-xs text-slate-300">
              {council.identified_risks.map((risk, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="font-bold text-amber-400">▲</span>
                  <span>{risk}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs italic text-slate-500">{t('ceo_no_risks')}</p>
          )}
        </div>

        <div className="rounded-xl border border-cyan-900/30 bg-cyan-950/10 p-3.5">
          <div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cyan-300">
            <Award className="h-4 w-4" />
            {t('ceo_mandatory_guidelines')}
          </div>
          {mission.directives && mission.directives.length > 0 ? (
            <ul className="flex flex-col gap-1.5 text-xs text-slate-300">
              {mission.directives.map((dir, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-cyan-400" />
                  <span>{dir}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs italic text-slate-500">{t('ceo_default_guidelines')}</p>
          )}
        </div>
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-300">
            <Users className="h-4 w-4 text-cyan-400" />
            {t('specialists_title')} ({mission.specialists.length})
          </div>
        </div>
        {mission.specialists.length === 0 ? (
          <p className="text-xs italic text-slate-500">{t('ceo_no_specialists')}</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {mission.specialists.map((spec) => {
              const activeTask = getSpecialistActiveTask(spec);
              const doneCount = getSpecialistDoneCount(spec);
              return (
                <div
                  key={spec.id}
                  className={`flex flex-col justify-between gap-2.5 rounded-xl border p-3.5 transition ${
                    activeTask
                      ? 'border-cyan-500/60 bg-cyan-950/25 shadow-md shadow-cyan-950/30'
                      : 'border-slate-800 bg-slate-950/50'
                  }`}
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Bot className={`h-4 w-4 shrink-0 ${activeTask ? 'animate-pulse text-cyan-400' : 'text-slate-400'}`} />
                        <span className="text-xs font-bold text-slate-100">{spec.role}</span>
                      </div>
                      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-300">
                        {doneCount} OK
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] text-slate-400">{spec.title}</p>
                    {activeTask && (
                      <div className="mt-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1.5 text-[11px] text-cyan-200">
                        <Sparkles className="mr-1 inline h-3 w-3" />
                        {activeTask.title}
                      </div>
                    )}
                  </div>
                  {spec.tools && spec.tools.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1 pt-1">
                      <Wrench className="mr-1 h-3 w-3 text-slate-500" />
                      {spec.tools.slice(0, 4).map((toolName) => (
                        <span
                          key={toolName}
                          className="rounded border border-slate-800 bg-slate-900 px-1.5 py-0.5 font-mono text-[10px] text-slate-400"
                        >
                          {toolName}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
