import React from 'react';
import { Activity as ActivityIcon, CircleDot, Loader2, Radio } from 'lucide-react';
import { Expert } from '../data/expertsApi';
import { Activity, DebianLive, FootballLive, Match } from '../data/live';
import { useLive } from '../hooks/useExperts';
import { GIB, glassClass, labelClass, useExpertsI18n } from '../scope';

const pct = (used: number, total: number) => (total > 0 ? Math.min(100, Math.round((used / total) * 100)) : 0);

const Gauge: React.FC<{ readonly label: string; readonly value: number; readonly detail: string; readonly color: string; readonly text?: string }> = ({ label, value, detail, color, text }) => {
  const c = 2 * Math.PI * 34;
  const tone = value >= 90 ? '#fb7185' : value >= 75 ? '#fbbf24' : color;
  return (
    <figure className="flex flex-col items-center gap-1 rounded-xl border border-slate-800/80 bg-slate-950/50 p-2">
      <svg viewBox="0 0 80 80" className="h-20 w-20 3xl:h-28 3xl:w-28" role="img" aria-label={`${label} ${text ?? `${value}%`}`}>
        <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(148,163,184,0.15)" strokeWidth="7" />
        <circle cx="40" cy="40" r="34" fill="none" stroke={tone} strokeWidth="7" strokeLinecap="round" strokeDasharray={`${(c * value) / 100} ${c}`} transform="rotate(-90 40 40)" style={{ filter: `drop-shadow(0 0 6px ${tone})`, transition: 'stroke-dasharray .6s ease' }} />
        <text x="40" y="45" textAnchor="middle" className="fill-white font-mono text-[15px]">{text ?? `${value}%`}</text>
      </svg>
      <figcaption className="text-center text-[0.6875rem] text-slate-400">
        <span className="block font-semibold uppercase tracking-[0.14em] text-slate-300">{label}</span>
        {detail}
      </figcaption>
    </figure>
  );
};

const Debian: React.FC<{ readonly d: DebianLive; readonly color: string }> = ({ d, color }) => {
  const { t } = useExpertsI18n();
  const gb = (v: number) => (v / GIB).toFixed(1);
  const load = d.load[0] ?? 0;
  return (
    <div className="grid gap-3">
      <p className="text-xs text-slate-400">
        <span className="font-semibold text-slate-200">{d.os}</span> · {d.kernel} · {d.host} · {t('uptime', { h: Math.floor(d.uptime / 3600), m: Math.floor((d.uptime % 3600) / 60) })}
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Gauge label={t('memory')} value={pct(d.memory.used, d.memory.total)} detail={`${gb(d.memory.used)} / ${gb(d.memory.total)} GiB`} color={color} />
        <Gauge label={t('disk')} value={pct(d.disk.used, d.disk.total)} detail={`${gb(d.disk.used)} / ${gb(d.disk.total)} GiB`} color={color} />
        <Gauge label={t('load')} value={pct(load, d.cpus || 1)} detail={`${d.load.join(' · ')} / ${d.cpus} CPU`} color={color} />
        {d.temperature !== null ? (
          <Gauge label={t('temperature')} value={Math.min(100, Math.round(d.temperature))} text={`${Math.round(d.temperature)}°`} detail={`${d.temperature} °C`} color={color} />
        ) : (
          <div className="flex items-center justify-center rounded-xl border border-slate-800/80 bg-slate-950/50 p-2 text-center text-[0.6875rem] text-slate-500">{t('temperature_none')}</div>
        )}
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-800/80 bg-slate-950/50 px-3 py-2 text-xs">
          <span className="block text-[0.625rem] uppercase tracking-[0.16em] text-slate-500">{t('failed_units')}</span>
          {d.failed === null ? (
            <span className="text-slate-500">{t('not_available')}</span>
          ) : d.failed.length === 0 ? (
            <span className="text-emerald-300">{t('none')}</span>
          ) : (
            <span className="font-mono text-rose-200">{d.failed.join(', ')}</span>
          )}
        </div>
        <div className="rounded-xl border border-slate-800/80 bg-slate-950/50 px-3 py-2 text-xs">
          <span className="block text-[0.625rem] uppercase tracking-[0.16em] text-slate-500">{t('updates')}</span>
          {d.updates === null ? (
            <span className="text-slate-500">{t('not_available')}</span>
          ) : (
            <span className={d.updates.security ? 'text-amber-200' : 'text-slate-200'}>{t('updates_count', { count: d.updates.count, security: d.updates.security })}</span>
          )}
        </div>
      </div>
    </div>
  );
};

const MatchRow: React.FC<{ readonly m: Match }> = ({ m }) => {
  const { t, lang } = useExpertsI18n();
  const when = m.state === 'in' ? m.clock || t('live') : m.state === 'post' ? t('final') : new Intl.DateTimeFormat(lang, { weekday: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(m.start));
  const score = (v: number | null) => (m.state === 'pre' || v === null ? '–' : String(v));
  return (
    <li className={`grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 rounded-xl border px-3 py-2 text-sm ${m.state === 'in' ? 'border-emerald-400/50 bg-emerald-400/5' : 'border-slate-800/80 bg-slate-950/50'}`}>
      <span className="flex min-w-0 items-center justify-end gap-2 text-right">
        <span className="truncate text-slate-100">{m.home.name}</span>
        <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: m.home.color }} aria-hidden="true" />
      </span>
      <span className="text-center">
        <span className="block font-mono text-lg text-white">{score(m.home.score)} : {score(m.away.score)}</span>
        <span className={`flex items-center justify-center gap-1 text-[0.625rem] ${m.state === 'in' ? 'text-emerald-300' : 'text-slate-500'}`}>
          {m.state === 'in' && <CircleDot className="h-3 w-3 animate-pulse motion-reduce:animate-none" aria-hidden="true" />}
          {when}
        </span>
      </span>
      <span className="flex min-w-0 items-center gap-2">
        <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: m.away.color }} aria-hidden="true" />
        <span className="truncate text-slate-100">{m.away.name}</span>
      </span>
      <span className="col-span-3 text-center text-[0.625rem] uppercase tracking-[0.14em] text-slate-500">{m.league}</span>
    </li>
  );
};

const Football: React.FC<{ readonly d: FootballLive }> = ({ d }) => {
  const { t } = useExpertsI18n();
  if (!d.available) {
    return <p className="text-sm text-slate-500">{t('football_unavailable')}</p>;
  }
  if (d.matches.length === 0) {
    return <p className="text-sm text-slate-500">{t('football_empty')}</p>;
  }
  return <ul className="grid gap-2 2xl:grid-cols-2">{d.matches.map((m) => <MatchRow key={m.id} m={m} />)}</ul>;
};

const Feed: React.FC<{ readonly a: Activity }> = ({ a }) => {
  const { t, lang } = useExpertsI18n();
  const time = new Intl.DateTimeFormat(lang, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  return (
    <div className="grid gap-2">
      <p className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-xs ${a.doing ? 'border-emerald-400/40 bg-emerald-400/5 text-emerald-100' : 'border-slate-800 text-slate-500'}`}>
        <Radio className={`h-3.5 w-3.5 ${a.doing ? 'animate-pulse motion-reduce:animate-none' : ''}`} aria-hidden="true" />
        {a.doing ? t('doing', { what: a.doing }) : t('idle')}
      </p>
      {a.recent.length > 0 && (
        <ol className="grid gap-1" aria-live="polite">
          {[...a.recent].reverse().map((m, i) => (
            <li key={`${m.at}-${i}`} className="flex gap-2 text-[0.6875rem]">
              <span className="shrink-0 font-mono text-slate-500">{m.at ? time.format(new Date(m.at * 1000)) : ''}</span>
              <span className={`break-words ${m.kind === 'errore' ? 'text-rose-200' : 'text-slate-300'}`}>{m.text}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
};

export const LivePanel: React.FC<{ readonly expert: Expert }> = ({ expert }) => {
  const { t } = useExpertsI18n();
  const live = useLive(expert.id, expert.live);
  return (
    <section className={glassClass} aria-labelledby="expert-live">
      <h3 id="expert-live" className={labelClass}>
        <ActivityIcon className="h-3.5 w-3.5" style={{ color: expert.color }} aria-hidden="true" />
        {t(`live_${expert.live}`)}
        <span className="ml-auto flex items-center gap-1 rounded-full border border-emerald-400/40 px-2 py-0.5 text-[0.625rem] tracking-[0.1em] text-emerald-200">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-300 motion-reduce:animate-none" aria-hidden="true" />
          {t('live')}
        </span>
      </h3>
      {!live ? (
        <p className="flex items-center gap-2 text-sm text-slate-500" role="status">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          {t('loading_live')}
        </p>
      ) : (
        <div className="grid gap-4">
          {live.data?.kind === 'debian' && <Debian d={live.data} color={expert.color} />}
          {live.data?.kind === 'football' && <Football d={live.data} />}
          <Feed a={live.activity} />
        </div>
      )}
    </section>
  );
};
