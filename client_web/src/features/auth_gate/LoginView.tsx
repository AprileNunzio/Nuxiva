import React, { FormEvent, useState } from 'react';
import { Eye, EyeOff, Globe, Loader2, LockKeyhole, Moon, ShieldCheck, Sun, User } from 'lucide-react';
import { reportError } from '../../shared/errors/errorBus';
import { useI18n } from '../../shared/i18n/I18nContext';
import { SupportedLanguage } from '../../shared/i18n/translations';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { useTheme } from '../../shared/theme/ThemeContext';
import { LoginError, LoginFailure, login } from './authApi';
import { availableLanguages, languageName } from '../../shared/i18n/languageRegistry';
import './auth_gate.css';

const LANGUAGES = availableLanguages;

interface LoginViewProps {
  readonly expired: boolean;
  readonly onSignedIn: (user: string) => void;
}

export const LoginView: React.FC<LoginViewProps> = ({ expired, onSignedIn }) => {
  const { t } = useScopedI18n('features/auth_gate');
  const { lang, setLang } = useI18n();
  const { theme, toggleTheme } = useTheme();
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
    <main className="ag-stage">
      <div className="ag-orb" aria-hidden="true" />
      <div className="ag-top-controls">
        <label className="ag-control-pill">
          <Globe size={14} aria-hidden="true" />
          <span className="sr-only">{t('language_label')}</span>
          <select
            value={lang}
            onChange={(event) => {
              const next = event.target.value as SupportedLanguage;
              if (LANGUAGES.includes(next)) {
                setLang(next);
              }
            }}
            className="ag-lang-select"
          >
            {LANGUAGES.map((code) => (
              <option key={code} value={code}>
                {languageName(code)}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="ag-theme-toggle"
          title={theme === 'dark' ? 'Tema Chiaro' : 'Tema Scuro'}
          aria-label={theme === 'dark' ? 'Tema Chiaro' : 'Tema Scuro'}
          onClick={toggleTheme}
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </div>

      <form
        onSubmit={submit}
        className="ag-panel"
        aria-describedby={failure ? 'ag-error' : undefined}
      >
        <div className="ag-brand-header">
          <span className="ag-emblem">
            <ShieldCheck size={28} aria-hidden="true" />
          </span>
          <h1 className="ag-title">{t('brand')}</h1>
          <p className="ag-subtitle">{t(expired ? 'subtitle_expired' : 'subtitle')}</p>
        </div>

        <div className="ag-form-fields">
          <label className="ag-field-wrap">
            <span className="sr-only">{t('username')}</span>
            <User className="ag-field-icon" aria-hidden="true" />
            <input
              className="ag-input"
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

          <label className="ag-field-wrap">
            <span className="sr-only">{t('password')}</span>
            <LockKeyhole className="ag-field-icon" aria-hidden="true" />
            <input
              className="ag-input"
              style={{ paddingRight: '2.8rem' }}
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
              className="ag-reveal-btn"
            >
              {reveal ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
            </button>
          </label>
        </div>

        {failure && (
          <p id="ag-error" role="alert" className="ag-error-alert">
            {t(`error_${failure}`)}
          </p>
        )}

        <button
          type="submit"
          disabled={pending}
          className="ag-submit-btn"
        >
          {pending && <Loader2 size={16} className="network-spinning" aria-hidden="true" />}
          {t('submit')}
        </button>
        <p className="ag-hint">{t('hint_admin')}</p>
      </form>
    </main>
  );
};
