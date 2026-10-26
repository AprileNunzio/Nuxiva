import React, { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Check, Eraser, Loader2, MessageCircle, SendHorizontal, ShieldAlert, X } from 'lucide-react';
import { reportError } from '../../../../shared/errors/errorBus';
import { fieldClass } from '../../scope';
import { AskResult, ChatTurn, Expert, PendingAction, SKILL_STEP, Skill, askExpert, confirmExpert, fetchHistory, forgetChat } from '../data/expertsApi';
import { glassClass, labelClass, useExpertsI18n } from '../scope';
import { ExpertAvatar } from './ExpertAvatar';

const LIMIT = 2000;

interface ExpertChatProps {
  readonly expert: Expert;
  readonly skills: readonly Skill[];
  readonly onChange: () => void;
}

export const ExpertChat: React.FC<ExpertChatProps> = ({ expert, skills, onChange }) => {
  const { t } = useExpertsI18n();
  const skillNames = useMemo(() => new Map(skills.map((s) => [s.id, s.name])), [skills]);
  const [turns, setTurns] = useState<readonly ChatTurn[]>([]);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [draft, setDraft] = useState('');
  const [thinking, setThinking] = useState(false);
  const scroller = useRef<HTMLOListElement>(null);

  const reload = useCallback(
    async (signal?: AbortSignal) => {
      const history = await fetchHistory(expert.id, signal);
      setTurns(history.turns);
      setPending(history.pending);
    },
    [expert.id],
  );

  useEffect(() => {
    const controller = new AbortController();
    setTurns([]);
    setPending(null);
    reload(controller.signal).catch((cause: unknown) => {
      if (!controller.signal.aborted) {
        reportError('experts_unavailable', cause);
      }
    });
    return () => controller.abort();
  }, [reload]);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: 'smooth' });
  }, [turns, thinking, pending]);

  const settle = async (task: () => Promise<AskResult>) => {
    setThinking(true);
    try {
      const result = await task();
      setPending(result.pending);
      await reload();
    } catch (cause) {
      reportError('expert_ask_failed', cause);
    } finally {
      setThinking(false);
      onChange();
    }
  };

  const submit = (event: FormEvent | React.KeyboardEvent) => {
    event.preventDefault();
    const question = draft.trim();
    if (!question || thinking) {
      return;
    }
    setDraft('');
    setTurns((prev) => [...prev, { at: Date.now() / 1000, role: 'user', text: question, steps: [] }]);
    void settle(() => askExpert(expert.id, question));
  };

  const clear = async () => {
    try {
      await forgetChat(expert.id);
      setTurns([]);
    } catch (cause) {
      reportError('expert_update_failed', cause);
    }
  };

  return (
    <section className={`${glassClass} flex min-h-[26rem] flex-col`} aria-labelledby="expert-chat">
      <h3 id="expert-chat" className={labelClass}>
        <MessageCircle className="h-3.5 w-3.5 text-cyan-700" aria-hidden="true" />
        {t('chat_title', { role: expert.role })}
        {turns.length > 0 && (
          <button type="button" onClick={() => void clear()} className="ml-auto flex items-center gap-1 rounded-lg px-2 py-1 text-[0.625rem] normal-case tracking-normal text-slate-600 hover:text-slate-950 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400">
            <Eraser className="h-3 w-3" aria-hidden="true" />
            {t('chat_clear')}
          </button>
        )}
      </h3>
      <ol ref={scroller} className="flex max-h-[32rem] flex-1 flex-col gap-3 overflow-y-auto pr-1 3xl:max-h-[48rem]" aria-live="polite">
        {turns.length === 0 && !thinking && <li className="m-auto max-w-sm text-center text-sm text-slate-500">{t('chat_empty', { role: expert.role, specialty: expert.specialty })}</li>}
        {turns.map((turn, i) =>
          turn.role === 'user' ? (
            <li key={`${turn.at}-${i}`} className="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-gradient-to-br from-cyan-100 to-indigo-100 px-3.5 py-2 text-sm text-slate-950">
              {turn.text}
            </li>
          ) : (
            <li key={`${turn.at}-${i}`} className="flex max-w-[92%] gap-2">
              <ExpertAvatar icon={expert.icon} color={expert.color} />
              <div className="min-w-0 rounded-2xl rounded-tl-md border border-slate-300 bg-white px-3.5 py-2">
                <p className="whitespace-pre-wrap break-words text-sm text-slate-900">{turn.text}</p>
                {turn.steps.length > 0 && (
                  <p className="mt-2 flex flex-wrap gap-1" aria-label={t('chat_steps')}>
                    {turn.steps.map((s, n) =>
                      s.tool.startsWith(SKILL_STEP) ? (
                        <span key={`${s.tool}-${n}`} className="rounded-full border border-indigo-300 bg-indigo-50 px-2 py-0.5 text-[0.625rem] font-semibold text-indigo-900">
                          ✦ {skillNames.get(s.tool.slice(SKILL_STEP.length)) ?? s.tool.slice(SKILL_STEP.length)}
                        </span>
                      ) : (
                        <span key={`${s.tool}-${n}`} className={`rounded-full border px-2 py-0.5 font-mono text-[0.625rem] ${s.ok ? 'border-emerald-300 text-emerald-800' : 'border-rose-300 text-rose-800'}`}>
                          {s.tool}
                        </span>
                      ),
                    )}
                  </p>
                )}
              </div>
            </li>
          ),
        )}
        {thinking && (
          <li className="flex items-center gap-2 text-sm text-slate-600" role="status">
            <Loader2 className="h-4 w-4 animate-spin" style={{ color: expert.color }} aria-hidden="true" />
            {t('chat_thinking', { role: expert.role })}
          </li>
        )}
        {pending && !thinking && (
          <li className="rounded-2xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-50">
            <p className="flex items-center gap-2 font-semibold">
              <ShieldAlert className="h-4 w-4" aria-hidden="true" />
              {t('confirm_title', { role: expert.role })}
            </p>
            <pre className="mt-2 overflow-x-auto rounded-lg bg-white p-2 font-mono text-[0.6875rem] text-amber-900">{`${pending.tool} ${JSON.stringify(pending.args)}`}</pre>
            <div className="mt-2 flex gap-2">
              <button type="button" onClick={() => void settle(() => confirmExpert(expert.id, true))} className="flex items-center gap-1 rounded-xl bg-amber-400 px-3 py-1.5 text-xs font-bold text-slate-950 hover:brightness-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-200">
                <Check className="h-3.5 w-3.5" aria-hidden="true" />
                {t('confirm_yes')}
              </button>
              <button type="button" onClick={() => void settle(() => confirmExpert(expert.id, false))} className="flex items-center gap-1 rounded-xl border border-slate-300 px-3 py-1.5 text-xs text-slate-800 hover:text-slate-950 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400">
                <X className="h-3.5 w-3.5" aria-hidden="true" />
                {t('confirm_no')}
              </button>
            </div>
          </li>
        )}
      </ol>
      <form onSubmit={submit} className="mt-3 flex items-end gap-2">
        <label className="sr-only" htmlFor="expert-question">
          {t('chat_placeholder', { role: expert.role })}
        </label>
        <textarea
          id="expert-question"
          value={draft}
          maxLength={LIMIT}
          rows={1}
          disabled={!expert.enabled}
          placeholder={expert.enabled ? t('chat_placeholder', { role: expert.role }) : t('chat_disabled')}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              submit(e);
            }
          }}
          className={`${fieldClass} max-h-40 min-h-[2.75rem] flex-1 resize-y rounded-2xl`}
        />
        <button
          type="submit"
          disabled={!draft.trim() || thinking || !expert.enabled}
          aria-label={t('chat_send')}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-indigo-500 text-slate-950 shadow-[0_0_20px_rgba(34,211,238,0.35)] transition hover:brightness-110 disabled:opacity-40 disabled:shadow-none focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200"
        >
          <SendHorizontal className="h-5 w-5" aria-hidden="true" />
        </button>
      </form>
    </section>
  );
};
