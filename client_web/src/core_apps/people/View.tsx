import React, { useCallback, useMemo, useState } from 'react';
import { Fingerprint, Loader2 } from 'lucide-react';
import { PAGE_CLASS } from '../../shared/ui/layout';
import { useAction, usePolled } from '../../node_apps/shared/hooks/useAction';
import { createPerson, fetchPeople, fetchPresence, fetchSchema } from './data/peopleApi';
import { RemindersTab } from './components/RemindersTab';
import { HouseHabits } from './house/HouseHabits';
import { IdentityGallery } from './identity/IdentityGallery';
import { PersonPage } from './identity/PersonPage';
import { panelClass, usePeopleI18n } from './scope';

export const View: React.FC = () => {
  const { t } = usePeopleI18n();
  const list = usePolled(fetchPeople, 'people_unavailable', true, 15000);
  const presence = usePolled(fetchPresence, 'people_presence_failed', true, 5000);
  const schema = usePolled(fetchSchema, 'people_schema_failed', true, 0);
  const action = useAction(list.refresh);
  const [selected, setSelected] = useState<string | null>(null);
  const [tab, setTab] = useState<'people' | 'reminders' | 'house'>('people');
  const present = useMemo(() => new Set(presence.data?.present ?? []), [presence.data]);
  const run = useCallback(
    async (key: string, task: () => Promise<unknown>, code: string) => {
      let succeeded = false;
      await action.run(
        key,
        async () => {
          await task();
          succeeded = true;
        },
        code,
      );
      return succeeded;
    },
    [action],
  );

  if (!list.data || !schema.data) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center gap-2 text-sm text-slate-600" role="status">
        <Loader2 className="h-5 w-5 animate-spin text-blue-700" aria-hidden="true" />
        {t('loading')}
      </div>
    );
  }

  const people = list.data.people;
  const person = selected ? people.find((p) => p.slug === selected) ?? null : null;
  const known = people.filter((p) => !p.scanned);
  const stats = [
    [t('stat_people'), known.length],
    [t('stat_present'), present.size],
    [t('stat_home'), known.filter((p) => p.membership === 'home' || p.membership === 'both' || ['owner', 'family'].includes(p.role)).length],
    [t('stat_scanned'), people.length - known.length],
  ] as const;

  return (
    <div className={PAGE_CLASS}>
      <header className="flex flex-col gap-4 rounded-3xl bg-gradient-to-br from-slate-900 via-slate-900 to-blue-950 p-5 text-white shadow-lg sm:p-6 lg:flex-row lg:items-center">
        <div className="flex min-w-0 flex-1 items-center gap-4">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white/10 ring-1 ring-white/20">
            <Fingerprint className="h-6 w-6 text-sky-300" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <h1 className="font-['Rajdhani'] text-3xl font-bold tracking-wide">{t('title')}</h1>
            <p className="mt-0.5 text-sm text-slate-300">{t('description')}</p>
            {presence.data && presence.data.status !== 'ok' && <p className="mt-1 text-xs text-amber-300">{t('presence_off')}</p>}
          </div>
        </div>
        <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {stats.map(([label, value]) => (
            <div key={label} className="flex flex-col-reverse rounded-2xl bg-white/5 px-3 py-2 ring-1 ring-white/10">
              <dt className="mt-1 truncate text-[10px] uppercase tracking-[0.12em] text-slate-400">{label}</dt>
              <dd className="font-['Rajdhani'] text-2xl font-bold leading-none">{value}</dd>
            </div>
          ))}
        </dl>
      </header>
      <div role="tablist" aria-label={t('title')} className="flex gap-1 self-start rounded-2xl bg-slate-100 p-1">
        {(['people', 'reminders', 'house'] as const).map((id) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={`rounded-xl px-4 py-1.5 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${tab === id ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
          >
            {t(`main_tab_${id}`)}
          </button>
        ))}
      </div>
      {tab === 'reminders' && (
        <RemindersTab
          onOpen={(slug) => {
            setSelected(slug);
            setTab('people');
          }}
        />
      )}
      {tab === 'house' && (
        <section className={panelClass}>
          <HouseHabits />
        </section>
      )}
      {tab === 'people' &&
        (person ? (
          <PersonPage
            key={person.slug}
            summary={person}
            sections={schema.data.sections}
            voices={schema.data.voices}
            people={people}
            roles={list.data.roles}
            present={present.has(person.slug)}
            busy={action.busy}
            run={run}
            onBack={() => setSelected(null)}
            onDeleted={() => {
              setSelected(null);
              list.refresh();
            }}
          />
        ) : (
          <IdentityGallery
            people={people}
            roles={list.data.roles}
            present={present}
            busy={action.busy !== null}
            onOpen={setSelected}
            onCreate={(name) => void run('create', () => createPerson(name), 'people_create_failed')}
          />
        ))}
    </div>
  );
};

export default View;
