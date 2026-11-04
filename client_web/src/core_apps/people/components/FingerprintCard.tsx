import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Fingerprint, Trash2 } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import {
  FINGERS, Finger, FingerprintState, cancelFingerprintEnroll, fetchFingerprint, forgetFingerprint, setFingerprintEnabled, startFingerprintEnroll,
} from '../data/fingerprintApi';
import { chipClass, fieldClass, usePeopleI18n } from '../scope';

interface Props {
  readonly slug: string;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
}

const REFRESH_MS = 3000;
const cardClass = 'flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4';

export const FingerprintCard: React.FC<Props> = ({ slug, busy, run }) => {
  const { t } = usePeopleI18n();
  const [state, setState] = useState<FingerprintState | null>(null);
  const [tick, setTick] = useState(0);
  const [finger, setFinger] = useState<Finger>('right_index');
  const [reader, setReader] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    fetchFingerprint(slug, controller.signal)
      .then(setState)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_connectors_failed', cause));
    return () => controller.abort();
  }, [slug, tick]);

  useEffect(() => {
    const timer = window.setInterval(() => setTick((v) => v + 1), REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  const act = useCallback(
    async (key: string, task: () => Promise<unknown>) => {
      const ok = await run(key, task, 'people_connectors_failed');
      setTick((v) => v + 1);
      return ok;
    },
    [run],
  );

  const usable = useMemo(() => (state?.readers ?? []).filter((r) => r.online && r.ready), [state]);
  const chosen = usable.find((r) => r.key === reader)?.key ?? usable[0]?.key ?? '';

  if (!state) {
    return null;
  }
  const linked = state.fingers.length > 0;

  return (
    <section className={cardClass} aria-labelledby="connector-fingerprint">
      <header className="flex items-center gap-2">
        <Fingerprint className="h-4 w-4 text-indigo-700" aria-hidden="true" />
        <h3 id="connector-fingerprint" className="font-semibold text-slate-900">
          {t('fp_title')}
        </h3>
        <label className="ml-auto flex items-center gap-2 text-xs font-semibold text-slate-800">
          <input
            type="checkbox"
            checked={state.enabled}
            disabled={busy !== null}
            onChange={(e) => void act('fp-toggle', () => setFingerprintEnabled(slug, e.target.checked))}
            className="h-4 w-4 accent-indigo-600"
          />
          {t(state.enabled ? 'fp_enabled' : 'fp_disabled')}
        </label>
      </header>
      <p className="text-xs text-slate-600">{t('fp_hint')}</p>

      <div className="flex flex-col gap-1">
        <h4 className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">{t('fp_readers')}</h4>
        {state.readers.length === 0 && <p className="text-xs text-slate-600">{t('fp_no_readers')}</p>}
        <ul className="flex flex-col gap-1">
          {state.readers.map((r) => (
            <li key={r.key} className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs">
              <span className="font-semibold text-slate-900">{r.label}</span>
              <span className="text-slate-600">{r.room || t('fp_room_unset')}</span>
              <span className="rounded-full border border-slate-300 px-2 text-slate-700">{t(`fp_transport_${r.transport}`)}</span>
              <span className={`ml-auto ${r.online ? (r.ready ? 'text-emerald-800' : 'text-amber-800') : 'text-slate-500'}`}>
                {t(r.online ? (r.ready ? 'fp_ready' : 'fp_detected') : 'fp_offline')}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex flex-col gap-1">
        <h4 className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">{t('fp_fingers')}</h4>
        {!linked && <p className="text-xs text-slate-600">{t('fp_none')}</p>}
        <ul className="flex flex-wrap gap-2">
          {state.fingers.map((f) => (
            <li key={`${f.finger}:${f.reader}`} className="flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-white px-2.5 py-1 text-xs text-slate-900">
              {t(`fp_finger_${f.finger}`)}
              <button
                type="button"
                aria-label={t('fp_forget')}
                disabled={busy !== null}
                onClick={() => void act(`fp-del:${f.finger}`, () => forgetFingerprint(slug, f.finger))}
                className="text-rose-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-400"
              >
                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      </div>

      {state.pending ? (
        <div role="status" className="flex flex-wrap items-center gap-3 rounded-lg border border-indigo-300 bg-indigo-50 px-3 py-2 text-xs text-indigo-900">
          <Fingerprint className="h-4 w-4 animate-pulse" aria-hidden="true" />
          {t('fp_waiting', { finger: t(`fp_finger_${state.pending.finger}`) })}
          <button type="button" disabled={busy !== null} onClick={() => void act('fp-cancel', () => cancelFingerprintEnroll(slug))} className={`${chipClass} ml-auto border-slate-300 text-slate-800`}>
            {t('fp_cancel')}
          </button>
        </div>
      ) : (
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex min-w-[8rem] flex-1 flex-col gap-1 text-xs font-semibold text-slate-800">
            {t('fp_finger')}
            <select value={finger} onChange={(e) => setFinger(e.target.value as Finger)} className={fieldClass}>
              {FINGERS.map((f) => (
                <option key={f} value={f}>
                  {t(`fp_finger_${f}`)}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[8rem] flex-1 flex-col gap-1 text-xs font-semibold text-slate-800">
            {t('fp_reader')}
            <select value={chosen} onChange={(e) => setReader(e.target.value)} disabled={usable.length === 0} className={fieldClass}>
              {usable.map((r) => (
                <option key={r.key} value={r.key}>
                  {`${r.label} · ${r.room || t('fp_room_unset')}`}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            disabled={busy !== null || !chosen}
            onClick={() => void act('fp-enroll', () => startFingerprintEnroll(slug, finger, chosen))}
            className={`${chipClass} border-indigo-300 px-3 py-2 text-indigo-900`}
          >
            {t('fp_enroll')}
          </button>
          {linked && (
            <button type="button" disabled={busy !== null} onClick={() => void act('fp-forget-all', () => forgetFingerprint(slug))} className={`${chipClass} border-rose-300 px-3 py-2 text-rose-800`}>
              {t('fp_forget_all')}
            </button>
          )}
        </div>
      )}
      {state.last && <p className="text-xs text-slate-600">{t('fp_last', { room: state.last.room || t('fp_room_unset') })}</p>}
    </section>
  );
};
