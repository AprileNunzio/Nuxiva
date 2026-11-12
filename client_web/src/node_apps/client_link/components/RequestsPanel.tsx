import React from 'react';
import { Check, Loader2, Radio, X } from 'lucide-react';
import { Panel } from '../../shared/components/ModuleFrame';
import { approveRequest, rejectRequest } from '../data/linkApi';
import { LinksHandle, useNow } from '../hooks/useLinks';
import { relativeTime, useLinkI18n } from '../scope';

export const RequestsPanel: React.FC<{ readonly handle: LinksHandle }> = ({ handle }) => {
  const { t, lang } = useLinkI18n();
  const now = useNow(5000);
  const pending = handle.overview?.pending ?? [];
  const found = handle.overview?.found ?? [];
  if (pending.length === 0 && found.length === 0) {
    return null;
  }
  return (
    <Panel title={t('requests_title', { count: pending.length })}>
      <ul className="flex flex-col gap-2">
        {pending.map((request) => (
          <li key={request.id} className="rounded-xl border border-amber-400/40 bg-amber-400/5 p-3">
            <p className="truncate text-sm font-semibold text-slate-100">{request.name}</p>
            <p className="truncate text-[11px] text-slate-400">
              {[t(`type_${request.type}`), request.room, request.ip].filter(Boolean).join(' · ')}
            </p>
            <p className="mt-1 text-[11px] text-slate-400">
              {t('request_fingerprint')} <span className="font-mono text-amber-100">{request.fingerprint}</span>
            </p>
            <div className="mt-2 flex gap-2">
              <button
                type="button"
                disabled={handle.busy !== null}
                onClick={() => void handle.run(`approve:${request.id}`, () => approveRequest(request.id), 'node_request_approve_failed')}
                className="flex items-center gap-1.5 rounded-lg bg-emerald-400 px-3 py-1.5 text-xs font-bold text-slate-950 transition hover:bg-emerald-300 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-100"
              >
                {handle.busy === `approve:${request.id}` ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Check className="h-3.5 w-3.5" aria-hidden="true" />}
                {t('request_approve')}
              </button>
              <button
                type="button"
                disabled={handle.busy !== null}
                onClick={() => void handle.run(`reject:${request.id}`, () => rejectRequest(request.id), 'node_request_reject_failed')}
                className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200 transition hover:border-rose-400/60 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-300"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
                {t('request_reject')}
              </button>
            </div>
          </li>
        ))}
      </ul>
      {found.length > 0 && (
        <div className={pending.length ? 'mt-4 border-t border-slate-800/80 pt-3' : ''}>
          <p className="mb-2 text-xs font-semibold text-slate-300">{t('found_title')}</p>
          <ul className="flex flex-col gap-1.5">
            {found.map((beacon) => (
              <li key={beacon.id} className="flex items-center gap-2 rounded-lg border border-slate-800/80 bg-slate-950/40 px-3 py-2 text-sm">
                <Radio className="h-3.5 w-3.5 shrink-0 animate-pulse text-cyan-300" aria-hidden="true" />
                <span className="min-w-0 flex-1 truncate font-mono text-slate-200">{beacon.id}</span>
                <span className="shrink-0 text-[11px] text-slate-500">
                  {[beacon.ip, beacon.version, relativeTime(beacon.at, now, lang)].filter(Boolean).join(' · ')}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[11px] text-slate-500">{t('found_hint')}</p>
        </div>
      )}
    </Panel>
  );
};
