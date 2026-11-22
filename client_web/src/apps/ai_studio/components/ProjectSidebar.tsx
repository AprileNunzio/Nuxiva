import React, { useState } from 'react';
import { useStudioI18n } from '../scope';
import type { Project, Thread, Workpiece3DData } from '../types';

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
  onOpen3DViewer?: (data?: Workpiece3DData) => void;
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
  onOpen3DViewer,
}) => {
  const { t } = useStudioI18n();
  const [search, setSearch] = useState('');

  const safeProjects = Array.isArray(projects) ? projects.filter(Boolean) : [];
  const safeThreads = Array.isArray(threads) ? threads.filter(Boolean) : [];

  const currentProject = safeProjects.find((p) => p && p.id === selectedProjectId);

  const isLiveVoiceSelected = selectedThreadId === 'th_live_voice_port80';

  const manualThreads = safeThreads.filter((th) => {
    if (!th) return false;
    if (th.id === 'th_live_voice_port80') return false;
    if (selectedProjectId && th.project_id !== selectedProjectId) return false;
    if (search.trim()) {
      return (th.title || '').toLowerCase().includes(search.toLowerCase());
    }
    return true;
  });

  return (
    <aside className="w-full h-full flex flex-col bg-slate-950/80 border-r border-slate-800/80 backdrop-blur-md">
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
              {safeProjects.map((p) => (
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

          {onOpen3DViewer && (
            <button
              type="button"
              onClick={() => onOpen3DViewer({
                title: currentProject ? `Lavorazione 3D · ${currentProject.name}` : 'Lavorazione 3D CAD & Laser CNC',
                format: 'openscad',
                material: 'PLA / Compensato Laser',
                dimensions_mm: [60, 90, 30],
                tolerance_mm: 0.15,
                kerf_mm: 0.14,
              })}
              className="p-1.5 rounded-lg bg-slate-900 border border-slate-700/80 text-cyan-400 hover:text-cyan-300 hover:border-cyan-600 text-xs transition-colors"
              title="Apri finestra lavorazione 3D"
            >
              🧊
            </button>
          )}

          <button
            type="button"
            onClick={onOpenMemoryHud}
            className="p-1.5 rounded-lg bg-slate-900 border border-slate-700/80 text-purple-400 hover:text-purple-300 hover:border-purple-600 text-xs transition-colors"
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

      <div className="p-2 border-b border-slate-800/80 bg-slate-900/40">
        <div
          onClick={() => onSelectThread('th_live_voice_port80')}
          className={`group relative flex flex-col p-2.5 rounded-xl text-xs cursor-pointer transition-all border shadow-md ${
            isLiveVoiceSelected
              ? 'bg-gradient-to-r from-cyan-950/80 to-blue-950/80 text-white font-semibold border-cyan-500 shadow-cyan-950/50'
              : 'bg-slate-900/80 text-slate-200 hover:bg-slate-800 border-cyan-500/30 hover:border-cyan-400'
          }`}
        >
          <div className="flex items-center justify-between gap-1 mb-1">
            <span className="flex items-center gap-1.5 text-cyan-400 font-bold text-[11px] tracking-wide uppercase">
              <span>📌</span>
              <span>Conversazione Vocale</span>
            </span>
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 text-[9px] font-mono border border-cyan-500/40 animate-pulse">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
              <span>PAGINA 80 LIVE</span>
            </span>
          </div>

          <div className="flex items-center gap-2 text-slate-300 text-xs mt-0.5">
            <span className="text-sm">🎙️</span>
            <span className="truncate flex-1">Stream audio duplex e trascrizioni voce</span>
          </div>
        </div>
      </div>

      <div className="px-3 pt-2 pb-1 text-[10px] font-semibold tracking-wider text-slate-500 uppercase flex items-center justify-between">
        <span>Chat Manuali & Progetti</span>
        <span className="text-slate-600 font-mono">{manualThreads.length}</span>
      </div>

      <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-1">
        {manualThreads.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-500">{t('no_threads')}</div>
        ) : (
          manualThreads.map((thread) => {
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
                  {onOpen3DViewer && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onOpen3DViewer({
                          title: `3D · ${thread.title}`,
                          format: 'openscad',
                          dimensions_mm: [50, 50, 20],
                        });
                      }}
                      className="p-1 hover:text-cyan-300 text-slate-500"
                      title="Visualizza lavorazione 3D"
                    >
                      🧊
                    </button>
                  )}
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
