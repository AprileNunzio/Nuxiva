import React, { useState } from 'react';
import { KeyRound } from 'lucide-react';
import { Btn, Field, Panel, Pill, inputClass } from '../../shared/kit';
import { openChallenge, reasonCode } from '../api';
import { ResetChallenge, ResetOptions, Translate } from '../types';

interface Props {
  readonly options: ResetOptions;
  readonly onBack: () => void;
  readonly onIssued: (challenge: ResetChallenge) => void;
  readonly t: Translate;
}

export const IdentityStep: React.FC<Props> = ({ options, onBack, onIssued, t }) => {
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!password || busy) return;
    setBusy(true);
    setError('');
    try {
      const challenge = await openChallenge(password, options);
      setPassword('');
      onIssued(challenge);
    } catch (cause) {
      setPassword('');
      setError(t(`err_${reasonCode(cause)}`));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} autoComplete="off">
      <Panel title={t('identity_title')} icon={<KeyRound className="h-4 w-4 text-amber-700" aria-hidden="true" />}>
        <p className="mb-3 text-sm text-slate-700">{t('identity_body')}</p>
        <Field label={t('password_label')}>
          <input
            className={inputClass}
            type="password"
            value={password}
            maxLength={256}
            autoComplete="current-password"
            autoFocus
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>
        {error ? (
          <div className="mt-3" role="alert">
            <Pill tone="rose">{error}</Pill>
          </div>
        ) : null}
        <div className="mt-4 flex justify-between gap-2">
          <Btn tone="slate" onClick={onBack}>
            {t('back')}
          </Btn>
          <Btn tone="rose" type="submit" busy={busy} disabled={!password}>
            {t('verify')}
          </Btn>
        </div>
      </Panel>
    </form>
  );
};
