import React, { useEffect, useState } from 'react';
import { Eye } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { ObservedHabits, PersonSummary, Profile, SchemaSection, fetchObservedHabits, habitsOf } from '../data/peopleApi';
import { localLabel, panelClass, relative, usePeopleI18n } from '../scope';
import { SectionForm } from './SectionForm';

const Bars: React.FC<{ readonly values: readonly number[]; readonly labels: readonly string[]; readonly title: string }> = ({ values, labels, title }) => {
  const max = Math.max(1, ...values);
  return (
    <figure className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-3">
      <figcaption className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">{title}</figcaption>
      <div className="flex h-32 items-end gap-1" role="img" aria-label={title}>
        {values.map((v, i) => (
          <div key={i} className="flex h-full flex-1 flex-col items-center gap-1">
            <div className="flex w-full flex-1 items-end">
              <div className="w-full rounded-t bg-gradient-to-t from-cyan-500/40 to-cyan-300 shadow-[0_0_12px_rgba(34,211,238,0.35)]" style={{ height: `${(v / max) * 100}%`, minHeight: v ? 3 : 0 }} title={`${labels[i]}: ${v}`} />
            </div>
            <span className="h-3 text-[9px] leading-3 text-slate-500">{labels[i]}</span>
          </div>
        ))}
      </div>
    </figure>
  );
};

interface HabitsTabProps {
  readonly summary: PersonSummary;
  readonly profile: Profile;
  readonly section: SchemaSection | undefined;
  readonly people: readonly PersonSummary[];
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
}

export const HabitsTab: React.FC<HabitsTabProps> = ({ summary, profile, section, people, busy, run }) => {
  const { t, lang } = usePeopleI18n();
  const [observed, setObserved] = useState<ObservedHabits | null>(null);
  const habits = habitsOf(profile);
  const stats = (typeof profile.stats === 'object' && profile.stats !== null ? profile.stats : {}) as Record<string, unknown>;
  const days = Array.from({ length: 7 }, (_, i) => new Intl.DateTimeFormat(lang, { weekday: 'short' }).format(new Date(2024, 0, 1 + i)));
  const hours = Array.from({ length: 24 }, (_, h) => (h % 3 === 0 ? String(h) : ''));
  const facts = [
    [t('visits'), String(stats.visits ?? 0)],
    [t('avg_stay'), t('minutes', { minutes: Math.round(habits.avgMinutes) })],
    [t('first_seen'), relative(Number(stats.first_seen ?? 0), lang) || '—'],
    [t('last_seen'), relative(Number(stats.last_seen ?? 0), lang) || '—'],
  ];

  useEffect(() => {
    const controller = new AbortController();
    fetchObservedHabits(summary.slug, controller.signal)
      .then(setObserved)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_habits_failed', cause));
    return () => controller.abort();
  }, [summary.slug]);

  return (
    <div className="flex flex-col gap-4">
      {section ? (
        <div className={panelClass}>
          <SectionForm
            slug={summary.slug}
            title={localLabel(t, lang, `section_${section.id}`, section.title)}
            isPrivate={section.private}
            fields={section.fields}
            profile={profile}
            people={people}
            busy={busy}
            run={run}
          />
        </div>
      ) : null}
      <section className={panelClass} aria-label={t('observed_title')}>
        <h3 className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
          <Eye className="h-4 w-4 text-purple-300" aria-hidden="true" />
          {t('observed_title')}
        </h3>
        <p className="mb-3 text-xs text-slate-500">{t('observed_hint', { days: observed?.days ?? 21 })}</p>
        {!observed || observed.habits.length === 0 ? (
          <p className="text-sm text-slate-400">{observed ? t('observed_none', { events: observed.events }) : t('loading')}</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {observed.habits.map((habit) => (
              <li key={habit.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2">
                <span className="text-sm text-slate-200">{habit.text}</span>
                <span className="font-mono text-[11px] text-slate-500">{t('observed_evidence', { support: habit.support, observed: habit.observed, confidence: Math.round(habit.confidence * 100) })}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
      <p className="rounded-xl border border-cyan-400/20 bg-cyan-400/5 px-3 py-2 text-sm text-cyan-100">{habits.summary || t('habits_none')}</p>
      <dl className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        {facts.map(([label, value]) => (
          <div key={label} className="rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2">
            <dt className="text-[10px] uppercase tracking-wider text-slate-500">{label}</dt>
            <dd className="font-mono text-lg text-white">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="grid gap-3 xl:grid-cols-2">
        <Bars values={habits.arrivalHours} labels={hours} title={t('arrivals_by_hour')} />
        <Bars values={habits.weekdays} labels={days} title={t('arrivals_by_day')} />
      </div>
    </div>
  );
};
