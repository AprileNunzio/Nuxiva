import React, { useState } from 'react';
import { Check, Loader2, Radio, X } from 'lucide-react';
import { Panel } from '../../shared/components/ModuleFrame';
import { approveRequest, rejectRequest } from '../data/linkApi';
import { NodeProfile, PROFILES } from '../data/trustApi';
import { LinksHandle, useNow } from '../hooks/useLinks';
import { relativeTime, useLinkI18n } from '../scope';

export const RequestsPanel: React.FC<{ readonly handle: LinksHandle }> = ({ handle }) => {
  const { t, lang } = useLinkI18n();
  const now = useNow(5000);
  const [choice, setChoice] = useState<Readonly<Record<string, NodeProfile>>>({});
  const pending = handle.overview?.pending ?? [];
  const found = handle.overview?.found ?? [];
  if (pending.length === 0 && found.length === 0) {
    return null;
  }
  return (
    <Panel flat title={t('requests_title', { count: pending.length })}>
      <ul className="flex flex-col gap-2">
        {pending.map((request) => (
          <li key={request.id} className="rounded-2xl bg-warning-container px-3 py-3 text-on-warning-container">
            <p className="truncate text-sm font-semibold text-on-surface">{request.name}</p>
            <p className="truncate text-[11px] text-on-surface-variant">
              {[t(`type_${request.type}`), request.room, request.ip].filter(Boolean).join(' · ')}
            </p>
            <p className="mt-1 text-[11px] text-on-surface-variant">
              {t('request_fingerprint')} <span className="font-mono text-on-surface">{request.fingerprint}</span>
            </p>
            <label className="mt-2 block text-[11px] text-on-surface-variant">
              {t('request_profile')}
              <select
                value={request.signed ? (choice[request.id] ?? 'satellite') : 'satellite'}
                disabled={!request.signed}
                onChange={(event) => setChoice({ ...choice, [request.id]: PROFILES.find((p) => p === event.target.value) ?? 'satellite' })}
                className="mt-1 block w-full rounded-xl bg-surface-container-high px-2 py-1.5 text-xs text-on-surface focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                {PROFILES.map((profile) => (
                  <option key={profile} value={profile}>
                    {t(`profile_${profile}`)}
                  </option>
                ))}
              </select>
            </label>
            <p className="mt-1 text-[11px] text-on-surface-variant">
              {request.signed ? t(`profile_${choice[request.id] ?? 'satellite'}_hint`) : t('request_legacy')}
            </p>
            <div className="mt-2 flex gap-2">
              <button
                type="button"
                disabled={handle.busy !== null}
                onClick={() => void handle.run(`approve:${request.id}`, () => approveRequest(request.id, request.signed ? (choice[request.id] ?? 'satellite') : 'satellite'), 'node_request_approve_failed')}
                className="md-state flex min-h-9 items-center gap-1.5 rounded-full bg-success-container px-3.5 py-1.5 text-xs font-semibold text-on-success-container disabled:opacity-50"
              >
                {handle.busy === `approve:${request.id}` ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Check className="h-3.5 w-3.5" aria-hidden="true" />}
                {t('request_approve')}
              </button>
              <button
                type="button"
                disabled={handle.busy !== null}
                onClick={() => void handle.run(`reject:${request.id}`, () => rejectRequest(request.id), 'node_request_reject_failed')}
                className="md-state flex min-h-9 items-center gap-1.5 rounded-full bg-error-container px-3.5 py-1.5 text-xs font-semibold text-on-error-container disabled:opacity-50"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
                {t('request_reject')}
              </button>
            </div>
          </li>
        ))}
      </ul>
      {found.length > 0 && (
        <div className={pending.length ? 'mt-4 pt-3' : ''}>
          <p className="mb-2 text-xs font-semibold text-on-surface">{t('found_title')}</p>
          <ul className="flex flex-col gap-1.5">
            {found.map((beacon) => (
              <li key={beacon.id} className="flex items-center gap-2 rounded-2xl bg-surface-container px-3 py-2 text-sm">
                <Radio className="h-3.5 w-3.5 shrink-0 animate-pulse text-primary" aria-hidden="true" />
                <span className="min-w-0 flex-1 truncate font-mono text-on-surface">{beacon.id}</span>
                <span className="shrink-0 text-[11px] text-on-surface-variant">
                  {[beacon.ip, beacon.version, relativeTime(beacon.at, now, lang)].filter(Boolean).join(' · ')}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[11px] text-on-surface-variant">{t('found_hint')}</p>
        </div>
      )}
    </Panel>
  );
};
