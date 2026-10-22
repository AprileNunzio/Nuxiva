import React from 'react';
import { Search } from 'lucide-react';
import { fieldClass, useFleetI18n } from '../scope';
import { CATEGORIES, FleetFilters, KINDS, ORIGINS, STATES } from '../types';

interface Props {
  readonly filters: FleetFilters;
  readonly onChange: (filters: FleetFilters) => void;
}

interface SelectProps {
  readonly name: keyof FleetFilters;
  readonly options: readonly string[];
  readonly prefix: string;
  readonly filters: FleetFilters;
  readonly onChange: (filters: FleetFilters) => void;
}

const FilterSelect: React.FC<SelectProps> = ({ name, options, prefix, filters, onChange }) => {
  const { t } = useFleetI18n();
  return (
    <select
      aria-label={t(`filter_${name}`)}
      className={fieldClass}
      value={filters[name]}
      onChange={(event) => onChange({ ...filters, [name]: event.target.value })}
    >
      <option value="">{t(`filter_${name}`)}: {t('all')}</option>
      {options.map((option) => (
        <option key={option} value={option}>
          {t(`${prefix}_${option}`)}
        </option>
      ))}
    </select>
  );
};

export const FilterBar: React.FC<Props> = ({ filters, onChange }) => {
  const { t } = useFleetI18n();
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-[2fr_repeat(4,1fr)]">
      <label className="relative block">
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-500" aria-hidden="true" />
        <input
          type="search"
          maxLength={80}
          className={`${fieldClass} pl-9`}
          placeholder={t('search')}
          aria-label={t('search')}
          value={filters.q}
          onChange={(event) => onChange({ ...filters, q: event.target.value })}
        />
      </label>
      <FilterSelect name="state" options={STATES} prefix="state" filters={filters} onChange={onChange} />
      <FilterSelect name="kind" options={KINDS} prefix="kind" filters={filters} onChange={onChange} />
      <FilterSelect name="category" options={CATEGORIES} prefix="category" filters={filters} onChange={onChange} />
      <FilterSelect name="origin" options={ORIGINS} prefix="origin" filters={filters} onChange={onChange} />
    </div>
  );
};
