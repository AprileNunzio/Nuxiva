import React from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { ReportedError } from '../errorBus';
import { errorTitle } from '../errorTitle';
import { buildReport, serializeReports } from '../diagnosis/report';
import { CopyDetailsButton } from './CopyDetailsButton';
import { ErrorDetails } from './ErrorDetails';

type Translate = (key: string, params?: Record<string, string | number>) => string;

interface Props {
  readonly entry: ReportedError;
  readonly t: Translate;
  readonly lang: string;
  readonly onDismiss: (id: number) => void;
}

export const ErrorToast: React.FC<Props> = ({ entry, t, lang, onDismiss }) => {
  const critical = entry.severity === 'critical';
  const report = () => serializeReports([buildReport(entry.code, entry.occurredAt, entry.diagnosis, window.location.pathname)]);
  return (
    <div
      role="alert"
      className={`pointer-events-auto flex w-full max-w-md items-start gap-3 rounded-xl border bg-slate-950/95 p-3 text-sm shadow-xl backdrop-blur-xl ${
        critical ? 'border-rose-500/50 text-rose-100' : 'border-amber-400/40 text-amber-50'
      }`}
    >
      <AlertTriangle className={`mt-0.5 h-4 w-4 shrink-0 ${critical ? 'text-rose-400' : 'text-amber-300'}`} aria-hidden="true" />
      <div className="min-w-0 flex-1 leading-snug">
        <p className="font-medium">{errorTitle(t, entry.code)}</p>
        <ErrorDetails t={t} code={entry.code} occurredAt={entry.occurredAt} diagnosis={entry.diagnosis} lang={lang} />
        <div className="mt-2">
          <CopyDetailsButton payload={report} label={t('copy_details')} doneLabel={t('copied')} />
        </div>
      </div>
      <button
        type="button"
        onClick={() => onDismiss(entry.id)}
        aria-label={t('dismiss')}
        className="rounded-md p-1 text-slate-400 transition hover:bg-slate-800 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
      >
        <X className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  );
};
