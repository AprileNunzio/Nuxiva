import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, HelpCircle, MessageCircleQuestion } from 'lucide-react';
import { answerQuestion } from '../api';
import { inputFieldClass, primaryBtnClass, useAutonomousI18n } from '../scope';
import { Mission } from '../types';

interface Props {
  mission: Mission;
  onUpdate: (updated: Mission) => void;
}

export const MissionQuestionsPanel: React.FC<Props> = ({ mission, onUpdate }) => {
  const { t } = useAutonomousI18n();
  const [ansTextMap, setAnsTextMap] = useState<Record<string, string>>({});
  const [selectedOptsMap, setSelectedOptsMap] = useState<Record<string, string[]>>({});
  const [busyId, setBusyId] = useState<string | null>(null);

  const unanswered = mission.questions.filter((q) => !q.answered);
  const answered = mission.questions.filter((q) => q.answered);
  const taskDoubts = mission.phases
    .flatMap((p) => p.tasks)
    .flatMap((tk) =>
      (tk.doubts || []).map((d) => ({
        taskId: tk.id,
        taskTitle: tk.title,
        role: tk.specialist_role,
        doubt: d,
      }))
    );

  function toggleOpt(qid: string, opt: string, isMulti: boolean) {
    setSelectedOptsMap((prev) => {
      const current = prev[qid] || [];
      if (!isMulti) {
        return { ...prev, [qid]: current.includes(opt) ? [] : [opt] };
      }
      return {
        ...prev,
        [qid]: current.includes(opt) ? current.filter((o) => o !== opt) : [...current, opt],
      };
    });
  }

  async function handleAnswer(qid: string) {
    const text = (ansTextMap[qid] || '').trim();
    const opts = selectedOptsMap[qid] || [];
    if (!text && opts.length === 0) return;
    setBusyId(qid);
    try {
      const updated = await answerQuestion(mission.id, qid, text, opts);
      onUpdate(updated);
      setAnsTextMap((p) => ({ ...p, [qid]: '' }));
      setSelectedOptsMap((p) => ({ ...p, [qid]: [] }));
    } finally {
      setBusyId(null);
    }
  }

  if (unanswered.length === 0 && answered.length === 0 && taskDoubts.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-amber-800/40 bg-slate-900/50 p-5">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <MessageCircleQuestion className="h-5 w-5 text-amber-400" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-amber-200">
            {t('doubts_and_questions_title')}
          </h3>
        </div>
        <div className="flex gap-2 text-[11px]">
          <span className="rounded bg-amber-950/60 px-2 py-0.5 font-semibold text-amber-300">
            {t('doubts_pending_count', { count: unanswered.length })}
          </span>
          <span className="rounded bg-emerald-950/60 px-2 py-0.5 font-semibold text-emerald-300">
            {t('doubts_resolved_count', { count: answered.length })}
          </span>
        </div>
      </div>

      {unanswered.map((q) => {
        const selected = selectedOptsMap[q.id] || [];
        const ansVal = ansTextMap[q.id] || '';
        return (
          <div
            key={q.id}
            className="flex flex-col gap-3 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="flex items-center gap-1.5 text-xs font-bold text-amber-300">
                <HelpCircle className="h-4 w-4" />
                {t('question_pending')}
              </span>
              {q.asked_by && (
                <span className="rounded bg-slate-900/80 px-2 py-0.5 font-mono text-[10px] text-amber-200">
                  {q.asked_by}
                </span>
              )}
            </div>
            <p className="text-sm font-medium text-slate-100">{q.question}</p>
            {q.rationale && (
              <p className="rounded-lg border border-amber-500/20 bg-slate-950/50 p-2.5 text-xs text-slate-300">
                <span className="font-semibold text-amber-300">{t('question_rationale_label')}:</span>{' '}
                {q.rationale}
              </p>
            )}
            {q.options.length > 0 && (
              <div className="grid gap-2 sm:grid-cols-2">
                {q.options.map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    onClick={() => toggleOpt(q.id, opt, q.is_multi_select)}
                    className={`rounded-xl border p-2.5 text-left text-xs transition ${
                      selected.includes(opt)
                        ? 'border-amber-400 bg-amber-400/20 font-semibold text-white'
                        : 'border-slate-700 bg-slate-900/70 text-slate-300 hover:border-slate-600'
                    }`}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            )}
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                type="text"
                placeholder={t('question_optional_details')}
                value={ansVal}
                onChange={(e) => setAnsTextMap((p) => ({ ...p, [q.id]: e.target.value }))}
                className={inputFieldClass}
              />
              <button
                type="button"
                onClick={() => void handleAnswer(q.id)}
                disabled={busyId === q.id || (!ansVal.trim() && selected.length === 0)}
                className={primaryBtnClass}
              >
                {t('answer_btn')}
              </button>
            </div>
          </div>
        );
      })}

      {taskDoubts.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-amber-300/90">
            <AlertTriangle className="h-3.5 w-3.5" />
            {t('specialist_technical_doubts')} ({taskDoubts.length})
          </h4>
          <div className="grid gap-2 md:grid-cols-2">
            {taskDoubts.map((item, idx) => (
              <div
                key={`${item.taskId}-${idx}`}
                className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-xs"
              >
                <div className="mb-1 flex items-center justify-between text-[10px] text-slate-400">
                  <span className="font-semibold text-cyan-400">{item.role}</span>
                  <span>{item.taskTitle}</span>
                </div>
                <p className="text-slate-200">{item.doubt}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {answered.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-emerald-300/90">
            <CheckCircle2 className="h-3.5 w-3.5" />
            {t('resolved_questions_history')} ({answered.length})
          </h4>
          <div className="grid gap-2 md:grid-cols-2">
            {answered.map((q) => (
              <div
                key={q.id}
                className="rounded-xl border border-emerald-900/30 bg-emerald-950/15 p-3 text-xs"
              >
                <p className="font-semibold text-slate-200">{q.question}</p>
                {q.rationale && <p className="mt-0.5 text-[11px] text-slate-400">{q.rationale}</p>}
                <div className="mt-2 rounded-lg bg-slate-950/60 px-2.5 py-1.5 font-medium text-emerald-300">
                  ✓ {q.answer || (q.selected_options || []).join(', ')}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
