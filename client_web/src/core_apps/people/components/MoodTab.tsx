import React, { FormEvent, useEffect, useState } from 'react';
import { Check, Plus, Sparkles, Trash2, X } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { MoodEntry, addMood, deleteMood, fetchMood, moodFeedback } from '../data/peopleApi';
import { chipClass, fieldClass, usePeopleI18n } from '../scope';

const TONE: Readonly<Record<string, string>> = {
  felice: 'bg-emerald-400', sereno: 'bg-teal-400', entusiasta: 'bg-lime-400', innamorato: 'bg-pink-400', grato: 'bg-emerald-300',
  neutro: 'bg-slate-400', stanco: 'bg-indigo-400', annoiato: 'bg-slate-500', stressato: 'bg-amber-400', preoccupato: 'bg-orange-400',
  triste: 'bg-sky-500', arrabbiato: 'bg-rose-500', malato: 'bg-purple-500',
};

interface Props {
  readonly slug: string;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
}

export const MoodTab: React.FC<Props> = ({ slug, busy, run }) => {
  const { t, lang } = usePeopleI18n();
  const [moods, setMoods] = useState<readonly string[]>([]);
  const [journal, setJournal] = useState<readonly MoodEntry[] | null>(null);
  const [mood, setMood] = useState('');
  const [intensity, setIntensity] = useState(3);
  const [note, setNote] = useState('');
  const [tick, setTick] = useState(0);
  const format = new Intl.DateTimeFormat(lang, { dateStyle: 'medium', timeStyle: 'short' });

  useEffect(() => {
    const controller = new AbortController();
    fetchMood(slug, controller.signal)
      .then((data) => {
        setMoods(data.moods);
        setJournal(data.journal);
      })
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_mood_failed', cause));
    return () => controller.abort();
  }, [slug, tick]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (mood && (await run('mood', () => addMood(slug, mood, intensity, note.trim()), 'people_mood_failed'))) {
      setNote('');
      setTick((v) => v + 1);
    }
  };
  const act = async (key: string, task: () => Promise<unknown>) => {
    if (await run(key, task, 'people_mood_failed')) {
      setTick((v) => v + 1);
    }
  };
  const recent = (journal ?? []).slice(0, 30).reverse();

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs text-slate-600">{t('mood_hint')}</p>
      {recent.length > 0 && (
        <div className="flex h-24 items-end gap-1 rounded-xl border border-slate-200 bg-slate-50 p-3" role="img" aria-label={t('mood_timeline')}>
          {recent.map((e) => (
            <span key={e.id} className={`w-full max-w-[18px] flex-1 rounded-t opacity-90 ${TONE[e.mood] ?? 'bg-slate-500'}`} style={{ height: `${e.intensity * 20}%` }} title={`${format.format(new Date(e.at * 1000))} · ${t(`mood_${e.mood}`)}`} />
          ))}
        </div>
      )}
      <form onSubmit={submit} className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_10rem] xl:grid-cols-[minmax(0,1fr)_12rem_minmax(0,2fr)_auto]">
        <select value={mood} onChange={(event) => setMood(event.target.value)} aria-label={t('mood')} className={fieldClass}>
          <option value="">{t('mood_pick')}</option>
          {moods.map((m) => (
            <option key={m} value={m}>
              {t(`mood_${m}`)}
            </option>
          ))}
        </select>
        <label className="flex min-w-0 items-center gap-2 text-xs text-slate-600">
          {t('intensity')}
          <input type="range" min={1} max={5} value={intensity} onChange={(event) => setIntensity(Number(event.target.value))} className="min-w-0 flex-1 accent-cyan-400" />
          <span className="font-mono text-slate-900">{intensity}</span>
        </label>
        <input maxLength={300} value={note} onChange={(event) => setNote(event.target.value)} placeholder={t('mood_note')} aria-label={t('mood_note')} className={fieldClass} />
        <button type="submit" disabled={!mood || busy !== null} className={`${chipClass} justify-center border-blue-300 bg-blue-50 py-2 text-blue-900`}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          {t('add_mood')}
        </button>
      </form>
      {journal !== null && journal.length === 0 && <p className="text-sm text-slate-500">{t('mood_empty')}</p>}
      <ul className="grid gap-2 xl:grid-cols-2 4xl:grid-cols-3">
        {(journal ?? []).map((e) => (
          <li key={e.id} className="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
            <span className={`mt-1 h-3 w-3 shrink-0 rounded-full ${TONE[e.mood] ?? 'bg-slate-500'}`} aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <p className="text-sm text-slate-900">
                {t(`mood_${e.mood}`)} <span className="font-mono text-xs text-slate-600">{e.intensity}/5</span>
              </p>
              {e.note && <p className="text-xs text-slate-700">{e.note}</p>}
              {e.evidence && <p className="text-xs italic text-slate-600">«{e.evidence}»</p>}
              <p className="text-[10px] text-slate-500">{[format.format(new Date(e.at * 1000)), t(`source_${e.source}`), e.feedback && t(`feedback_${e.feedback}`)].filter(Boolean).join(' · ')}</p>
              {e.source === 'assistente' && e.feedback === '' && (
                <div className="mt-2 flex flex-wrap items-center gap-1.5" role="group" aria-label={t('mood_feedback')}>
                  <Sparkles className="h-3.5 w-3.5 text-blue-700" aria-hidden="true" />
                  <button type="button" disabled={busy !== null} onClick={() => void act(`mood-ok:${e.id}`, () => moodFeedback(slug, e.id, 'ok'))} className={`${chipClass} border-emerald-300 px-2 text-emerald-800`}>
                    <Check className="h-3 w-3" aria-hidden="true" />
                    {t('feedback_right')}
                  </button>
                  <button type="button" disabled={busy !== null} onClick={() => void act(`mood-no:${e.id}`, () => moodFeedback(slug, e.id, 'wrong'))} className={`${chipClass} border-rose-300 px-2 text-rose-800`}>
                    <X className="h-3 w-3" aria-hidden="true" />
                    {t('feedback_wrong')}
                  </button>
                  <select
                    aria-label={t('feedback_fix')}
                    value=""
                    disabled={busy !== null}
                    onChange={(event) => event.target.value && void act(`mood-fix:${e.id}`, () => moodFeedback(slug, e.id, 'wrong', { mood: event.target.value, intensity: e.intensity }))}
                    className={`${fieldClass} w-auto py-0.5 text-xs`}
                  >
                    <option value="">{t('feedback_fix')}</option>
                    {moods.filter((m) => m !== e.mood).map((m) => (
                      <option key={m} value={m}>
                        {t(`mood_${m}`)}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
            <button
              type="button"
              disabled={busy !== null}
              aria-label={t('delete_mood')}
              onClick={() => void run(`mood:${e.id}`, () => deleteMood(slug, e.id), 'people_mood_failed').then((ok) => ok && setTick((v) => v + 1))}
              className="rounded-lg p-1 text-slate-500 hover:text-rose-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-300"
            >
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};
