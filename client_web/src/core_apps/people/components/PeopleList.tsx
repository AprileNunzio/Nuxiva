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
            className={`shrink-0 rounded-full border px-3 py-1 text-xs transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
              filter === f ? 'border-cyan-400/60 bg-cyan-400/15 text-cyan-100' : 'border-slate-700 text-slate-400 hover:text-white'
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
              className={`flex w-full items-center gap-3 rounded-xl border px-3 py-2 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                selected === p.slug ? 'border-cyan-400/60 bg-cyan-400/10' : 'border-slate-800/80 bg-slate-950/40 hover:border-slate-600'
              }`}
            >
              <span className={`relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full border text-sm font-bold ${p.scanned ? 'border-amber-400/50 bg-amber-400/10 text-amber-200' : 'border-slate-700 bg-slate-900 text-cyan-100'}`}>
                {p.scanned ? <ScanFace className="h-5 w-5" aria-hidden="true" /> : initials(p.name)}
                {present.has(p.slug) && <span className="absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-slate-950 bg-emerald-400" aria-label={t('present_now')} />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold text-slate-100">{p.scanned ? t('unknown_face') : p.name}</span>
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
      <form onSubmit={submit} className="flex gap-2 border-t border-slate-800/80 pt-3">
        <input maxLength={40} value={name} onChange={(event) => setName(event.target.value)} placeholder={t('new_person')} aria-label={t('new_person')} className={`${fieldClass} min-w-0 flex-1`} />
        <button type="submit" disabled={busy || !name.trim()} aria-label={t('add_person')} className={`${chipClass} border-cyan-400/50 bg-cyan-400/10 px-3 text-cyan-100`}>
          <Plus className="h-4 w-4" aria-hidden="true" />
        </button>
      </form>
    </div>
  );
};
