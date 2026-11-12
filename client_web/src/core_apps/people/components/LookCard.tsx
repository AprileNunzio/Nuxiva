import React, { useCallback, useEffect, useState } from 'react';
import { Check, Glasses, ShieldCheck, X } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { LookDetails, LookEvent, fetchLook, judgeLook } from '../data/lookApi';
import { usePeopleI18n } from '../scope';

interface LookCardProps {
  readonly slug: string;
  readonly tick: number;
}

const chip = 'rounded-full bg-secondary-container px-2.5 py-0.5 text-[11px] font-semibold text-on-secondary-container';

export const LookCard: React.FC<LookCardProps> = ({ slug, tick }) => {
  const { t } = usePeopleI18n();
  const [look, setLook] = useState<LookDetails | null>(null);
  const [round, setRound] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchLook(slug, controller.signal)
      .then(setLook)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_look_failed', cause));
    return () => controller.abort();
  }, [slug, tick, round]);

  const judge = useCallback(
    (event: LookEvent, verdict: 'ok' | 'wrong') => {
      setBusy(event.id);
      judgeLook(slug, event.id, verdict)
        .then(() => setRound((r) => r + 1))
        .catch((cause: unknown) => reportError('people_look_feedback_failed', cause))
        .finally(() => setBusy(null));
    },
    [slug],
  );

  if (!look?.available) {
    return null;
  }
  const s = look.summary;
  const traits = s
    ? [
        s.glasses && t('look_glasses'),
        s.beard && t('look_beard'),
        s.fringe && t('look_fringe'),
        s.hair && t('look_hair', { color: t(`hair_${s.hair}`) }),
        s.smoker && t('look_smoker', { count: s.smokingEpisodes }),
      ].filter((v): v is string => typeof v === 'string')
    : [];
  const describe = (e: LookEvent): string => {
    if (e.kind === 'hair_color') {
      const to = t(`hair_${e.value}`);
      return e.previous ? t('look_event_hair_change', { from: t(`hair_${e.previous}`), to }) : t('look_event_hair', { color: to });
    }
    if (e.kind === 'smoking' || e.kind === 'smoker') {
      return t(`look_event_${e.kind}`);
    }
    return t(`look_event_${e.kind}_${e.value === 'on' ? 'on' : 'off'}`);
  };

  return (
    <section className="md-enter rounded-2xl p-3 text-on-surface" aria-label={t('look_title')}>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs">
        <span className="flex items-center gap-1.5 font-semibold">
          <Glasses className="h-4 w-4 text-primary" aria-hidden="true" />
          {t('look_title')}
        </span>
        <span className="flex items-center gap-1 text-on-surface-variant">
          <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
          {look.consent ? t('look_private') : t('look_no_consent')}
        </span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {traits.length === 0 ? (
          <span className="text-xs text-on-surface-variant">{t('look_none', { count: s?.observations ?? 0 })}</span>
        ) : (
          traits.map((label) => (
            <span key={label} className={chip}>
              {label}
            </span>
          ))
        )}
      </div>
      {look.events.length > 0 && (
        <ul className="mt-2 space-y-1">
          {look.events.slice(0, 8).map((e) => (
            <li key={e.id} className="flex flex-wrap items-center gap-2 text-xs">
              <span className="font-mono text-on-surface-variant">{new Date(e.at * 1000).toLocaleString()}</span>
              <span className={e.status === 'rejected' ? 'text-on-surface-variant line-through' : ''}>{describe(e)}</span>
              {e.status === 'auto' ? (
                <span className="flex gap-1">
                  <button type="button" disabled={busy === e.id} onClick={() => judge(e, 'ok')} aria-label={t('look_confirm')}
                    className="rounded-full p-1 text-primary hover:bg-primary/10 disabled:opacity-40">
                    <Check className="h-3.5 w-3.5" aria-hidden="true" />
                  </button>
                  <button type="button" disabled={busy === e.id} onClick={() => judge(e, 'wrong')} aria-label={t('look_wrong')}
                    className="rounded-full p-1 text-error hover:bg-error/10 disabled:opacity-40">
                    <X className="h-3.5 w-3.5" aria-hidden="true" />
                  </button>
                </span>
              ) : (
                <span className="text-on-surface-variant">{t(`look_status_${e.status}`)}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};
