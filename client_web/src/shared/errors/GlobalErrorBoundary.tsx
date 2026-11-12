import React from 'react';
import { AlertOctagon, RotateCcw } from 'lucide-react';
import { reportError } from './errorBus';
import { useScopedI18n } from '../i18n/useScopedI18n';

interface BoundaryState {
  readonly failed: boolean;
}

const FallbackScreen: React.FC = () => {
  const { t } = useScopedI18n('shared/errors');
  return (
    <div role="alert" className="min-h-screen flex items-center justify-center bg-[#02040a] p-6">
      <div className="max-w-md w-full rounded-2xl border border-rose-500/40 bg-slate-950/90 p-6 text-center shadow-[0_0_40px_rgba(244,63,94,0.2)]">
        <AlertOctagon className="mx-auto mb-4 h-10 w-10 text-rose-400" aria-hidden="true" />
        <h1 className="font-['Rajdhani'] text-2xl font-bold tracking-wide text-white">{t('fallback_title')}</h1>
        <p className="mt-2 text-sm text-slate-400">{t('fallback_body')}</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-rose-500/90 px-5 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-rose-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-300"
        >
          <RotateCcw className="h-4 w-4" aria-hidden="true" />
          {t('fallback_reload')}
        </button>
      </div>
    </div>
  );
};

export class GlobalErrorBoundary extends React.Component<{ children: React.ReactNode }, BoundaryState> {
  state: BoundaryState = { failed: false };

  static getDerivedStateFromError(): BoundaryState {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    reportError('render_failure', { error, componentStack: info.componentStack }, 'critical');
  }

  render(): React.ReactNode {
    return this.state.failed ? <FallbackScreen /> : this.props.children;
  }
}
