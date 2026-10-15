import React from 'react';
import { Atom, ChevronRight, Globe, LogOut, Network, Radio } from 'lucide-react';
import { useAuthenticatedSession } from '../../features/auth_gate';
import { reportError } from '../../shared/errors/errorBus';
import { useI18n } from '../../shared/i18n/I18nContext';
import { SupportedLanguage } from '../../shared/i18n/translations';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { CoreAppTitle } from '../CoreAppTitle';
import { SHELL_SCOPE } from '../shellScope';
import { ShellRoute } from '../shellRoute';

const LANGUAGES: readonly SupportedLanguage[] = ['it', 'en', 'fr', 'es'];

interface ShellNavbarProps {
  readonly route: ShellRoute;
  readonly onNavigateMesh: () => void;
  readonly onNavigateCore: () => void;
}

const crumb = 'flex items-center gap-1.5 rounded-md px-1.5 py-0.5 transition hover:text-cyan-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400';

export const ShellNavbar: React.FC<ShellNavbarProps> = ({ route, onNavigateMesh, onNavigateCore }) => {
  const { t } = useScopedI18n(SHELL_SCOPE);
  const { lang, setLang } = useI18n();
  const { user, signOut } = useAuthenticatedSession();
  const handleSignOut = () => {
    signOut().catch((cause: unknown) => reportError('logout_failed', cause));
  };
  const inCore = route.view === 'core' || route.view === 'app';

  return (
    <header className="sticky top-0 z-50 w-full border-b border-cyan-500/15 bg-[#02040a]/90 px-3 py-2 backdrop-blur-xl sm:px-6">
      <div className="flex w-full items-center justify-between gap-3">
        <button
          type="button"
          onClick={onNavigateMesh}
          aria-label={t('home_aria')}
          className="group flex items-center gap-3 rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          <span className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-cyan-400/50 bg-cyan-950/40 text-cyan-300 shadow-[0_0_18px_rgba(34,211,238,0.3)] transition group-hover:scale-105">
            <Radio className="h-4 w-4" aria-hidden="true" />
          </span>
          <span className="flex flex-col items-start leading-tight">
            <span className="bg-gradient-to-r from-cyan-300 via-sky-300 to-indigo-300 bg-clip-text font-['Rajdhani'] text-lg font-bold tracking-[0.3em] text-transparent sm:text-xl">
              {t('brand_name')}
            </span>
            <span className="hidden font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500 sm:block">{t('brand_tagline')}</span>
          </span>
        </button>

        <nav aria-label={t('breadcrumb_aria')} className="hidden min-w-0 items-center gap-1 rounded-xl border border-slate-800 bg-slate-900/60 px-2 py-1 font-mono text-xs md:flex">
          <button type="button" onClick={onNavigateMesh} className={`${crumb} ${route.view === 'mesh' ? 'font-bold text-cyan-300' : 'text-slate-400'}`}>
            <Network className="h-3.5 w-3.5" aria-hidden="true" />
            {t('crumb_mesh')}
          </button>
          {inCore && (
            <>
              <ChevronRight className="h-3.5 w-3.5 text-slate-600" aria-hidden="true" />
              <button type="button" onClick={onNavigateCore} className={`${crumb} ${route.view === 'core' ? 'font-bold text-cyan-300' : 'text-slate-400'}`}>
                <Atom className="h-3.5 w-3.5" aria-hidden="true" />
                {t('crumb_core')}
              </button>
            </>
          )}
          {route.view === 'app' && (
            <>
              <ChevronRight className="h-3.5 w-3.5 text-slate-600" aria-hidden="true" />
              <span className="truncate px-1.5 font-bold text-cyan-200" aria-current="page">
                <CoreAppTitle appId={route.appId} />
              </span>
            </>
          )}
          {route.view === 'node' && (
            <>
              <ChevronRight className="h-3.5 w-3.5 text-slate-600" aria-hidden="true" />
              <span className="flex items-center gap-1.5 truncate px-1.5 font-bold text-emerald-300" aria-current="page">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" aria-hidden="true" />
                {route.node.name}
              </span>
            </>
          )}
        </nav>

        <div className="flex items-center gap-2">
          {route.view !== 'mesh' && (
            <button
              type="button"
              onClick={onNavigateMesh}
              className="flex items-center gap-1.5 rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-3 py-1.5 text-xs font-bold text-cyan-200 transition hover:bg-cyan-500/20 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            >
              <Network className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="hidden sm:inline">{t('back_to_mesh')}</span>
            </button>
          )}
          <button
            type="button"
            onClick={handleSignOut}
            title={t('signed_in_as', { user })}
            aria-label={`${t('logout')} · ${t('signed_in_as', { user })}`}
            className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/70 px-2.5 py-1.5 text-xs text-slate-300 transition hover:border-rose-400/50 hover:text-rose-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-300"
          >
            <span className="hidden max-w-[8rem] truncate font-mono lg:inline">{user}</span>
            <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
          <label className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/70 px-2.5 py-1.5">
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
                  {t(`language_${code}`)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
    </header>
  );
};
