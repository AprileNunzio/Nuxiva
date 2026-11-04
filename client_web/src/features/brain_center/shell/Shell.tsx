import React from 'react';
import { Cpu } from 'lucide-react';
import { useBrainText } from '../core/i18n';
import { SECTION_ICONS, SECTION_IDS, SectionId } from './sections';

interface ShellProps {
  readonly active: SectionId;
  readonly onSelect: (id: SectionId) => void;
  readonly children: React.ReactNode;
}

export const Shell: React.FC<ShellProps> = ({ active, onSelect, children }) => {
  const { t } = useBrainText();
  return (
    <div className="flex h-full min-h-0 w-full flex-col bg-slate-100 font-sans text-slate-900 md:flex-row">
      <nav aria-label={t('nav_label')} className="shrink-0 border-b border-slate-200 bg-slate-50 md:w-60 md:border-b-0 md:border-r lg:w-64">
        <div className="hidden items-center gap-3 px-5 pb-3 pt-5 md:flex">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-xs">
            <Cpu className="h-5 w-5" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="truncate text-base font-semibold text-slate-900">{t('title')}</p>
            <p className="truncate text-xs text-slate-500">{t('tagline')}</p>
          </div>
        </div>
        <ul className="flex gap-1 overflow-x-auto px-2 py-2 md:flex-col md:overflow-visible md:px-3">
          {SECTION_IDS.map((id) => {
            const Icon = SECTION_ICONS[id];
            const selected = id === active;
            return (
              <li key={id} className="shrink-0">
                <button
                  type="button"
                  aria-current={selected ? 'page' : undefined}
                  onClick={() => onSelect(id)}
                  className={`relative flex min-h-[40px] w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 ${
                    selected ? 'bg-white font-semibold text-slate-900 shadow-2xs' : 'text-slate-600 hover:bg-slate-200/60 hover:text-slate-900'
                  }`}
                >
                  {selected && <span className="absolute left-0 top-1/2 hidden h-5 w-1 -translate-y-1/2 rounded-full bg-blue-600 md:block" aria-hidden="true" />}
                  <Icon className={`h-4 w-4 shrink-0 ${selected ? 'text-blue-600' : 'text-slate-500'}`} aria-hidden="true" />
                  <span className="whitespace-nowrap">{t(`nav_${id}`)}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-[200rem] flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8 lg:py-7 2xl:px-10">{children}</div>
      </main>
    </div>
  );
};
