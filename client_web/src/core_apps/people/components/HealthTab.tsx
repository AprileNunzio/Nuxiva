import React, { useEffect, useMemo, useState } from 'react';
import { Activity, AlertTriangle, Footprints, HeartPulse, Moon, Scale, Wind } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { HEALTH_GROUPS, HealthGroup, HealthState, HealthValue, fetchHealth, setCameraVitals, syncHealth } from '../data/healthApi';
import { usePeopleI18n } from '../scope';
import { Ring, Sparkline } from './HealthCharts';
import { HealthSources } from './HealthSources';
import { VitalsCard } from './VitalsCard';

interface Props {
  readonly slug: string;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
  readonly onConnectors: () => void;
}

const REFRESH_MS = 15000;
const SPANS = [7, 14, 30] as const;
const GROUP_ICON: Record<HealthGroup, React.ElementType> = { heart: HeartPulse, breath: Wind, body: Scale, move: Footprints, rest: Moon };
const GROUP_TONE: Record<HealthGroup, string> = {
  heart: 'text-rose-600', breath: 'text-sky-600', body: 'text-violet-600', move: 'text-emerald-600', rest: 'text-indigo-600',
};
const BAND_TONE = { high: 'text-emerald-500', mid: 'text-amber-500', low: 'text-rose-500' } as const;
const RING_TONE: Record<string, string> = { steps: 'text-emerald-500', active_kcal: 'text-orange-500', sleep_min: 'text-indigo-500' };

export const HealthTab: React.FC<Props> = ({ slug, busy, run, onConnectors }) => {
  const { t, lang } = usePeopleI18n();
  const [state, setState] = useState<HealthState | null>(null);
  const [days, setDays] = useState<(typeof SPANS)[number]>(14);
  const [tick, setTick] = useState(0);
  const number = useMemo(() => new Intl.NumberFormat(lang, { maximumFractionDigits: 1 }), [lang]);

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(slug, days, controller.signal)
      .then(setState)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_health_failed', cause));
    return () => controller.abort();
  }, [slug, days, tick]);

  useEffect(() => {
    const timer = window.setInterval(() => setTick((v) => v + 1), REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  const sync = () => void run('health-sync', () => syncHealth(slug), 'people_health_failed').then(() => setTick((v) => v + 1));
  const toggleCamera = () =>
    state && void run('health-camera', () => setCameraVitals(!state.camera.enabled), 'people_health_failed').then(() => setTick((v) => v + 1));
  const show = (v: HealthValue) => (v.metric === 'sleep_min' || v.metric.startsWith('sleep_') ? t('hl_hours', { h: Math.floor(v.value / 60), m: Math.round(v.value % 60) }) : number.format(v.value));

  if (!state) {
    return null;
  }
  const byGroup = HEALTH_GROUPS.map((g) => ({ g, rows: state.values.filter((v) => v.group === g) })).filter((x) => x.rows.length);
  const heart = state.values.find((v) => v.metric === 'heart_rate');
  const empty = state.values.length === 0;

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs text-slate-600">{t('hl_hint')}</p>
      {empty ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-600">{t('hl_empty')}</div>
      ) : (
        <>
          <section className="grid gap-3 cq-lg:grid-cols-[auto_minmax(0,1fr)_auto]" aria-label={t('hl_overview')}>
            <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-900 to-slate-800 p-4 text-white">
              <Ring pct={state.recovery?.score ?? 0} tone={state.recovery ? BAND_TONE[state.recovery.band] : 'text-slate-500'} label={t('hl_recovery')}>
                <b className="text-3xl font-light tabular-nums">{state.recovery ? state.recovery.score : '—'}</b>
                <small className="text-[10px] uppercase tracking-widest text-slate-300">{t('hl_recovery')}</small>
              </Ring>
              <p className="max-w-[12rem] text-xs text-slate-300">{t(state.recovery ? `hl_band_${state.recovery.band}` : 'hl_recovery_missing')}</p>
            </div>
            <div className="flex min-w-0 flex-col justify-between gap-2 rounded-2xl border border-rose-200 bg-gradient-to-br from-rose-50 to-white p-4">
              <div className="flex items-baseline gap-2">
                <HeartPulse className={`h-5 w-5 self-center text-rose-600 ${heart ? 'animate-pulse' : ''}`} aria-hidden="true" />
                <span className="text-xs font-semibold uppercase tracking-wider text-rose-700">{t('hm_heart_rate')}</span>
                <b className="ml-auto text-3xl font-light tabular-nums text-slate-900">{heart ? number.format(heart.value) : '—'}</b>
                <small className="text-xs text-slate-500">bpm</small>
              </div>
              <Sparkline values={state.pulse} label={t('hl_pulse_30')} tone="text-rose-500" height={48} />
            </div>
            <div className="flex items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-white p-4">
              {state.rings.map((r) => (
                <Ring key={r.metric} pct={r.pct} size={84} stroke={8} tone={RING_TONE[r.metric] ?? 'text-blue-500'} label={t(`hm_${r.metric}`)}>
                  <b className="text-sm font-semibold tabular-nums text-slate-900">{r.pct}%</b>
                  <small className="max-w-[4.5rem] truncate text-[10px] text-slate-500">{t(`hm_${r.metric}`)}</small>
                </Ring>
              ))}
              {!state.rings.length && <Activity className="h-6 w-6 text-slate-300" aria-hidden="true" />}
            </div>
          </section>
          {state.signals.length > 0 && (
            <ul className="flex flex-wrap gap-2" aria-label={t('hl_signals')}>
              {state.signals.map((s) => (
                <li key={`${s.metric}-${s.code}`} className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${s.level === 'alert' ? 'border-rose-400 bg-rose-50 text-rose-800' : 'border-amber-300 bg-amber-50 text-amber-900'}`}>
                  <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
                  {t(`hs_${s.metric}_${s.code}`)}
                </li>
              ))}
              <li className="self-center text-[11px] text-slate-500">{t('hl_not_medical')}</li>
            </ul>
          )}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-600">{t('hl_range')}</span>
            {SPANS.map((d) => (
              <button key={d} type="button" aria-pressed={days === d} onClick={() => setDays(d)}
                className={`rounded-lg px-2.5 py-1 text-xs font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${days === d ? 'bg-blue-100 text-blue-900' : 'text-slate-600 hover:text-slate-900'}`}>
                {t('hl_days', { n: d })}
              </button>
            ))}
          </div>
          {byGroup.map(({ g, rows }) => {
            const Icon = GROUP_ICON[g];
            return (
              <section key={g} aria-labelledby={`hg-${g}`} className="flex flex-col gap-2">
                <h3 id={`hg-${g}`} className={`flex items-center gap-2 text-sm font-bold ${GROUP_TONE[g]}`}>
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {t(`hg_${g}`)}
                </h3>
                <div className="grid gap-2 cq-sm:grid-cols-2 cq-xl:grid-cols-4">
                  {rows.map((v) => (
                    <article key={v.metric} className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
                      <span className="text-xs text-slate-600">{t(`hm_${v.metric}`)}</span>
                      <b className="text-2xl font-light tabular-nums text-slate-900">
                        {show(v)}
                        {!v.metric.startsWith('sleep_') && v.unit && <small className="ml-1 text-xs font-normal text-slate-500">{v.unit}</small>}
                      </b>
                      <Sparkline values={(state.trends[v.metric] ?? []).map((p) => p.value)} label={t('hl_trend', { n: days })} tone={GROUP_TONE[g]} />
                      <span className="text-[11px] text-slate-500">{t(`hl_src_${v.kind}`)} · {relative(v.age, lang)}</span>
                    </article>
                  ))}
                </div>
              </section>
            );
          })}
        </>
      )}
      <HealthSources state={state} busy={busy} onSync={sync} onConnectors={onConnectors} onCamera={toggleCamera} />
      <div className="grid gap-3 cq-xl:grid-cols-2">
        <VitalsCard slug={slug} busy={busy} run={run} />
      </div>
    </div>
  );
};

function relative(age: number, lang: string): string {
  const units: [Intl.RelativeTimeFormatUnit, number][] = [['day', 86400], ['hour', 3600], ['minute', 60], ['second', 1]];
  const [unit, size] = units.find(([, s]) => age >= s) ?? units[3];
  return new Intl.RelativeTimeFormat(lang, { numeric: 'auto' }).format(-Math.round(age / size), unit);
}
