import React from 'react';
import { ShieldCheck, FolderGit2, Trash2, Plus } from 'lucide-react';
import { StoreRepository, StorePackage } from '../types';

interface RepositoriesViewProps {
  repositories: StoreRepository[];
  packages: StorePackage[];
  onOpenAddRepo: () => void;
  onDeleteRepo: (id: string) => void;
  t: (key: string, params?: Record<string, any>) => string;
}

export const RepositoriesView: React.FC<RepositoriesViewProps> = ({
  repositories,
  packages,
  onOpenAddRepo,
  onDeleteRepo,
  t
}) => {
  return (
    <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
      <div className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-wrap items-center justify-between gap-4 shadow-xs">
        <div>
          <h2 className="text-base font-bold text-slate-900">{t('repo_title')}</h2>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">{t('repo_subtitle')}</p>
        </div>
        <button
          onClick={onOpenAddRepo}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 active:scale-95 text-white rounded-xl text-xs font-semibold shadow-xs transition"
        >
          <Plus className="w-4 h-4" />
          <span>{t('add_repo_button')}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {repositories.map(repo => {
          const isOfficial = repo.official || repo.id === 'official';
          return (
            <div
              key={repo.id}
              className="bg-white border border-slate-200/90 rounded-2xl p-5 flex flex-col justify-between shadow-xs hover:border-slate-300 transition-all"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center border ${
                        isOfficial
                          ? 'bg-blue-50 text-blue-600 border-blue-200'
                          : 'bg-amber-50 text-amber-600 border-amber-200'
                      }`}
                    >
                      {isOfficial ? <ShieldCheck className="w-5 h-5" /> : <FolderGit2 className="w-5 h-5" />}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-bold text-sm text-slate-900">{repo.name}</h3>
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.2 rounded-full border ${
                            isOfficial
                              ? 'bg-blue-50 text-blue-700 border-blue-200'
                              : 'bg-amber-50 text-amber-700 border-amber-200'
                          }`}
                        >
                          {isOfficial ? t('repo_official_badge') : t('repo_custom_badge')}
                        </span>
                      </div>
                      <span className="text-[11px] font-mono text-slate-400 break-all block mt-0.5">
                        {repo.url}
                      </span>
                    </div>
                  </div>
                </div>

                <p className="text-xs text-slate-600 mt-3 leading-relaxed">
                  {repo.description || 'Nessuna descrizione specificata.'}
                </p>
              </div>

              <div className="pt-3 mt-4 border-t border-slate-100 flex items-center justify-between text-xs">
                <span className="text-slate-500 font-medium">
                  {t('repo_packages_count', {
                    count:
                      repo.packages_count ??
                      (isOfficial
                        ? packages.filter(p => p.source !== 'custom').length
                        : packages.filter(p => p.repository_id === repo.id).length)
                  })}
                </span>

                {isOfficial ? (
                  <span className="text-slate-400 font-medium italic text-[11px]">
                    {t('repo_protected')}
                  </span>
                ) : (
                  <button
                    onClick={() => onDeleteRepo(repo.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-rose-600 hover:text-rose-700 hover:bg-rose-50 border border-rose-200 rounded-xl transition text-xs font-medium"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Rimuovi</span>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
