import React, { useState } from 'react';
import {
  CheckCircle,
  Clock,
  FileCode,
  HelpCircle,
  MessageSquare,
  Pause,
  Play,
  RotateCcw,
  Send,
  Users,
  XOctagon,
} from 'lucide-react';
import { addDirective, answerQuestion, controlMission } from '../api';
import { inputFieldClass, primaryBtnClass, secondaryBtnClass, useAutonomousI18n } from '../scope';
import { Mission, Task } from '../types';
import { MissionMemoryCard } from './MissionMemoryCard';

interface Props {
  mission: Mission;
  onUpdate: (updated: Mission) => void;
}

export const MissionDetail: React.FC<Props> = ({ mission, onUpdate }) => {
  const { t } = useAutonomousI18n();
  const [ansText, setAnsText] = useState('');
  const [selectedOpts, setSelectedOpts] = useState<string[]>([]);
  const [directiveText, setDirectiveText] = useState('');
  const [busy, setBusy] = useState(false);

  async function handleControl(action: string) {
    setBusy(true);
    try {
      const updated = await controlMission(mission.id, action);
      onUpdate(updated);
    } finally {
      setBusy(false);
    }
  }

  async function handleAnswer(qid: string) {
    if (!ansText.trim() && selectedOpts.length === 0) return;
    setBusy(true);
    try {
      const updated = await answerQuestion(mission.id, qid, ansText, selectedOpts);
      onUpdate(updated);
      setAnsText('');
      setSelectedOpts([]);
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

  const activeQuestion = mission.questions.find((q) => !q.answered);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
        <div>
          <h2 className="text-xl font-bold text-slate-100">{mission.title}</h2>
          <p className="mt-1 text-xs text-slate-400">{mission.goal}</p>
        </div>
        <div className="flex items-center gap-2">
          {mission.status === 'running' && (
            <button type="button" onClick={() => void handleControl('pause')} disabled={busy} className={secondaryBtnClass}>
              <Pause className="h-4 w-4" />
              {t('action_pause')}
            </button>
          )}
          {mission.status === 'paused' && (
            <button type="button" onClick={() => void handleControl('resume')} disabled={busy} className={secondaryBtnClass}>
              <Play className="h-4 w-4" />
              {t('action_resume')}
            </button>
          )}
          {mission.status === 'failed' && (
            <button type="button" onClick={() => void handleControl('retry')} disabled={busy} className={secondaryBtnClass}>
              <RotateCcw className="h-4 w-4" />
              {t('action_retry')}
            </button>
          )}
          <button type="button" onClick={() => void handleControl('cancel')} disabled={busy} className={secondaryBtnClass}>
            <XOctagon className="h-4 w-4 text-rose-400" />
            {t('action_cancel')}
          </button>
        </div>
      </div>

      {activeQuestion && (
        <div className="flex flex-col gap-3 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-5">
          <div className="flex items-center gap-2 font-semibold text-amber-300">
            <HelpCircle className="h-5 w-5" />
            {t('question_pending')}
          </div>
          <p className="text-sm text-slate-200">{activeQuestion.question}</p>
          {activeQuestion.options.length > 0 && (
            <div className="grid gap-2 sm:grid-cols-2">
              {activeQuestion.options.map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() =>
                    setSelectedOpts((prev) =>
                      prev.includes(opt) ? prev.filter((o) => o !== opt) : [...prev, opt]
                    )
                  }
                  className={`rounded-xl border p-2 text-left text-xs transition ${
                    selectedOpts.includes(opt)
                      ? 'border-amber-400 bg-amber-400/20 text-white'
                      : 'border-slate-700 bg-slate-900/60 text-slate-300 hover:border-slate-600'
                  }`}
                >
                  {opt}
                </button>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Inserisci dettagli opzionali..."
              value={ansText}
              onChange={(e) => setAnsText(e.target.value)}
              className={inputFieldClass}
            />
            <button
              type="button"
              onClick={() => void handleAnswer(activeQuestion.id)}
              disabled={busy}
              className={primaryBtnClass}
            >
              {t('answer_btn')}
            </button>
          </div>
        </div>
      )}

      <MissionMemoryCard mission={mission} onUpdate={onUpdate} />

      <div className="flex flex-col gap-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          {t('phases_title')}
        </h3>
        <div className="flex flex-col gap-3">
          {mission.phases.map((phase) => (
            <div key={phase.id} className="rounded-2xl border border-slate-800 bg-slate-900/30 p-4">
              <h4 className="font-semibold text-slate-200">{phase.title}</h4>
              <p className="mb-3 text-xs text-slate-400">{phase.description}</p>
              <div className="flex flex-col gap-2">
                {phase.tasks.map((task: Task) => (
                  <div
                    key={task.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-850 bg-slate-950/40 p-3 text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-300">{task.title}</span>
                      <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-cyan-400">
                        {task.specialist_role}
                      </span>
                    </div>
                    <span className="font-mono uppercase text-slate-400">{task.status}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          {t('collab_title')}
        </h3>
        <div className="flex max-h-60 flex-col gap-2 overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900/30 p-4">
          {mission.collab_messages.slice(-15).map((msg) => (
            <div key={msg.id} className="rounded-lg border border-slate-800 bg-slate-950/40 p-2 text-xs">
              <div className="flex justify-between font-mono text-[10px] text-slate-500">
                <span>{msg.sender_role || msg.sender_id}</span>
                <span>{msg.kind}</span>
              </div>
              <p className="mt-1 text-slate-200">{msg.content}</p>
            </div>
          ))}
        </div>
      </div>

      <form onSubmit={(e) => void handleSendDirective(e)} className="flex gap-2">
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
    </div>
  );
};
