import React, { useMemo, useState } from 'react';
import { Plus, Search } from 'lucide-react';
import { Expert } from '../data/expertsApi';
import { fieldClass, useExpertsI18n } from '../scope';
import { ExpertAvatar } from './ExpertAvatar';

interface ExpertRosterProps {
  readonly experts: readonly Expert[];
  readonly selected: string | null;
  readonly onSelect: (id: string) => void;
  readonly onCreate: () => void;
}

const TECHNICAL = new Set(['debian', 'football']);
const GROUPS = ['all', 'teacher', 'professional', 'technical', 'custom'] as const;
type Group = (typeof GROUPS)[number];

export function groupOf(expert: Expert): Exclude<Group, 'all'> {
  if (!expert.template) {
    return 'custom';
  }
  if (expert.template.startsWith('teacher-')) {
    return 'teacher';
  }
  return TECHNICAL.has(expert.template) ? 'technical' : 'professional';
}

export const ExpertRoster: React.FC<ExpertRosterProps> = ({ experts, selected, onSelect, onCreate }) => {
  const { t } = useExpertsI18n();
  const [query, setQuery] = useState('');
  const [group, setGroup] = useState<Group>('all');
  const present = useMemo(() => GROUPS.filter((g) => g === 'all' || experts.some((e) => groupOf(e) === g)), [experts]);
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return experts.filter((e) => (group === 'all' || groupOf(e) === group) && (!q || `${e.role} ${e.specialty}`.toLowerCase().includes(q)));
  }, [experts, query, group]);

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <label className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t('search')}
          aria-label={t('search')}
          className={`${fieldClass} w-full pl-9`}
        />
      </label>
      <div className="flex gap-1.5 overflow-x-auto pb-1" role="tablist" aria-label={t('groups')}>
        {present.map((g) => (
          <button
            key={g}
            type="button"
            role="tab"
            aria-selected={group === g}
            onClick={() => setGroup(g)}
            className={`shrink-0 rounded-full border px-3 py-1 text-xs transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
              group === g ? 'border-cyan-400/60 bg-cyan-400/15 text-cyan-100' : 'border-slate-700 text-slate-400 hover:text-white'
            }`}
          >
            {t(`group_${g}`)}
          </button>
        ))}
      </div>
      <nav aria-label={t('roster')} className="flex snap-x gap-3 overflow-x-auto pb-1 lg:max-h-[70vh] lg:flex-col lg:overflow-y-auto lg:overflow-x-visible lg:pr-1">
        {visible.map((e) => {
          const active = e.id === selected;
          const busy = Boolean(e.doing);
          return (
            <button
              key={e.id}
              type="button"
              onClick={() => onSelect(e.id)}
              aria-current={active ? 'true' : undefined}
              className={`group flex min-w-[15rem] snap-start items-center gap-3 rounded-2xl border px-3 py-2.5 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 lg:min-w-0 ${
                active ? 'border-cyan-400/60 bg-cyan-400/10 shadow-[0_0_24px_rgba(34,211,238,0.15)]' : 'border-slate-800 bg-slate-950/50 hover:border-cyan-400/40'
              } ${e.enabled ? '' : 'opacity-60'}`}
            >
              <ExpertAvatar icon={e.icon} color={e.color} busy={busy} />
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2">
                  <span className="truncate font-['Rajdhani'] text-lg font-bold text-white">{e.role}</span>
                  <span
                    className={`h-2 w-2 shrink-0 rounded-full ${e.pending ? 'bg-amber-300' : busy ? 'animate-pulse bg-emerald-300' : e.enabled ? 'bg-cyan-300/70' : 'bg-slate-600'}`}
                    aria-hidden="true"
                  />
                </span>
                <span className="block truncate text-xs text-slate-400">{e.specialty}</span>
                <span className="block truncate text-[0.6875rem] text-cyan-200/80">
                  {e.pending ? t('status_waiting') : busy ? t('status_busy', { what: e.doing }) : e.enabled ? t('status_ready') : t('status_off')}
                </span>
              </span>
            </button>
          );
        })}
        {visible.length === 0 && <p className="px-2 py-3 text-sm text-slate-500">{t('no_match')}</p>}
        <button
          type="button"
          onClick={onCreate}
          className="flex min-w-[12rem] snap-start items-center justify-center gap-2 rounded-2xl border border-dashed border-cyan-400/40 px-3 py-3 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 lg:min-w-0"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          {t('new_expert')}
        </button>
      </nav>
    </div>
  );
};
