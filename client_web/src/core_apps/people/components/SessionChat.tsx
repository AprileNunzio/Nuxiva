import React, { FormEvent, useEffect, useRef, useState } from 'react';
import { HeartHandshake, Send } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Turn, WellSession, closeSession, sendTurn } from '../data/wellbeingApi';
import { chipClass, fieldClass, primaryClass, usePeopleI18n } from '../scope';

interface Props {
  readonly slug: string;
  readonly session: WellSession;
  readonly onDone: () => void;
}

export const SessionChat: React.FC<Props> = ({ slug, session, onDone }) => {
  const { t } = usePeopleI18n();
  const [turns, setTurns] = useState<readonly Turn[]>(session.turns);
  const [phase, setPhase] = useState(session.phase);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [crisis, setCrisis] = useState(false);
  const [nearing, setNearing] = useState(false);
  const [rating, setRating] = useState(5);
  const [closing, setClosing] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end' });
  }, [turns]);

  const send = async (event: FormEvent) => {
    event.preventDefault();
    const message = text.trim();
    if (!message || busy) {
      return;
    }
    setBusy(true);
    setText('');
    setTurns((prev) => [...prev, { role: 'user', text: message }]);
    try {
      const result = await sendTurn(slug, session.id, message);
      setTurns((prev) => [...prev, { role: 'assistant', text: result.reply }]);
      setPhase(result.phase);
      setNearing(result.nearingEnd);
      setCrisis(result.crisis);
    } catch (cause) {
      reportError('people_wellbeing_failed', cause);
    } finally {
      setBusy(false);
    }
  };

  const finish = async () => {
    setBusy(true);
    try {
      await closeSession(slug, session.id, rating);
      onDone();
    } catch (cause) {
      reportError('people_wellbeing_failed', cause);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4" aria-labelledby="wb-session">
      <header className="flex flex-wrap items-center gap-2">
        <HeartHandshake className="h-4 w-4 text-rose-700" aria-hidden="true" />
        <h3 id="wb-session" className="font-semibold text-slate-900">
          {t(`wb_stage_${session.stage}`)}
        </h3>
        <span className="rounded-full border border-slate-300 px-2 py-0.5 text-xs text-slate-700">{t(`wb_phase_${phase}`)}</span>
        <button type="button" onClick={() => setClosing(true)} className={`${chipClass} ml-auto border-slate-300 text-slate-800`}>
          {t('wb_close')}
        </button>
      </header>
      {crisis && (
        <p role="alert" className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-900">
          {t('wb_crisis')}
        </p>
      )}
      {(nearing || phase === 'closing') && !closing && <p className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">{t('wb_nearing')}</p>}
      <div className="flex max-h-[26rem] min-h-[10rem] flex-col gap-2 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-3" aria-live="polite">
        {turns.map((turn, index) => (
          <p key={index} className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm ${turn.role === 'user' ? 'self-end bg-blue-600 text-white' : 'self-start border border-slate-200 bg-white text-slate-900'}`}>
            {turn.text}
          </p>
        ))}
        <div ref={end} />
      </div>
      {closing ? (
        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-800">
          <label className="flex min-w-0 flex-1 items-center gap-2">
            {t('wb_mood_after')}
            <input type="range" min={0} max={10} value={rating} onChange={(e) => setRating(Number(e.target.value))} className="min-w-0 flex-1 accent-blue-600" />
            <span className="font-mono">{rating}</span>
          </label>
          <button type="button" disabled={busy} onClick={() => void finish()} className={primaryClass}>
            {t('wb_finish')}
          </button>
          <button type="button" onClick={() => setClosing(false)} className={`${chipClass} border-slate-300`}>
            {t('wb_cancel')}
          </button>
        </div>
      ) : (
        <form onSubmit={(e) => void send(e)} className="flex gap-2">
          <input value={text} maxLength={4000} onChange={(e) => setText(e.target.value)} placeholder={t('wb_placeholder')} aria-label={t('wb_placeholder')} className={fieldClass} />
          <button type="submit" disabled={busy || !text.trim()} className={primaryClass}>
            <Send className="h-4 w-4" aria-hidden="true" />
            {t('wb_send')}
          </button>
        </form>
      )}
    </section>
  );
};
