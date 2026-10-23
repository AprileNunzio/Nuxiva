import React, { useEffect, useMemo, useState } from 'react';
import { Cake, CalendarDays, Gift } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Reminder, fetchReminders } from '../data/peopleApi';
import { panelClass, usePeopleI18n } from '../scope';

interface RemindersTabProps {
  readonly onOpen: (slug: string) => void;
}

const RANGES = [30, 90, 365] as const;

const iconOf = (type: string) => {
  if (type === 'compleanno') return <Cake className="h-4 w-4 text-pink-300" aria-hidden="true" />;
  if (type === 'onomastico') return <Gift className="h-4 w-4 text-amber-300" aria-hidden="true" />;
  return <CalendarDays className="h-4 w-4 text-cyan-300" aria-hidden="true" />;
};

export const RemindersTab: React.FC<RemindersTabProps> = ({ onOpen }) => {
  const { t, lang } = usePeopleI18n();
  const [range, setRange] = useState<number>(90);
  const [data, setData] = useState<Reminder[] | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetchReminders(range, controller.signal)
      .then(setData)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_reminders_failed', cause));
    return () => controller.abort();
  }, [range]);
  const rows = useMemo(() => [...(data ?? [])].sort((a: Reminder, b: Reminder) => a.days - b.days || a.person.localeCompare(b.person)), [data]);
  const format = (iso: string) => new Intl.DateTimeFormat(lang, { weekday: 'short', day: 'numeric', month: 'long' }).format(new Date(`${iso}T12:00:00`));

  return (
    <section className={panelClass} aria-label={t('reminders_title')}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white">{t('reminders_title')}</h2>
          <p className="text-xs text-slate-400">{t('reminders_hint')}</p>
        </div>
        <div role="tablist" aria-label={t('reminders_range')} className="flex gap-1 rounded-xl border border-slate-800/80 bg-slate-950/60 p-1">
          {RANGES.map((days) => (
            <button
              key={days}
              type="button"
              role="tab"
              aria-selected={range === days}
              onClick={() => setRange(days)}
              className={`rounded-lg px-3 py-1 text-xs font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${range === days ? 'bg-cyan-400/15 text-cyan-100' : 'text-slate-400 hover:text-white'}`}
            >
              {t('reminders_days', { n: days })}
            </button>
          ))}
        </div>
      </div>
      {rows.length === 0 ? (
        <p className="py-6 text-center text-sm text-slate-500">{data ? t('reminders_empty') : t('loading')}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.map((reminder) => (
            <li key={`${reminder.slug}-${reminder.type}-${reminder.date}-${reminder.title}`}>
              <button
                type="button"
                onClick={() => onOpen(reminder.slug)}
                className="flex w-full items-center gap-3 rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2 text-left transition hover:border-cyan-400/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              >
                {iconOf(reminder.type)}
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-slate-100">{reminder.title}</span>
                  <span className="block text-[11px] text-slate-500">{format(reminder.date)}</span>
                </span>
                <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] ${reminder.days <= 7 ? 'border-amber-400/50 text-amber-200' : 'border-slate-700 text-slate-400'}`}>
                  {reminder.days === 0 ? t('reminders_today') : t('reminders_in', { n: reminder.days })}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};
