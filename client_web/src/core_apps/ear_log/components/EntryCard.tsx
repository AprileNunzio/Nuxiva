import React, { useState } from 'react';
import { Check, Pause, Play, Trash2, X } from 'lucide-react';
import { Btn, Pill, formatTime } from '../../shared/kit';
import { audioUrl, deleteEntry, sendFeedback } from '../api';
import { EarEntry, EarPerson } from '../types';
import { FeedbackForm } from './FeedbackForm';

interface Props {
  readonly entry: EarEntry;
  readonly people: readonly EarPerson[];
  readonly busy: boolean;
  readonly lang: string;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly run: <R>(task: () => Promise<R>, code?: string) => Promise<R | null>;
}

export const EntryCard: React.FC<Props> = ({ entry, people, busy, lang, t, run }) => {
  const [playing, setPlaying] = useState(false);
  const [editing, setEditing] = useState(false);
  const name = (slug: string) => people.find((person) => person.slug === slug)?.name ?? slug;
  const shown = entry.speaker ? name(entry.speaker) : t('speaker_unknown');

  return (
    <li className="rounded-xl border border-slate-800/70 bg-slate-950/50 p-3">
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
        <span>{formatTime(entry.ts, lang)}</span>
        <Pill tone={entry.kind === 'command' ? 'cyan' : 'slate'}>{t(entry.kind === 'command' ? 'kind_command' : 'kind_heard')}</Pill>
        <Pill tone={entry.speaker ? 'purple' : 'slate'}>{shown}</Pill>
        {entry.speaker ? <span>{t('score', { pct: Math.round(entry.score * 100) })}</span> : null}
        {entry.dur > 0 ? <span>{t('duration', { s: entry.dur.toFixed(1) })}</span> : null}
        {entry.live ? <Pill tone="emerald">{t('live_badge')}</Pill> : null}
        {entry.verdict === 'ok' ? <Pill tone="emerald">{t('verdict_ok')}</Pill> : null}
        {entry.verdict === 'wrong' ? <Pill tone="rose">{t('verdict_wrong')}</Pill> : null}
        {entry.verdict ? <span>{entry.applied ? t('applied') : t('queued')}</span> : null}
      </div>
      <p className="mt-1.5 text-sm text-slate-100">{entry.text}</p>
      {entry.correction ? (
        <p className="mt-1 text-sm text-emerald-300">
          <span className="text-[11px] uppercase tracking-wide text-slate-500">{t('correction_label')}: </span>
          {entry.correction}
        </p>
      ) : null}
      {entry.fixSpeaker ? <p className="mt-0.5 text-xs text-purple-300">{t('speaker_label')} {name(entry.fixSpeaker)}</p> : null}
      {entry.note ? <p className="mt-0.5 text-xs text-slate-400">{entry.note}</p> : null}
      {playing && entry.audio ? <audio className="mt-2 h-8 w-full" controls autoPlay src={audioUrl(entry.id)} onEnded={() => setPlaying(false)} /> : null}
      <div className="mt-2 flex flex-wrap gap-2">
        <Btn tone="slate" disabled={!entry.audio} onClick={() => setPlaying((value) => !value)} title={entry.audio ? t('play') : t('no_audio')}>
          {playing ? <Pause className="h-3.5 w-3.5" aria-hidden="true" /> : <Play className="h-3.5 w-3.5" aria-hidden="true" />}
          {playing ? t('hide_audio') : entry.audio ? t('play') : t('no_audio')}
        </Btn>
        <Btn tone="emerald" busy={busy} disabled={entry.verdict === 'ok'} onClick={() => void run(() => sendFeedback(entry.id, { verdict: 'ok', correction: '', speaker: '', note: '' }), 'ear_log_failed')}>
          <Check className="h-3.5 w-3.5" aria-hidden="true" />
          {t('ok')}
        </Btn>
        <Btn tone="rose" disabled={busy} onClick={() => setEditing((value) => !value)}>
          <X className="h-3.5 w-3.5" aria-hidden="true" />
          {t('wrong')}
        </Btn>
        <Btn tone="slate" busy={busy} onClick={() => void run(() => deleteEntry(entry.id), 'ear_log_failed')} title={t('delete')}>
          <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
        </Btn>
      </div>
      {editing ? <FeedbackForm entry={entry} people={people} busy={busy} t={t} run={run} onClose={() => setEditing(false)} /> : null}
    </li>
  );
};
