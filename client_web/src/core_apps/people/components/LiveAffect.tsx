import React from 'react';
import { Activity } from 'lucide-react';
import { AREAS, Area, LiveAffect as Live } from '../data/wellbeingApi';
import { usePeopleI18n } from '../scope';

const TONE: Readonly<Record<Area, string>> = {
  tension: 'border-rose-300 bg-rose-50 text-rose-900',
  exhaustion: 'border-indigo-300 bg-indigo-50 text-indigo-900',
  receptive: 'border-sky-300 bg-sky-50 text-sky-900',
  relief: 'border-emerald-300 bg-emerald-50 text-emerald-900',
};
const BAR: Readonly<Record<Area, string>> = { tension: 'bg-rose-500', exhaustion: 'bg-indigo-500', receptive: 'bg-sky-500', relief: 'bg-emerald-500' };

interface Props {
  readonly live: Live | null;
}

const percent = (value: number): number => Math.max(0, Math.min(100, Math.round(value * 100)));

export const LiveAffect: React.FC<Props> = ({ live }) => {
  const { t } = usePeopleI18n();
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4" aria-labelledby="wb-live">
      <header className="flex items-center gap-2">
        <Activity className="h-4 w-4 text-cyan-700" aria-hidden="true" />
        <h3 id="wb-live" className="font-semibold text-slate-900">
          {t('wb_live_title')}
        </h3>
        {live?.calibrating && <span className="ml-auto rounded-full border border-amber-300 px-2 py-0.5 text-xs text-amber-900">{t('wb_calibrating')}</span>}
      </header>
      {!live ? (
        <p className="text-sm text-slate-600">{t('wb_live_none')}</p>
      ) : (
        <>
          <div className="flex flex-col gap-1">
            <div className="flex items-baseline justify-between text-xs text-slate-700">
              <span>{t('wb_arousal')}</span>
              <span className="font-mono text-base font-semibold text-slate-900">{Math.round(live.arousal)}/100</span>
            </div>
            <div className="relative h-3 rounded-full bg-gradient-to-r from-indigo-200 via-sky-200 to-rose-300" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(live.arousal)} aria-label={t('wb_arousal')}>
              <span className="absolute top-1/2 h-5 w-1.5 -translate-y-1/2 rounded bg-white transition-all" style={{ left: `calc(${Math.round(live.arousal)}% - 3px)` }} />
            </div>
          </div>
          <ul className="grid grid-cols-2 gap-2 lg:grid-cols-4">
            {AREAS.map((area) => (
              <li key={area} className={`rounded-lg border px-3 py-2 text-xs transition ${area === live.area ? `${TONE[area]} ring-2 ring-offset-1 ring-current` : 'border-slate-200 text-slate-600'}`} aria-current={area === live.area}>
                <div className="font-semibold">{t(`wb_area_${area}`)}</div>
                <div className="mt-0.5 opacity-80">{t(`wb_area_${area}_hint`)}</div>
              </li>
            ))}
          </ul>
          <dl className="grid grid-cols-3 gap-2 text-xs text-slate-700">
            {[
              ['wb_brow', percent(live.browTension), BAR.tension],
              ['wb_mimic', percent(live.mimic), BAR.receptive],
              ['wb_lips', percent((live.lipTone + 1) / 2), BAR.relief],
            ].map(([key, value, bar]) => (
              <div key={String(key)} className="flex flex-col gap-1">
                <dt>{t(String(key))}</dt>
                <dd className="h-1.5 rounded-full bg-slate-200">
                  <div className={`h-full rounded-full ${String(bar)}`} style={{ width: `${Number(value)}%` }} />
                </dd>
              </div>
            ))}
          </dl>
          <p className="text-[11px] text-slate-500">{t('wb_estimate')}</p>
        </>
      )}
    </section>
  );
};
