import React, { FormEvent, useMemo, useState } from 'react';
import { Check, Plus, Search, UserPlus, X } from 'lucide-react';
import { PersonSummary } from '../data/peopleApi';
import { fieldClass, primaryClass, usePeopleI18n } from '../scope';
import { IdentityCard } from './IdentityCard';
import { sortKey } from './names';

interface Props {
  readonly people: readonly PersonSummary[];
  readonly roles: Readonly<Record<string, string>>;
  readonly present: ReadonlySet<string>;
  readonly busy: boolean;
  readonly onOpen: (slug: string) => void;
  readonly onCreate: (name: string) => void;
}

const FILTERS = ['all', 'home', 'business', 'present', 'incomplete'] as const;
type Filter = (typeof FILTERS)[number];
const GRID = 'os-tiles [--tile-min:9rem] [--tile-gap:0.75rem]';

export const IdentityGallery: React.FC<Props> = ({ people, roles, present, busy, onOpen, onCreate }) => {
  const { t } = usePeopleI18n();
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<Filter>('all');
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState('');

  const { known, scanned } = useMemo(() => {
    const q = query.trim().toLocaleLowerCase();
    const match = (p: PersonSummary) => {
      if (q && !`${p.name} ${p.nickname} ${p.firstName} ${p.lastName}`.toLocaleLowerCase().includes(q)) return false;
      if (filter === 'home') return p.membership === 'home' || p.membership === 'both' || ['owner', 'family'].includes(p.role);
      if (filter === 'business') return p.membership === 'business' || p.membership === 'both';
      if (filter === 'present') return present.has(p.slug);
      if (filter === 'incomplete') return p.quality <= 0;
      return true;
    };
    const rows = people.filter(match);
    return {
      known: rows.filter((p) => !p.scanned).sort((a, b) => sortKey(a).localeCompare(sortKey(b))),
      scanned: rows.filter((p) => p.scanned),
    };
  }, [people, query, filter, present]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const clean = name.trim();
    if (clean) {
      onCreate(clean);
      setName('');
      setAdding(false);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
        <label className="relative min-w-0 flex-1 lg:max-w-md">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface-variant" aria-hidden="true" />
          <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t('search')} aria-label={t('search')} className={`${fieldClass} rounded-2xl py-2.5 pl-10`} />
        </label>
        <div className="flex gap-1.5 overflow-x-auto pb-1 lg:pb-0" role="group" aria-label={t('filters')}>
          {FILTERS.map((f) => (
            <button
              key={f}
              type="button"
              aria-pressed={filter === f}
              onClick={() => setFilter(f)}
              className={`md-state flex shrink-0 items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-xs font-semibold ${
                filter === f ? 'border-transparent bg-secondary-container text-on-secondary-container' : 'border-outline bg-transparent text-on-surface-variant'
              }`}
            >
              {filter === f && <Check className="md-pop h-3.5 w-3.5" aria-hidden="true" />}
              {t(`filter_${f}`)}
            </button>
          ))}
        </div>
        <div className="lg:ml-auto">
          {adding ? (
            <form onSubmit={submit} className="flex gap-2">
              <input autoFocus maxLength={40} value={name} onChange={(event) => setName(event.target.value)} placeholder={t('new_person')} aria-label={t('new_person')} className={`${fieldClass} min-w-0 flex-1 rounded-2xl lg:w-64`} />
              <button type="submit" disabled={busy || !name.trim()} aria-label={t('add_person')} className={`${primaryClass} px-3`}>
                <Plus className="h-4 w-4" aria-hidden="true" />
              </button>
              <button type="button" onClick={() => setAdding(false)} aria-label={t('cancel')} className="md-state rounded-full border-0 bg-transparent px-2 text-on-surface-variant">
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </form>
          ) : (
            <button type="button" onClick={() => setAdding(true)} className={`${primaryClass} w-full lg:w-auto`}>
              <UserPlus className="h-4 w-4" aria-hidden="true" />
              {t('id_new')}
            </button>
          )}
        </div>
      </div>
      {known.length === 0 && scanned.length === 0 ? (
        <p className="md-enter rounded-3xl bg-surface-container-low px-6 py-14 text-center text-sm text-on-surface-variant">{people.length ? t('no_people') : t('empty')}</p>
      ) : (
        <ul className={`${GRID} md-stagger`} aria-label={t('people_list')}>
          {known.map((p) => (
            <li key={p.slug}>
              <IdentityCard person={p} role={roles[p.role] ?? p.role} present={present.has(p.slug)} onOpen={onOpen} />
            </li>
          ))}
        </ul>
      )}
      {scanned.length > 0 && (
        <section aria-labelledby="id-scanned" className="flex flex-col gap-3">
          <h2 id="id-scanned" className="text-sm font-bold uppercase tracking-[0.12em] text-warning">{t('id_to_identify', { n: scanned.length })}</h2>
          <ul className={`${GRID} md-stagger`}>
            {scanned.map((p) => (
              <li key={p.slug}>
                <IdentityCard person={p} role="" present={present.has(p.slug)} onOpen={onOpen} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
};
