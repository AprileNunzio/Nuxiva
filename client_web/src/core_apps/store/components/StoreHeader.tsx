import React from 'react';
import { Package, FolderGit2, Plus, HardDrive, Cpu, RefreshCw, Code2 } from 'lucide-react';
import { StoreResources } from '../types';

interface StoreHeaderProps {
  t: (key: string, params?: Record<string, any>) => string;
  activeTab: 'packages' | 'repositories' | 'developer_guide';
  setActiveTab: (tab: 'packages' | 'repositories' | 'developer_guide') => void;
  packagesCount: number;
  repositoriesCount: number;
  resources: StoreResources | null;
  loading: boolean;
  onRefresh: () => void;
  onOpenAddRepo: () => void;
}

export const StoreHeader: React.FC<StoreHeaderProps> = ({
  t,
  activeTab,
  setActiveTab,
  packagesCount,
  repositoriesCount,
  resources,
  loading,
  onRefresh,
  onOpenAddRepo
}) => {
  return (
    <header className="px-6 py-3.5 border-b border-[var(--md-sys-color-outline-variant)] bg-[var(--os-glass-header)] backdrop-blur-md flex flex-wrap items-center justify-between gap-4 shrink-0 shadow-xs">
      <div className="flex items-center gap-3.5">
        <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20 ring-1 ring-blue-500/20">
          <span className="text-xl">🛍️</span>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold tracking-tight text-[var(--md-sys-color-on-surface)]">{t('title')}</h1>
            <span className="px-2 py-0.5 text-[10px] font-semibold bg-blue-500/15 text-blue-400 border border-blue-400/20 rounded-full">
              OS AppCenter
            </span>
          </div>
          <p className="text-xs text-[var(--md-sys-color-on-surface-variant)]">{t('subtitle')}</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center p-1 bg-[var(--md-sys-color-surface-container)] rounded-xl border border-[var(--md-sys-color-outline-variant)] text-xs font-semibold">
          <button
            type="button"
            onClick={() => setActiveTab('packages')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
              activeTab === 'packages'
                ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs font-bold'
                : 'text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]'
            }`}
          >
            <Package className="w-3.5 h-3.5" />
            <span>{t('tab_packages')}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/20 text-white font-mono">
              {packagesCount}
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('developer_guide')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
              activeTab === 'developer_guide'
                ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs font-bold'
                : 'text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]'
            }`}
          >
            <Code2 className="w-3.5 h-3.5" />
            <span>{t('tab_developer_guide')}</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('repositories')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
              activeTab === 'repositories'
                ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs font-bold'
                : 'text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]'
            }`}
          >
            <FolderGit2 className="w-3.5 h-3.5" />
            <span>{t('tab_repositories')}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/20 text-white font-mono">
              {repositoriesCount}
            </span>
          </button>
        </div>

        <button
          type="button"
          onClick={onOpenAddRepo}
          className="os-btn os-btn-secondary py-1.5 px-3 text-xs"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>{t('add_repo_button')}</span>
        </button>

        {resources && (
          <div className="flex items-center gap-3.5 bg-[var(--md-sys-color-surface-container)] px-3 py-1.5 rounded-xl border border-[var(--md-sys-color-outline-variant)] text-xs shadow-xs">
            <div className="flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-[var(--md-sys-color-primary)] shrink-0" />
              <div className="flex flex-col">
                <span className="text-[9px] text-[var(--md-sys-color-on-surface-variant)] uppercase tracking-wider font-bold">
                  {t('storage_status')}
                </span>
                <span className="font-mono text-[var(--md-sys-color-on-surface)] font-bold text-[11px]">
                  {resources.disk_free_gb} GB
                </span>
              </div>
            </div>

            <div className="w-px h-5 bg-[var(--md-sys-color-outline-variant)]" />

            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-emerald-400 shrink-0" />
              <div className="flex flex-col">
                <span className="text-[9px] text-[var(--md-sys-color-on-surface-variant)] uppercase tracking-wider font-bold">
                  RAM
                </span>
                <span className="font-mono text-[var(--md-sys-color-on-surface)] font-bold text-[11px]">
                  {resources.ram_total_gb} GB
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={onRefresh}
              disabled={loading}
              className="p-1 text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-primary)] rounded-md transition active:scale-90"
              title={t('refresh')}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
