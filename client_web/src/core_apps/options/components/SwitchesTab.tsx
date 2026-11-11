import React from 'react';
import { Search, Sliders, CheckCircle2, XCircle } from 'lucide-react';
import type { OptionCategory, SystemSwitchOption } from '../types';

interface SwitchesTabProps {
  options: SystemSwitchOption[];
  search: string;
  setSearch: (v: string) => void;
  selectedCategory: OptionCategory | 'all';
  setSelectedCategory: (cat: OptionCategory | 'all') => void;
  categories: Array<{ id: OptionCategory | 'all'; label: string }>;
  onToggle: (id: string) => void;
  t: (k: string) => string;
}

export function SwitchesTab({
  options,
  search,
  setSearch,
  selectedCategory,
  setSelectedCategory,
  categories,
  onToggle,
  t,
}: SwitchesTabProps) {
  const q = search.trim().toLowerCase();
  const filteredOptions = options.filter((opt) => {
    const matchCategory = selectedCategory === 'all' || opt.category === selectedCategory;
    if (!matchCategory) return false;
    if (!q) return true;

    const title = t(opt.titleKey).toLowerCase();
    const desc = t(opt.descriptionKey).toLowerCase();
    const matchTags = opt.tags.some((tag) => tag.toLowerCase().includes(q));

    return title.includes(q) || desc.includes(q) || matchTags;
  });

  return (
    <>
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-on-surface-variant" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('search_placeholder')}
            className="w-full rounded-xl border border-outline-variant/60 bg-surface-container py-2 pl-9 pr-4 text-xs text-on-surface placeholder:text-outline focus:border-primary focus:outline-hidden"
          />
        </div>

        <div className="flex flex-wrap gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {categories.map((cat) => (
            <button
              key={cat.id}
              type="button"
              onClick={() => setSelectedCategory(cat.id)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition-all ${
                selectedCategory === cat.id
                  ? 'bg-primary text-on-primary shadow-xs'
                  : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 space-y-2.5">
        {filteredOptions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center text-outline">
            <Sliders className="h-10 w-10 stroke-[1.5]" />
            <p className="mt-2 text-xs">{t('no_options_found')}</p>
          </div>
        ) : (
          filteredOptions.map((opt) => (
            <div
              key={opt.id}
              onClick={() => onToggle(opt.id)}
              className="flex cursor-pointer items-center justify-between gap-4 rounded-2xl border border-outline-variant/50 bg-surface-container p-3.5 shadow-2xs transition-all hover:border-primary/40 hover:bg-surface-container-high sm:p-4"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-on-surface">{t(opt.titleKey)}</h3>
                  {opt.enabled ? (
                    <span className="flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary">
                      <CheckCircle2 className="h-3 w-3" />
                      {t('active')}
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 rounded-full bg-surface-container-highest px-2 py-0.5 text-[10px] font-medium text-outline">
                      <XCircle className="h-3 w-3" />
                      {t('disabled')}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-on-surface-variant leading-relaxed">
                  {t(opt.descriptionKey)}
                </p>
              </div>

              <div className="shrink-0">
                <div
                  role="switch"
                  aria-checked={opt.enabled}
                  tabIndex={0}
                  className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors duration-200 ease-in-out focus:outline-hidden ${
                    opt.enabled ? 'bg-primary' : 'bg-surface-container-highest border border-outline-variant'
                  }`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-md transition duration-200 ease-in-out ${
                      opt.enabled ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </>
  );
}
