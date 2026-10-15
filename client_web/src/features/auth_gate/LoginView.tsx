import React, { FormEvent, useState } from 'react';
import { Eye, EyeOff, Globe, Loader2, LockKeyhole, ShieldCheck, User } from 'lucide-react';
import { reportError } from '../../shared/errors/errorBus';
import { useI18n } from '../../shared/i18n/I18nContext';
import { SupportedLanguage } from '../../shared/i18n/translations';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { LoginError, LoginFailure, login } from './authApi';
import './auth_gate.css';

const LANGUAGES: readonly SupportedLanguage[] = ['it', 'en', 'fr', 'es'];

interface LoginViewProps {
  readonly expired: boolean;
  readonly onSignedIn: (user: string) => void;
}

const field =
  'w-full rounded-xl border border-slate-700/80 bg-slate-950/70 py-3 pl-10 pr-3 text-sm text-white placeholder-slate-500 transition focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/30';

export const LoginView: React.FC<LoginViewProps> = ({ expired, onSignedIn }) => {
  const { t } = useScopedI18n('features/auth_gate');
  const { lang, setLang } = useI18n();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [reveal, setReveal] = useState(false);
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState<LoginFailure | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setPending(true);
    setFailure(null);
    try {
      onSignedIn(await login(username.trim(), password));
    } catch (cause) {
      const reason = cause instanceof LoginError ? cause.reason : 'unreachable';
      if (reason === 'unreachable' || reason === 'rejected') {
        reportError('login_failed', cause);
      }
      setFailure(reason);
      setPassword('');
    } finally {
      setPending(false);
    }
  };

  return (
    <main className="ag-stage relative flex min-h-[100dvh] items-center justify-center overflow-hidden px-4 py-10">
      <div className="ag-orb pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2" aria-hidden="true" />
      <label className="absolute right-4 top-4 flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/70 px-2.5 py-1.5">
        <Globe className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
        <span className="sr-only">{t('language_label')}</span>
        <select
          value={lang}
          onChange={(event) => {
            const next = event.target.value as SupportedLanguage;
            if (LANGUAGES.includes(next)) {
              setLang(next);
            }
          }}
          className="cursor-pointer bg-transparent font-mono text-xs font-bold uppercase text-slate-200 focus:outline-none"
        >
          {LANGUAGES.map((code) => (
            <option key={code} value={code} className="bg-slate-900">
              {code.toUpperCase()}
            </option>
          ))}
        </select>
      </label>

      <form
        onSubmit={submit}
        className="ag-panel relative z-10 w-full max-w-sm rounded-3xl border border-cyan-400/25 p-6 shadow-[0_0_80px_rgba(34,211,238,0.15)] sm:p-8"
        aria-describedby={failure ? 'ag-error' : undefined}
      >
        <div className="mb-6 flex flex-col items-center text-center">
          <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-cyan-300/40 bg-cyan-400/10 shadow-[0_0_30px_rgba(34,211,238,0.35)]">
            <ShieldCheck className="h-7 w-7 text-cyan-200" aria-hidden="true" />
          </span>
          <h1 className="font-['Rajdhani'] text-3xl font-bold uppercase tracking-[0.3em] text-white">{t('brand')}</h1>
          <p className="mt-1 text-sm text-slate-400">{t(expired ? 'subtitle_expired' : 'subtitle')}</p>
        </div>

        <div className="flex flex-col gap-3">
          <label className="relative block">
            <span className="sr-only">{t('username')}</span>
            <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
            <input
              className={field}
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder={t('username')}
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              maxLength={32}
              required
            />
          </label>
          <label className="relative block">
            <span className="sr-only">{t('password')}</span>
            <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
            <input
              className={`${field} pr-11`}
              type={reveal ? 'text' : 'password'}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={t('password')}
              autoComplete="current-password"
              maxLength={1024}
              required
            />
            <button
              type="button"
              onClick={() => setReveal((value) => !value)}
              aria-label={t(reveal ? 'hide_password' : 'show_password')}
              aria-pressed={reveal}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-slate-400 transition hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            >
              {reveal ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
            </button>
          </label>
        </div>

        {failure && (
          <p id="ag-error" role="alert" className="mt-4 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
            {t(`error_${failure}`)}
          </p>
        )}

        <button
          type="submit"
          disabled={pending}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 py-3 text-sm font-bold text-slate-950 shadow-[0_0_30px_rgba(34,211,238,0.35)] transition hover:brightness-110 disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200"
        >
          {pending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
          {t('submit')}
        </button>
        <p className="mt-4 text-center text-[11px] leading-relaxed text-slate-500">{t('hint_admin')}</p>
      </form>
    </main>
  );
};
