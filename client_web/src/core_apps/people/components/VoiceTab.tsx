import React, { useEffect, useState } from 'react';
import { Loader2, Mic, Save, Trash2 } from 'lucide-react';
import { Profile, forgetVoiceTraining, forgetVoiceprint, startVoiceTraining, updatePerson, voiceprintOf } from '../data/peopleApi';
import { chipClass, fieldClass, primaryClass, relative, usePeopleI18n } from '../scope';

interface VoiceTabProps {
  readonly slug: string;
  readonly profile: Profile;
  readonly voices: Readonly<Record<string, string>>;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
}

const record = (value: unknown): Record<string, unknown> => (typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {});

export const VoiceTab: React.FC<VoiceTabProps> = ({ slug, profile, voices, busy, run }) => {
  const { t, lang } = usePeopleI18n();
  const voice = record(profile.voice);
  const training = record(profile.voice_training);
  const print = voiceprintOf(profile);
  const [tts, setTts] = useState(String(voice.tts_voice ?? ''));
  const [speed, setSpeed] = useState(Number(voice.speed ?? 1));
  useEffect(() => {
    setTts(String(voice.tts_voice ?? ''));
    setSpeed(Number(voice.speed ?? 1));
  }, [voice.tts_voice, voice.speed]);
  const dirty = tts !== String(voice.tts_voice ?? '') || speed !== Number(voice.speed ?? 1);
  const stale = training.stale === true;
  const conditions = record(training.conditions);
  const tips = Array.isArray(training.tips) ? (training.tips as string[]) : [];
  const dictionary = Array.isArray(training.dictionary) ? (training.dictionary as Record<string, unknown>[]) : [];

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <section className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
        <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-600">{t('voice_speaks')}</h3>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('tts_voice')}
          <select value={tts} onChange={(event) => setTts(event.target.value)} className={fieldClass}>
            <option value="">{t('voice_default')}</option>
            {Object.entries(voices).map(([id, label]) => (
              <option key={id} value={id}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          <span className="flex justify-between">
            {t('voice_speed')}
            <span className="font-mono text-slate-900">{speed.toFixed(2)}×</span>
          </span>
          <input type="range" min={0.5} max={2} step={0.05} value={speed} onChange={(event) => setSpeed(Number(event.target.value))} className="accent-cyan-400" />
        </label>
        <button type="button" disabled={!dirty || busy !== null} onClick={() => void run('voice', () => updatePerson(slug, { voice: { tts_voice: tts, speed } }), 'people_update_failed')} className={`${primaryClass} self-start`}>
          {busy === 'voice' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="h-4 w-4" aria-hidden="true" />}
          {t('save')}
        </button>
      </section>
      <section className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
        <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-600">{t('voice_recognition')}</h3>
        <p className={`text-sm ${print.enrolled ? 'text-emerald-700' : 'text-slate-600'}`}>
          {print.enrolled ? t('voiceprint_ready', { samples: print.samples }) : t('voiceprint_missing', { samples: print.samples })}
        </p>
        {stale && <p className="rounded-lg border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900">{t('training_stale', { name: String(training.assistant ?? '') })}</p>}
        {!stale && typeof training.score === 'number' && (
          <p className="text-xs text-slate-600">
            {t('training_result', { score: training.score, when: relative(Number(training.trained_at ?? 0), lang) })}
          </p>
        )}
        {!stale && Object.keys(conditions).length > 0 && (
          <ul className="grid gap-1 text-xs text-slate-700 sm:grid-cols-2">
            {Object.entries(conditions).map(([key, value]) => {
              const group = record(value);
              return (
                <li key={key} className="flex justify-between rounded-lg border border-slate-200 px-2 py-1">
                  <span>{t(`condition_${key}`)}</span>
                  <span className="font-mono">{String(group.ok ?? 0)}/{String(group.total ?? 0)}</span>
                </li>
              );
            })}
          </ul>
        )}
        {!stale && tips.map((tip) => (
          <p key={tip} className="text-xs text-amber-800">{t(`training_tip_${tip}`)}</p>
        ))}
        {!stale && dictionary.length > 0 && (
          <ul className="max-h-40 overflow-y-auto rounded-lg border border-slate-200 p-2 text-xs text-slate-700">
            {dictionary.slice(0, 30).map((row, i) => (
              <li key={i}>
                «{String(row.said ?? '')}» → <span className="text-blue-800">«{String(row.heard ?? '')}»</span>
              </li>
            ))}
          </ul>
        )}
        <div className="flex flex-wrap gap-2">
          <button type="button" disabled={busy !== null} onClick={() => void run('training', () => startVoiceTraining(slug), 'people_voice_failed')} className={`${chipClass} border-blue-300 bg-blue-50 py-2 text-blue-900`}>
            <Mic className="h-3.5 w-3.5" aria-hidden="true" />
            {t('start_training')}
          </button>
          {typeof training.score === 'number' && (
            <button type="button" disabled={busy !== null} onClick={() => void run('training', () => forgetVoiceTraining(slug), 'people_voice_failed')} className={`${chipClass} border-slate-300 py-2 text-slate-700`}>
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              {t('forget_training')}
            </button>
          )}
          {print.samples > 0 && (
            <button type="button" disabled={busy !== null} onClick={() => void run('voiceprint', () => forgetVoiceprint(slug), 'people_voice_failed')} className={`${chipClass} border-rose-300 py-2 text-rose-800`}>
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              {t('forget_voiceprint')}
            </button>
          )}
        </div>
        <p className="text-[11px] text-slate-500">{t('training_hint')}</p>
      </section>
    </div>
  );
};
