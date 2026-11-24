import React, { useEffect, useState, useSyncExternalStore } from 'react';
import { CheckCircle2, RefreshCw, WifiOff, X } from 'lucide-react';
import { connectivity } from '../connectivity/connectivity';
import { ConnectivitySnapshot } from '../connectivity/monitor';
import { buildReport, requestLabel, serializeReports } from '../diagnosis/report';
import { errorTitle } from '../errorTitle';
import { CopyDetailsButton } from './CopyDetailsButton';

type Translate = (key: string, params?: Record<string, string | number>) => string;

interface Props {
  readonly t: Translate;
  readonly lang: string;
}

const TICK_MS = 1000;

function useNow(active: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return undefined;
    const id = window.setInterval(() => setNow(Date.now()), TICK_MS);
    return () => window.clearInterval(id);
  }, [active]);
  return now;
}

const reportOf = (snap: ConnectivitySnapshot): string =>
  serializeReports(snap.calls.map((call) => buildReport(call.code, call.lastAt, call.diagnosis, window.location.pathname)));

function statusLine(t: Translate, snap: ConnectivitySnapshot, now: number): string {
  if (snap.probing) return t('connectivity_checking');
  const seconds = snap.nextProbeAt === null ? 0 : Math.max(0, Math.ceil((snap.nextProbeAt - now) / 1000));
  return t('connectivity_retry_in', { attempt: snap.attempts + 1, seconds });
}

export const ConnectivityToast: React.FC<Props> = ({ t, lang }) => {
  const snap = useSyncExternalStore(connectivity.subscribe, connectivity.getSnapshot, connectivity.getSnapshot);
  const now = useNow(snap.status === 'down');
  if (snap.status === 'online' || snap.hidden || snap.since === null) return null;
  const restored = snap.status === 'restored';
  const since = new Date(snap.since).toLocaleTimeString(lang);
  const title = restored ? 'connectivity_restored_title' : snap.offline ? 'connectivity_offline_title' : 'connectivity_down_title';
  const body = restored
    ? t('connectivity_restored_body', { seconds: Math.max(1, Math.round(((snap.restoredAt ?? now) - snap.since) / 1000)) })
    : t(snap.offline ? 'connectivity_offline_body' : 'connectivity_down_body', { time: since });
  return (
    <div
      role={restored ? 'status' : 'alert'}
      className={`pointer-events-auto flex w-full max-w-md items-start gap-3 rounded-xl border bg-slate-950/95 p-3 text-sm shadow-xl backdrop-blur-xl ${
        restored ? 'border-emerald-400/40 text-emerald-50' : 'border-amber-400/40 text-amber-50'
      }`}
    >
      {restored ? (
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" aria-hidden="true" />
      ) : (
        <WifiOff className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" aria-hidden="true" />
      )}
      <div className="min-w-0 flex-1 space-y-2 leading-snug">
        <p className="font-medium">{t(title)}</p>
        <p className="text-xs opacity-95">{body}</p>
        {!restored && (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-slate-300" aria-live="polite">{statusLine(t, snap, now)}</span>
            <button
              type="button"
              onClick={() => connectivity.retryNow()}
              disabled={snap.probing}
              className="inline-flex items-center gap-1 rounded-md border border-amber-400/50 px-2 py-1 text-amber-100 transition hover:bg-amber-500/10 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            >
              <RefreshCw className={`h-3 w-3 ${snap.probing ? 'animate-spin' : ''}`} aria-hidden="true" />
              {t('connectivity_retry_now')}
            </button>
          </div>
        )}
        {!restored && snap.lastProbe && <p className="break-words font-mono text-[11px] text-slate-400">{t('connectivity_last_probe', { detail: snap.lastProbe })}</p>}
        {restored && snap.lastProbe && <p className="text-[11px] text-slate-400">{t('connectivity_server_phase', { phase: snap.lastProbe })}</p>}
        <details className="text-[11px] text-slate-300">
          <summary className="cursor-pointer select-none">{t('connectivity_failed_calls', { count: snap.calls.length })}</summary>
          <ul className="mt-1 space-y-1">
            {snap.calls.map((call) => (
              <li key={`${call.code}|${requestLabel(call.diagnosis) ?? ''}`} className="min-w-0 break-words">
                <span className="text-slate-200">{errorTitle(t, call.code)}</span>
                <span className="block font-mono text-slate-400">
                  {requestLabel(call.diagnosis) ?? call.code} · ×{call.count} · {call.diagnosis.raw}
                </span>
              </li>
            ))}
          </ul>
        </details>
        <CopyDetailsButton payload={() => reportOf(snap)} label={t('copy_details')} doneLabel={t('copied')} />
      </div>
      {!restored && (
        <button
          type="button"
          onClick={() => connectivity.hide()}
          aria-label={t('dismiss')}
          className="rounded-md p-1 text-slate-400 transition hover:bg-slate-800 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      )}
    </div>
  );
};
