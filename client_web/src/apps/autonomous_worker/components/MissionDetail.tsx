import React, { useState } from 'react';
import {
  Brain,
  Compass,
  FileCode2,
  GitBranch,
  HelpCircle,
  Layers,
  MessageSquare,
  Pause,
  Play,
  RotateCcw,
  Send,
  XOctagon,
} from 'lucide-react';
import { addDirective, controlMission } from '../api';
import { inputFieldClass, primaryBtnClass, secondaryBtnClass, useAutonomousI18n } from '../scope';
import { Mission } from '../types';
import { ArtifactDiffExplorer } from './ArtifactDiffExplorer';
import { CEOOrganizationCard } from './CEOOrganizationCard';
import { CollabStreamPanel } from './CollabStreamPanel';
import { MissionDAGVisualizer } from './MissionDAGVisualizer';
import { MissionMemoryCard } from './MissionMemoryCard';
import { MissionPhasesInspector } from './MissionPhasesInspector';
import { MissionQuestionsPanel } from './MissionQuestionsPanel';
import { MissionWatchdogCard } from './MissionWatchdogCard';

interface Props {
  mission: Mission;
  onUpdate: (updated: Mission) => void;
}

type DetailSection =
  | 'all'
  | 'ceo'
  | 'reasoning'
  | 'doubts'
  | 'diffs'
  | 'collab'
  | 'memory';

export const MissionDetail: React.FC<Props> = ({ mission, onUpdate }) => {
  const { t } = useAutonomousI18n();
  const [directiveText, setDirectiveText] = useState('');
  const [busy, setBusy] = useState(false);
  const [section, setSection] = useState<DetailSection>('all');

  async function handleControl(action: string) {
    setBusy(true);
    try {
      const updated = await controlMission(mission.id, action);
      onUpdate(updated);
    } finally {
      setBusy(false);
    }
  }

  async function handleSendDirective(e: React.FormEvent) {
    e.preventDefault();
    if (!directiveText.trim()) return;
    setBusy(true);
    try {
      const updated = await addDirective(mission.id, directiveText.trim());
      onUpdate(updated);
      setDirectiveText('');
    } finally {
      setBusy(false);
    }
  }

  const allTasks = mission.phases.flatMap((p) => p.tasks);
  const doneTasks = allTasks.filter((tk) => tk.status === 'done').length;
  const totalDoubts =
    mission.questions.filter((q) => !q.answered).length +
    allTasks.reduce((acc, tk) => acc + (tk.doubts?.length || 0), 0);
  const totalReasoning = allTasks.reduce(
    (acc, tk) => acc + (tk.reasoning_steps?.length || 0),
    0
  );

  const navItems: Array<{ id: DetailSection; label: string; icon: React.ReactNode; badge?: number }> = [
    { id: 'all', label: t('subtab_all'), icon: <Layers className="h-3.5 w-3.5" /> },
    { id: 'ceo', label: t('subtab_ceo'), icon: <Compass className="h-3.5 w-3.5" />, badge: mission.specialists.length },
    { id: 'reasoning', label: t('subtab_reasoning'), icon: <GitBranch className="h-3.5 w-3.5" />, badge: totalReasoning },
    { id: 'doubts', label: t('subtab_doubts'), icon: <HelpCircle className="h-3.5 w-3.5" />, badge: totalDoubts },
    { id: 'diffs', label: t('subtab_diffs'), icon: <FileCode2 className="h-3.5 w-3.5" />, badge: mission.artifacts.length },
    { id: 'collab', label: t('subtab_collab'), icon: <MessageSquare className="h-3.5 w-3.5" />, badge: mission.collab_messages.length },
    { id: 'memory', label: t('subtab_memory'), icon: <Brain className="h-3.5 w-3.5" /> },
  ];

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-bold text-slate-100">{mission.title}</h2>
              <span className="rounded-lg border border-cyan-700/50 bg-cyan-950/60 px-2.5 py-0.5 font-mono text-xs uppercase text-cyan-300">
                {mission.status} · {mission.progress}%
              </span>
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-300">{mission.goal}</p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {(mission.status === 'running' || mission.status === 'question' || mission.status === 'planning') && (
              <button
                type="button"
                onClick={() => void handleControl('pause')}
                disabled={busy}
                className={secondaryBtnClass}
              >
                <Pause className="h-4 w-4" />
                {t('action_pause')}
              </button>
            )}
            {mission.status === 'paused' && (
              <button
                type="button"
                onClick={() => void handleControl('resume')}
                disabled={busy}
                className={secondaryBtnClass}
              >
                <Play className="h-4 w-4" />
                {t('action_resume')}
              </button>
            )}
            {mission.status === 'failed' && (
              <button
                type="button"
                onClick={() => void handleControl('retry')}
                disabled={busy}
                className={secondaryBtnClass}
              >
                <RotateCcw className="h-4 w-4" />
                {t('action_retry')}
              </button>
            )}
            <button
              type="button"
              onClick={() => void handleControl('cancel')}
              disabled={busy}
              className={secondaryBtnClass}
            >
              <XOctagon className="h-4 w-4 text-rose-400" />
              {t('action_cancel')}
            </button>
          </div>
        </div>

        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all duration-500"
            style={{ width: `${mission.progress}%` }}
          />
        </div>

        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <span className="text-[10px] uppercase tracking-wider text-slate-400">{t('stat_tasks')}</span>
            <div className="mt-0.5 font-mono text-lg font-bold text-white">
              {doneTasks}/{allTasks.length}
            </div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <span className="text-[10px] uppercase tracking-wider text-slate-400">{t('subtab_reasoning')}</span>
            <div className="mt-0.5 font-mono text-lg font-bold text-indigo-300">{totalReasoning}</div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <span className="text-[10px] uppercase tracking-wider text-slate-400">{t('subtab_doubts')}</span>
            <div className="mt-0.5 font-mono text-lg font-bold text-amber-300">{totalDoubts}</div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <span className="text-[10px] uppercase tracking-wider text-slate-400">{t('stat_artifacts')}</span>
            <div className="mt-0.5 font-mono text-lg font-bold text-emerald-300">
              {mission.artifacts.length}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-1.5 border-t border-slate-800 pt-3">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setSection(item.id)}
              className={`flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                section === item.id
                  ? 'bg-cyan-600 text-white shadow-md shadow-cyan-600/25'
                  : 'border border-slate-800 bg-slate-950/60 text-slate-300 hover:bg-slate-800'
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
              {item.badge !== undefined && item.badge > 0 && (
                <span className="rounded-full bg-slate-950/50 px-1.5 py-0.2 font-mono text-[10px]">
                  {item.badge}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={(e) => void handleSendDirective(e)} className="flex flex-col gap-2 sm:flex-row">
        <input
          type="text"
          placeholder={t('add_directive')}
          value={directiveText}
          onChange={(e) => setDirectiveText(e.target.value)}
          className={inputFieldClass}
        />
        <button type="submit" disabled={busy || !directiveText.trim()} className={primaryBtnClass}>
          <Send className="h-4 w-4" />
          {t('send_directive')}
        </button>
      </form>

      {(section === 'all' || section === 'doubts') && (
        <MissionQuestionsPanel mission={mission} onUpdate={onUpdate} />
      )}

      {(section === 'all' || section === 'ceo') && <CEOOrganizationCard mission={mission} />}

      {(section === 'all' || section === 'reasoning') && (
        <>
          <MissionDAGVisualizer missionId={mission.id} t={t} />
          <MissionPhasesInspector mission={mission} />
        </>
      )}

      {(section === 'all' || section === 'diffs') && <ArtifactDiffExplorer mission={mission} />}

      {(section === 'all' || section === 'collab') && <CollabStreamPanel mission={mission} />}

      {(section === 'all' || section === 'memory') && (
        <>
          <MissionMemoryCard mission={mission} onUpdate={onUpdate} />
          <MissionWatchdogCard missionId={mission.id} t={t} />
        </>
      )}
    </div>
  );
};
