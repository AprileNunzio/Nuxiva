import React from 'react';
import { Search, X, LucideIcon } from 'lucide-react';

interface CategoryItem {
  id: string;
  label: string;
  icon: LucideIcon;
}

interface StoreFilterBarProps {
  categories: CategoryItem[];
  activeCategory: string;
  setActiveCategory: (cat: string) => void;
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  getCategoryCount: (catId: string) => number;
  searchPlaceholder: string;
}

export const StoreFilterBar: React.FC<StoreFilterBarProps> = ({
  categories,
  activeCategory,
  setActiveCategory,
  searchQuery,
  setSearchQuery,
  getCategoryCount,
  searchPlaceholder
}) => {
  return (
    <div className="px-6 py-3 border-b border-[var(--md-sys-color-outline-variant)] flex flex-wrap items-center justify-between gap-3 shrink-0 bg-[var(--os-glass-bg)]">
      <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-0.5">
        {categories.map(c => {
          const Icon = c.icon;
          const count = getCategoryCount(c.id);
          const isActive = activeCategory === c.id;
          return (
            <button
              type="button"
              key={c.id}
              onClick={() => setActiveCategory(c.id)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium flex items-center gap-2 transition-all ${
                isActive
                  ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs font-semibold'
                  : 'bg-[var(--md-sys-color-surface-container)] text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-high)] hover:text-[var(--md-sys-color-on-surface)] border border-[var(--md-sys-color-outline-variant)]'
              }`}
            >
              <Icon className="w-3.5 h-3.5 shrink-0" />
              <span>{c.label}</span>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded-full font-mono ${
                  isActive ? 'bg-white/20 text-white' : 'bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-on-surface-variant)]'
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      <div className="relative w-full sm:w-64">
        <Search className="w-4 h-4 text-[var(--md-sys-color-on-surface-variant)] absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          placeholder={searchPlaceholder}
          className="os-input text-xs pl-9 pr-8 py-1.5"
        />
        {searchQuery && (
          <button
            type="button"
            onClick={() => setSearchQuery('')}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
};
