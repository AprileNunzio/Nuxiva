import React from 'react';
import { ArrowLeft, Atom, Network } from 'lucide-react';
import { useScopedI18n } from '../shared/i18n/useScopedI18n';
import { CoreAppTitle } from './CoreAppTitle';
import { resolveCoreApp } from './coreAppRegistry';
import { SHELL_SCOPE } from './shellScope';

interface AppViewFrameProps {
  readonly appId: string;
  readonly onBackToCore: () => void;
  readonly onBackToMesh: () => void;
}

const navButton =
  'flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-1.5 text-xs text-slate-300 transition hover:border-cyan-500/60 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400';

export const AppViewFrame: React.FC<AppViewFrameProps> = ({ appId, onBackToCore, onBackToMesh }) => {
  const { t } = useScopedI18n(SHELL_SCOPE);
  const AppComponent = resolveCoreApp(appId);
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 bg-slate-950/80 px-3 py-2.5 sm:px-6">
        <div className="flex items-center gap-2">
          <button type="button" onClick={onBackToCore} className={navButton}>
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            <span>{t('back_to_core')}</span>
          </button>
          <button type="button" onClick={onBackToMesh} className={navButton}>
            <Network className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
            <span className="hidden sm:inline">{t('back_to_mesh')}</span>
          </button>
        </div>
        <h1 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cyan-300">
          <Atom className="h-4 w-4" aria-hidden="true" />
          <CoreAppTitle appId={appId} />
        </h1>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {AppComponent ? <AppComponent /> : <p className="p-8 text-center text-sm text-slate-500">{t('app_unavailable')}</p>}
      </div>
    </div>
  );
};
