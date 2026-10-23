import React, { useEffect, useState } from 'react';
import { ShieldAlert } from 'lucide-react';
import { Btn, Field, Panel, Pill, inputClass } from '../../shared/kit';
import { reasonCode, runReset } from '../api';
import { ResetChallenge, ResetOptions, Translate } from '../types';

interface Props {
  readonly challenge: ResetChallenge;
  readonly options: ResetOptions;
  readonly onBack: () => void;
  readonly onExpired: () => void;
  readonly onStarted: (id: string) => void;
  readonly t: Translate;
}

export const ConfirmStep: React.FC<Props> = ({ challenge, options, onBack, onExpired, onStarted, t }) => {
  const [phrase, setPhrase] = useState('');
  const [understood, setUnderstood] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setElapsed((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (elapsed >= challenge.expiresIn) onExpired();
  }, [elapsed, challenge.expiresIn, onExpired]);

  const wait = Math.max(0, challenge.waitSeconds - elapsed);
  const matches = phrase.trim() === challenge.phrase;
  const ready = wait === 0 && matches && understood && !busy;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!ready) return;
    setBusy(true);
    setError('');
    try {
      onStarted(await runReset(challenge, phrase.trim(), options));
    } catch (cause) {
      setError(t(`err_${reasonCode(cause)}`));
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} autoComplete="off">
      <Panel title={t('confirm_title')} icon={<ShieldAlert className="h-4 w-4 text-rose-300" aria-hidden="true" />}>
        <p className="text-sm text-slate-300">{t('confirm_body')}</p>
        <p className="my-4 select-all rounded-xl border border-rose-500/40 bg-slate-950 px-4 py-3 text-center font-mono text-xl tracking-[0.3em] text-rose-200" aria-label={t('phrase_label')}>
          {challenge.phrase}
        </p>
        <Field label={t('phrase_label')}>
          <input
            className={inputClass}
            value={phrase}
            maxLength={32}
            autoCapitalize="characters"
            autoCorrect="off"
            spellCheck={false}
            aria-invalid={phrase.length > 0 && !matches}
            onChange={(event) => setPhrase(event.target.value.toUpperCase())}
            onPaste={(event) => event.preventDefault()}
          />
        </Field>
        <label className="mt-3 flex items-start gap-2 text-sm text-slate-300">
          <input className="mt-1" type="checkbox" checked={understood} onChange={(event) => setUnderstood(event.target.checked)} />
          <span>{t('understood')}</span>
        </label>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <Pill tone={wait > 0 ? 'amber' : 'emerald'}>{wait > 0 ? t('wait_left', { s: wait }) : t('wait_over')}</Pill>
          <span>{t('expires_in', { s: Math.max(0, challenge.expiresIn - elapsed) })}</span>
        </div>
        {error ? (
          <div className="mt-3" role="alert">
            <Pill tone="rose">{error}</Pill>
          </div>
        ) : null}
        <div className="mt-4 flex justify-between gap-2">
          <Btn tone="slate" onClick={onBack} disabled={busy}>
            {t('back')}
          </Btn>
          <Btn tone="rose" type="submit" busy={busy} disabled={!ready}>
            {t('erase_now')}
          </Btn>
        </div>
      </Panel>
    </form>
  );
};
