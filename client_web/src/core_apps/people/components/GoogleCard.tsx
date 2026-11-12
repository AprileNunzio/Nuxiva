import React, { useState } from 'react';
import { AlertTriangle, ExternalLink, Mail, Unlink } from 'lucide-react';
import { GoogleState, googleAuthUrl, googleCancel, googleFinish, googleUnlink } from '../data/connectorsApi';
import { chipClass, fieldClass, usePeopleI18n } from '../scope';
import { GoogleReminder } from './GoogleReminder';
import { GoogleServices } from './GoogleServices';
import { SetupLink } from './SetupLink';
import { dropWindow, reserveWindow, sendWindow } from './googleWindow';

interface Props {
  readonly slug: string;
  readonly state: GoogleState;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
}

export const GoogleCard: React.FC<Props> = ({ slug, state, busy, run }) => {
  const { t } = usePeopleI18n();
  const [pasted, setPasted] = useState('');
  const [manual, setManual] = useState('');

  const authorize = async (load: () => Promise<string>, key: string) => {
    const win = reserveWindow();
    let url = '';
    const ok = await run(key, async () => {
      url = await load();
    }, 'people_connectors_failed');
    if (!ok || !url) {
      dropWindow(win);
      return;
    }
    setManual(sendWindow(win, url) ? '' : url);
  };

  const finish = async () => {
    if (await run('gg-finish', () => googleFinish(slug, pasted.trim()), 'people_connectors_failed')) {
      setPasted('');
    }
  };

  return (
    <section className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4" aria-labelledby="connector-google">
      <header className="flex items-center gap-2">
        <Mail className="h-4 w-4 text-rose-700" aria-hidden="true" />
        <h3 id="connector-google" className="font-semibold text-slate-900">
          Google
        </h3>
        <span className={`ml-auto rounded-full border px-2 py-0.5 text-xs ${state.linked ? 'border-emerald-300 text-emerald-800' : 'border-slate-300 text-slate-600'}`}>
          {t(state.linked ? 'connector_linked' : 'connector_not_linked')}
        </span>
      </header>
      {!state.available && <SetupLink feature="google" hint={t('gg_not_configured')} />}
      {state.revoked && (
        <p className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900" role="alert">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          {t('gg_revoked')}
        </p>
      )}
      {manual && (
        <a href={manual} target="_blank" rel="noopener noreferrer" onClick={() => setManual('')} className={`${chipClass} self-start border-blue-300 bg-blue-600 px-3 py-2 text-white`}>
          <ExternalLink className="h-4 w-4" aria-hidden="true" />
          {t('gg_open_google')}
        </a>
      )}
      {state.linked && (
        <p className="text-sm text-slate-800">
          {t('gg_linked_as', { email: state.email || '—' })}
        </p>
      )}
      {state.services.length > 0 && <GoogleServices slug={slug} services={state.services} linked={state.linked} available={state.available} busy={busy} run={run} onAuth={authorize} />}
      {state.linked && <GoogleReminder slug={slug} minutes={state.remindMin} busy={busy} run={run} />}
      {state.pending && (
        <div className="flex flex-col gap-2">
          <p className="text-xs text-slate-600">{t('gg_paste_hint')}</p>
          <div className="flex gap-2">
            <input value={pasted} maxLength={4000} onChange={(event) => setPasted(event.target.value)} placeholder={t('gg_paste')} aria-label={t('gg_paste')} className={`${fieldClass} min-w-0 flex-1`} />
            <button type="button" disabled={busy !== null || pasted.trim().length < 10} onClick={() => void finish()} className={`${chipClass} border-blue-300 bg-blue-50 px-3 text-blue-900`}>
              {t('gg_finish')}
            </button>
          </div>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={busy !== null || !state.available} onClick={() => void authorize(() => googleAuthUrl(slug), 'gg-url')} className={`${chipClass} border-blue-300 bg-blue-50 px-3 text-blue-900`}>
          <ExternalLink className="h-4 w-4" aria-hidden="true" />
          {t(state.linked ? 'gg_relink' : 'gg_link')}
        </button>
        {state.pending && (
          <button type="button" disabled={busy !== null} onClick={() => void run('gg-cancel', () => googleCancel(slug), 'people_connectors_failed')} className={`${chipClass} border-slate-300 px-3 text-slate-800`}>
            {t('cancel')}
          </button>
        )}
        {state.linked && (
          <button type="button" disabled={busy !== null} onClick={() => void run('gg-unlink', () => googleUnlink(slug), 'people_connectors_failed')} className={`${chipClass} border-rose-300 px-3 text-rose-800`}>
            <Unlink className="h-4 w-4" aria-hidden="true" />
            {t('connector_unlink')}
          </button>
        )}
      </div>
    </section>
  );
};
