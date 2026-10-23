import React, { useState } from 'react';
import { Btn, Field, inputClass } from '../../shared/kit';
import { sendFeedback } from '../api';
import { EarEntry, EarPerson } from '../types';

interface Props {
  readonly entry: EarEntry;
  readonly people: readonly EarPerson[];
  readonly busy: boolean;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly run: <R>(task: () => Promise<R>, code?: string) => Promise<R | null>;
  readonly onClose: () => void;
}

export const FeedbackForm: React.FC<Props> = ({ entry, people, busy, t, run, onClose }) => {
  const [correction, setCorrection] = useState(entry.correction || entry.text);
  const [speaker, setSpeaker] = useState(entry.fixSpeaker);
  const [note, setNote] = useState(entry.note);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const changed = correction.trim() === entry.text.trim() ? '' : correction.trim();
    const saved = await run(() => sendFeedback(entry.id, { verdict: 'wrong', correction: changed, speaker, note: note.trim() }), 'ear_log_failed');
    if (saved !== null) {
      onClose();
    }
  };

  return (
    <form onSubmit={submit} className="mt-3 grid gap-3 rounded-xl border border-rose-500/30 bg-rose-500/5 p-3">
      <p className="text-xs font-semibold text-rose-200">{t('wrong_title')}</p>
      <Field label={t('correction_label')}>
        <input className={inputClass} value={correction} maxLength={600} onChange={(event) => setCorrection(event.target.value)} />
      </Field>
      <Field label={t('speaker_label')}>
        <select className={inputClass} value={speaker} onChange={(event) => setSpeaker(event.target.value)}>
          <option value="">{t('speaker_keep')}</option>
          {people.map((person) => (
            <option key={person.slug} value={person.slug}>
              {person.name}
            </option>
          ))}
        </select>
      </Field>
      <Field label={t('note_label')}>
        <input className={inputClass} value={note} maxLength={300} onChange={(event) => setNote(event.target.value)} />
      </Field>
      <div className="flex gap-2">
        <Btn type="submit" tone="rose" busy={busy}>
          {t('send')}
        </Btn>
        <Btn tone="slate" onClick={onClose}>
          {t('cancel')}
        </Btn>
      </div>
    </form>
  );
};
