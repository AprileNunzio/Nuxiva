import React from 'react';
import { OSFilterTabs, inputClass } from '../../shared/kit';
import { EarFilters, EarPerson } from '../types';

interface Props {
  readonly filters: EarFilters;
  readonly people: readonly EarPerson[];
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly onChange: (next: Partial<EarFilters>) => void;
}

export const Filters: React.FC<Props> = ({ filters, people, t, onChange }) => (
  <div className="mb-4 grid gap-2">
    <OSFilterTabs
      ariaLabel={t('filter_kind')}
      selected={filters.kind || 'all'}
      onSelect={(id) => onChange({ kind: id === 'all' ? '' : (id as EarFilters['kind']) })}
      options={[
        { id: 'all', label: t('filter_all') },
        { id: 'command', label: t('kind_command') },
        { id: 'heard', label: t('kind_heard') },
      ]}
    />
    <OSFilterTabs
      ariaLabel={t('filter_verdict')}
      selected={filters.verdict || 'all'}
      onSelect={(id) => onChange({ verdict: id === 'all' ? '' : (id as EarFilters['verdict']) })}
      options={[
        { id: 'all', label: t('filter_all') },
        { id: 'pending', label: t('verdict_pending') },
        { id: 'ok', label: t('verdict_ok') },
        { id: 'wrong', label: t('verdict_wrong') },
      ]}
    />
    <div className="grid gap-2 sm:grid-cols-2">
      <select className={inputClass} value={filters.speaker} aria-label={t('filter_speaker')} onChange={(event) => onChange({ speaker: event.target.value })}>
        <option value="">{t('filter_speaker_all')}</option>
        {people.map((person) => (
          <option key={person.slug} value={person.slug}>
            {person.name}
          </option>
        ))}
        <option value="-">{t('speaker_unknown')}</option>
      </select>
      <input className={inputClass} value={filters.query} maxLength={80} placeholder={t('search_placeholder')} aria-label={t('search_placeholder')} onChange={(event) => onChange({ query: event.target.value })} />
    </div>
  </div>
);
