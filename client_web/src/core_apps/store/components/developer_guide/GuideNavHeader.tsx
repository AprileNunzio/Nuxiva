import React from 'react';
import {
  Sparkles,
  BookOpen,
  ListOrdered,
  FileJson,
  Code,
  ShieldCheck
} from 'lucide-react';
import type { GuideSubTab } from './types';

interface GuideNavHeaderProps {
  t: (key: string, params?: Record<string, any>) => string;
  activeSubTab: GuideSubTab;
  onSelectSubTab: (tab: GuideSubTab) => void;
}

export const GuideNavHeader: React.FC<GuideNavHeaderProps> = ({
  t,
  activeSubTab,
  onSelectSubTab
}) => {
  return (
    <div className="rounded-3xl border border-[var(--md-sys-color-outline-variant)] bg-gradient-to-br from-indigo-950/40 via-[var(--md-sys-color-surface-container)] to-blue-950/30 p-6 shadow-sm space-y-5">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="p-3 rounded-2xl bg-blue-500/15 text-blue-400 border border-blue-400/30 shrink-0 shadow-xs">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-blue-500/20 text-blue-300 border border-blue-400/30">
                Nuxiva OS SDK & Developer Portal
              </span>
            </div>
            <h2 className="text-xl font-extrabold text-[var(--md-sys-color-on-surface)] tracking-tight">
              {t('dev_guide_title')}
            </h2>
            <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed max-w-3xl mt-1">
              {t('dev_guide_subtitle')}
            </p>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 p-1.5 bg-[var(--md-sys-color-surface)]/80 backdrop-blur-sm rounded-2xl border border-[var(--md-sys-color-outline-variant)]">
        <button
          type="button"
          onClick={() => onSelectSubTab('overview')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
            activeSubTab === 'overview'
              ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs'
              : 'text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          <span>{t('dev_subtab_overview')}</span>
        </button>

        <button
          type="button"
          onClick={() => onSelectSubTab('steps')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
            activeSubTab === 'steps'
              ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs'
              : 'text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]'
          }`}
        >
          <ListOrdered className="w-4 h-4" />
          <span>{t('dev_subtab_steps')}</span>
        </button>

        <button
          type="button"
          onClick={() => onSelectSubTab('manifest')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
            activeSubTab === 'manifest'
              ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs'
              : 'text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]'
          }`}
        >
          <FileJson className="w-4 h-4" />
          <span>{t('dev_subtab_manifest')}</span>
        </button>

        <button
          type="button"
          onClick={() => onSelectSubTab('code')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
            activeSubTab === 'code'
              ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs'
              : 'text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]'
          }`}
        >
          <Code className="w-4 h-4" />
          <span>{t('dev_subtab_code')}</span>
        </button>

        <button
          type="button"
          onClick={() => onSelectSubTab('best_practices')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
            activeSubTab === 'best_practices'
              ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs'
              : 'text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]'
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          <span>{t('dev_subtab_best_practices')}</span>
        </button>
      </div>
    </div>
  );
};
