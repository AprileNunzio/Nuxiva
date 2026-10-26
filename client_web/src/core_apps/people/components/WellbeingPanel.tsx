import React, { useCallback, useEffect, useState } from 'react';
import { Download, ShieldCheck, Trash2 } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { WellbeingState, downloadReport, eraseWellbeing, fetchWellbeing, setWellbeingConsent, startSession } from '../data/wellbeingApi';
import { chipClass, primaryClass, usePeopleI18n } from '../scope';
import { LiveAffect } from './LiveAffect';
import { SessionChat } from './SessionChat';

interface Props {
  readonly slug: string;
}

const REFRESH_MS = 2500;

export const WellbeingPanel: React.FC<Props> = ({ slug }) => {
  const { t, lang } = usePeopleI18n();
  const [state, setState] = useState<WellbeingState | null>(null);
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState(false);
  const [moodBefore, setMoodBefore] = useState(5);
  const [full, setFull] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetchWellbeing(slug, controller.signal)
      .then(setState)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_wellbeing_failed', cause));
    return () => controller.abort();
  }, [slug, tick]);

  useEffect(() => {
    const timer = window.setInterval(() => setTick((v) => v + 1), REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  const act = useCallback(async (task: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await task();
    } catch (cause) {
      reportError('people_wellbeing_failed', cause);
    } finally {
      setBusy(false);
      setTick((v) => v + 1);
    }
  }, []);

  if (!state) {
    return null;
  }
  const next = state.nextAt ? new Intl.DateTimeFormat(lang, { dateStyle: 'full' }).format(new Date(state.nextAt * 1000)) : '';

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <header className="flex flex-wrap items-center gap-2">
        <ShieldCheck className="h-5 w-5 text-emerald-700" aria-hidden="true" />
        <h2 className="text-base font-bold text-slate-900">{t('wb_title')}</h2>
        <label className="ml-auto flex items-center gap-2 text-xs font-semibold text-slate-800">
          <input type="checkbox" checked={state.consent} disabled={busy} onChange={(e) => void act(() => setWellbeingConsent(slug, e.target.checked))} className="h-4 w-4 accent-emerald-600" />
          {t('wb_consent')}
        </label>
      </header>
      <p className="text-xs text-slate-700">{t('wb_hint')}</p>
      <p className="text-xs text-slate-600">{t('wb_privacy')}</p>

      <LiveAffect live={state.live} />

      {state.consent && state.session && <SessionChat key={state.session.id} slug={slug} session={state.session} onDone={() => setTick((v) => v + 1)} />}

      {state.consent && !state.session && (
        <section className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-900">
            <span className="font-semibold">{t(`wb_stage_${state.stage}`)}</span>
            {state.concluded && <span className="rounded-full border border-emerald-300 px-2 py-0.5 text-xs text-emerald-800">{t('wb_concluded')}</span>}
            {next && <span className="text-xs text-slate-600">{t(state.due ? 'wb_due' : 'wb_next', { date: next })}</span>}
          </div>
          <label className="flex items-center gap-3 text-xs text-slate-800">
            {t('wb_mood_before')}
            <input type="range" min={0} max={10} value={moodBefore} onChange={(e) => setMoodBefore(Number(e.target.value))} className="max-w-xs flex-1 accent-blue-600" />
            <span className="font-mono">{moodBefore}</span>
          </label>
          <button type="button" disabled={busy} onClick={() => void act(() => startSession(slug, lang, moodBefore))} className={`${primaryClass} self-start`}>
            {t('wb_start')}
          </button>
        </section>
      )}

      <footer className="flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-1.5 text-xs text-slate-700">
          <input type="checkbox" checked={full} onChange={(e) => setFull(e.target.checked)} className="h-4 w-4" />
          {t('wb_report_full')}
        </label>
        <button type="button" disabled={busy} onClick={() => void act(() => downloadReport(slug, lang, full))} className={`${chipClass} border-blue-300 px-3 py-1.5 text-blue-900`}>
          <Download className="h-3.5 w-3.5" aria-hidden="true" />
          {t('wb_report')}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => window.confirm(t('wb_erase_confirm')) && void act(() => eraseWellbeing(slug))}
          className={`${chipClass} ml-auto border-rose-300 px-3 py-1.5 text-rose-800`}
        >
          <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
          {t('wb_erase')}
        </button>
      </footer>
      <p className="text-[11px] text-slate-600">{t('wb_disclaimer')}</p>
    </div>
  );
};
