import React, { FormEvent, useMemo, useState } from 'react';
import { Plus, ScanFace, Search } from 'lucide-react';
import { PersonSummary } from '../data/peopleApi';
import { chipClass, fieldClass, initials, relative, usePeopleI18n } from '../scope';

interface PeopleListProps {
  readonly people: readonly PersonSummary[];
  readonly roles: Readonly<Record<string, string>>;
  readonly present: ReadonlySet<string>;
  readonly selected: string | null;
  readonly busy: boolean;
  readonly onSelect: (slug: string) => void;
  readonly onCreate: (name: string) => void;
}

const FILTERS = ['all', 'home', 'business', 'present', 'incomplete', 'scanned'] as const;
type Filter = (typeof FILTERS)[number];

export const PeopleList: React.FC<PeopleListProps> = ({ people, roles, present, selected, busy, onSelect, onCreate }) => {
  const { t, lang } = usePeopleI18n();
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<Filter>('all');
  const [name, setName] = useState('');

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return people
      .filter((p) => {
        if (q && !`${p.name} ${p.nickname}`.toLowerCase().includes(q)) return false;
        if (filter === 'home') return p.membership === 'home' || p.membership === 'both' || ['owner', 'family'].includes(p.role);
        if (filter === 'business') return p.membership === 'business' || p.membership === 'both';
        if (filter === 'present') return present.has(p.slug);
        if (filter === 'incomplete') return !p.scanned && p.quality <= 0;
        if (filter === 'scanned') return p.scanned;
        return true;
      })
      .sort((a, b) => Number(present.has(b.slug)) - Number(present.has(a.slug)) || Number(a.scanned) - Number(b.scanned) || a.name.localeCompare(b.name));
  }, [people, query, filter, present]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (name.trim()) {
      onCreate(name.trim());
      setName('');
    }
  };

  return (
    <div className="flex min-h-0 flex-col gap-3">
      <label className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
        <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t('search')} aria-label={t('search')} className={`${fieldClass} pl-9`} />
      </label>
      <div className="flex gap-1.5 overflow-x-auto pb-1" role="tablist" aria-label={t('filters')}>
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            role="tab"
            aria-selected={filter === f}
            onClick={() => setFilter(f)}
            className={`shrink-0 rounded-full border px-3 py-1 text-xs transition focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
              filter === f ? 'border-blue-300 bg-blue-100 text-blue-900' : 'border-slate-300 text-slate-600 hover:text-slate-900'
            }`}
          >
            {t(`filter_${f}`)}
          </button>
        ))}
      </div>
      <ul className="flex max-h-[65vh] flex-col gap-1.5 overflow-y-auto pr-1">
        {visible.map((p) => (
          <li key={p.slug}>
            <button
              type="button"
              aria-current={selected === p.slug}
              onClick={() => onSelect(p.slug)}
              className={`flex w-full items-center gap-3 rounded-xl border px-3 py-2 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                selected === p.slug ? 'border-blue-300 bg-blue-50' : 'border-slate-200 bg-slate-50 hover:border-slate-400'
              }`}
            >
              <span className={`relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full border text-sm font-bold ${p.scanned ? 'border-amber-300 bg-amber-50 text-amber-800' : 'border-slate-300 bg-slate-100 text-blue-900'}`}>
                {p.scanned ? <ScanFace className="h-5 w-5" aria-hidden="true" /> : initials(p.name)}
                {present.has(p.slug) && <span className="absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-white bg-emerald-500" aria-label={t('present_now')} />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold text-slate-900">{p.scanned ? t('unknown_face') : p.name}</span>
                <span className="block truncate text-[11px] text-slate-500">
                  {[roles[p.role] ?? p.role, p.age !== null ? t('age', { age: p.age }) : '', p.lastSeen ? relative(p.lastSeen, lang) : t('never_seen')].filter(Boolean).join(' · ')}
                </span>
              </span>
              {p.quality > 0 && <span className="shrink-0 font-mono text-[10px] text-slate-500">{Math.round(p.quality)}%</span>}
            </button>
          </li>
        ))}
        {visible.length === 0 && <li className="px-3 py-6 text-center text-sm text-slate-500">{t('no_people')}</li>}
      </ul>
      <form onSubmit={submit} className="flex gap-2 border-t border-slate-200 pt-3">
        <input maxLength={40} value={name} onChange={(event) => setName(event.target.value)} placeholder={t('new_person')} aria-label={t('new_person')} className={`${fieldClass} min-w-0 flex-1`} />
        <button type="submit" disabled={busy || !name.trim()} aria-label={t('add_person')} className={`${chipClass} border-blue-300 bg-blue-50 px-3 text-blue-900`}>
          <Plus className="h-4 w-4" aria-hidden="true" />
        </button>
      </form>
    </div>
  );
};
