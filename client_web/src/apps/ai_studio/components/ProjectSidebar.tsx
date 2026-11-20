import React, { useState } from 'react';
import { useStudioI18n } from '../scope';
import type { Project, Thread } from '../types';

interface ProjectSidebarProps {
  projects: Project[];
  threads: Thread[];
  selectedProjectId: string | null;
  selectedThreadId: string | null;
  onSelectProject: (projectId: string | null) => void;
  onSelectThread: (threadId: string) => void;
  onNewChat: () => void;
  onNewProject: () => void;
  onEditProject: (project: Project) => void;
  onTogglePin: (thread: Thread) => void;
  onDeleteThread: (threadId: string) => void;
  onOpenMemoryHud: () => void;
}

export const ProjectSidebar: React.FC<ProjectSidebarProps> = ({
  projects,
  threads,
  selectedProjectId,
  selectedThreadId,
  onSelectProject,
  onSelectThread,
  onNewChat,
  onNewProject,
  onEditProject,
  onTogglePin,
  onDeleteThread,
  onOpenMemoryHud,
}) => {
  const { t } = useStudioI18n();
  const [search, setSearch] = useState('');

  const currentProject = projects.find((p) => p.id === selectedProjectId);

  const filteredThreads = threads.filter((th) => {
    if (selectedProjectId && th.project_id !== selectedProjectId) return false;
    if (search.trim()) {
      return th.title.toLowerCase().includes(search.toLowerCase());
    }
    return true;
  });

  return (
    <aside className="w-full md:w-72 md:min-w-72 h-full flex flex-col bg-slate-950/80 border-r border-slate-800/80 backdrop-blur-md">
      <div className="p-3 flex flex-col gap-2 border-b border-slate-800/60">
        <button
          type="button"
          onClick={onNewChat}
          className="w-full py-2.5 px-3 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-sm font-semibold flex items-center justify-center gap-2 shadow-lg shadow-cyan-950/50 transition-all active:scale-[0.98]"
        >
          <span>＋</span>
          <span>{t('new_chat')}</span>
        </button>

        <div className="flex items-center justify-between gap-1 pt-1">
          <div className="flex-1 relative">
            <select
              value={selectedProjectId || ''}
              onChange={(e) => onSelectProject(e.target.value || null)}
              className="w-full appearance-none bg-slate-900 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-medium focus:outline-none focus:border-cyan-500 truncate pr-6"
            >
              <option value="">{t('all_chats')}</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  📁 {p.name}
                </option>
              ))}
            </select>
            <span className="absolute right-2 top-2 pointer-events-none text-slate-400 text-xs">▼</span>
          </div>

          <button
            type="button"
            onClick={onNewProject}
            className="p-1.5 rounded-lg bg-slate-900 border border-slate-700/80 text-slate-300 hover:text-white hover:border-slate-600 text-xs transition-colors"
            title={t('new_project')}
          >
            ＋
          </button>

          {currentProject && (
            <button
              type="button"
              onClick={() => onEditProject(currentProject)}
              className="p-1.5 rounded-lg bg-slate-900 border border-slate-700/80 text-slate-300 hover:text-white hover:border-slate-600 text-xs transition-colors"
              title={t('project_settings')}
            >
              ⚙
            </button>
          )}

          <button
            type="button"
            onClick={onOpenMemoryHud}
            className="p-1.5 rounded-lg bg-slate-900 border border-slate-700/80 text-cyan-400 hover:text-cyan-300 hover:border-cyan-600 text-xs transition-colors"
            title={t('memory_hud')}
          >
            🧠
          </button>
        </div>

        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('search_placeholder')}
          className="w-full bg-slate-900/90 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-slate-700"
        />
      </div>

      <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-1">
        {filteredThreads.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-500">{t('no_threads')}</div>
        ) : (
          filteredThreads.map((thread) => {
            const isSelected = thread.id === selectedThreadId;
            return (
              <div
                key={thread.id}
                onClick={() => onSelectThread(thread.id)}
                className={`group relative flex items-center justify-between p-2 rounded-xl text-xs cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-slate-800/90 text-white font-medium border border-cyan-500/30 shadow-sm'
                    : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <span className="text-slate-500 text-sm">
                    {thread.pinned ? '📌' : '💬'}
                  </span>
                  <span className="truncate flex-1">{thread.title}</span>
                </div>

                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-1">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onTogglePin(thread);
                    }}
                    className="p-1 hover:text-cyan-400 text-slate-500"
                    title={thread.pinned ? t('unpin') : t('pin')}
                  >
                    📌
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteThread(thread.id);
                    }}
                    className="p-1 hover:text-red-400 text-slate-500"
                    title={t('delete')}
                  >
                    🗑
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
};
