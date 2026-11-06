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
      <div className="flex min-h-[40vh] items-center justify-center gap-2 text-sm text-muted-foreground" role="status">
        <Loader2 className="h-5 w-5 animate-spin text-primary" aria-hidden="true" />
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
    <div className={`${PAGE_CLASS} people-app`}>
      <header className="md-hero md-enter flex flex-col gap-5 rounded-[1.75rem] p-5 shadow-[var(--md-elevation-1)] sm:p-6 lg:flex-row lg:items-center">
        <div className="flex min-w-0 flex-1 items-center gap-4">
          <span className="md-hero-tile md-pop flex h-14 w-14 shrink-0 items-center justify-center rounded-[1.25rem]">
            <Fingerprint className="h-7 w-7 text-primary" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{t('title')}</h1>
            <p className="md-hero-muted mt-1 text-sm">{t('description')}</p>
            {presence.data && presence.data.status !== 'ok' && (
              <p className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-warning-container px-2.5 py-0.5 text-xs font-medium text-on-warning-container">{t('presence_off')}</p>
            )}
          </div>
        </div>
        <dl className="md-stagger flex flex-wrap gap-2 lg:flex-nowrap">
          {stats.map(([label, value]) => (
            <div key={label} className="md-hero-tile flex min-w-[6.5rem] flex-1 basis-[calc(50%-0.25rem)] flex-col-reverse rounded-2xl px-3.5 py-2.5 sm:basis-0">
              <dt className="md-hero-muted mt-1 truncate text-[11px] font-medium uppercase tracking-[0.08em]">{label}</dt>
              <dd className="text-2xl font-bold leading-none tabular-nums">{value}</dd>
            </div>
          ))}
        </dl>
      </header>
      <div role="tablist" aria-label={t('title')} className="flex gap-1 self-start rounded-full bg-surface-container-high p-1">
        {(['people', 'reminders', 'house'] as const).map((id) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={`md-state rounded-full border-0 px-4 py-1.5 text-sm font-semibold ${tab === id ? 'bg-secondary-container text-on-secondary-container shadow-[var(--md-elevation-1)]' : 'bg-transparent text-on-surface-variant'}`}
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
