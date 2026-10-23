import React, { useCallback, useMemo, useState } from 'react';
import { Loader2, UsersRound } from 'lucide-react';
import { PAGE_CLASS } from '../../shared/ui/layout';
import { useAction, usePolled } from '../../node_apps/shared/hooks/useAction';
import { createPerson, fetchPeople, fetchPresence, fetchSchema } from './data/peopleApi';
import { PeopleList } from './components/PeopleList';
import { PersonView } from './components/PersonView';
import { RemindersTab } from './components/RemindersTab';
import { HouseHabits } from './house/HouseHabits';
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
    async (key: string, task: () => Promise<unknown>, code: string) => (await action.run(key, task, code)) !== undefined,
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
  const person = people.find((p) => p.slug === selected) ?? people.find((p) => !p.scanned) ?? people[0] ?? null;
  const known = people.filter((p) => !p.scanned);
  const stats = [
    [t('stat_people'), known.length],
    [t('stat_present'), present.size],
    [t('stat_home'), known.filter((p) => p.membership === 'home' || p.membership === 'both' || ['owner', 'family'].includes(p.role)).length],
    [t('stat_scanned'), people.length - known.length],
  ] as const;

  return (
    <div className={PAGE_CLASS}>
      <section className={`${panelClass} flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between`}>
        <div>
          <h1 className="flex items-center gap-2 font-['Rajdhani'] text-3xl font-bold tracking-wide text-slate-900">
            <UsersRound className="h-7 w-7 text-blue-700" aria-hidden="true" />
            {t('title')}
          </h1>
          <p className="mt-1 text-sm text-slate-600">{t('description')}</p>
          {presence.data && presence.data.status !== 'ok' && <p className="mt-1 text-xs text-amber-800">{t('presence_off')}</p>}
        </div>
        <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {stats.map(([label, value]) => (
            <div key={label} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
              <dt className="text-[10px] uppercase tracking-[0.14em] text-slate-500">{label}</dt>
              <dd className="font-mono text-xl text-slate-900">{value}</dd>
            </div>
          ))}
        </dl>
      </section>
      <div role="tablist" aria-label={t('title')} className="flex gap-1 self-start rounded-xl border border-slate-200 bg-slate-50 p-1">
        {(['people', 'reminders', 'house'] as const).map((id) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={`rounded-lg px-4 py-1.5 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${tab === id ? 'bg-blue-100 text-blue-900' : 'text-slate-600 hover:text-slate-900'}`}
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
      <div className={`grid gap-4 lg:grid-cols-[20rem_minmax(0,1fr)] 4xl:grid-cols-[24rem_minmax(0,1fr)] ${tab === 'people' ? '' : 'hidden'}`}>
        <aside className={panelClass} aria-label={t('people_list')}>
          <PeopleList
            people={people}
            roles={list.data.roles}
            present={present}
            selected={person?.slug ?? null}
            busy={action.busy !== null}
            onSelect={setSelected}
            onCreate={(name) => void run('create', () => createPerson(name), 'people_create_failed')}
          />
        </aside>
        {person ? (
          <PersonView
            key={person.slug}
            summary={person}
            sections={schema.data.sections}
            voices={schema.data.voices}
            people={people}
            roles={list.data.roles}
            present={present.has(person.slug)}
            busy={action.busy}
            run={run}
            onDeleted={() => {
              setSelected(null);
              list.refresh();
            }}
          />
        ) : (
          <section className={`${panelClass} text-sm text-slate-600`}>{t('empty')}</section>
        )}
      </div>
    </div>
  );
};

export default View;
