import React, { useState, useEffect, useCallback } from 'react';
import { useStudioI18n } from './scope';
import type { Project, Thread, Message, Artifact, Attachment, ModelMode } from './types';
import * as api from './api';
import { ProjectSidebar } from './components/ProjectSidebar';
import { ConversationView } from './components/ConversationView';
import { InputOmnibar } from './components/InputOmnibar';
import { ArtifactCanvas } from './components/ArtifactCanvas';
import { SmbFilePickerModal } from './components/SmbFilePickerModal';
import { MemoryInspectorModal } from './components/MemoryInspectorModal';
import { NewProjectModal } from './components/NewProjectModal';

export const View: React.FC = () => {
  const { t } = useStudioI18n();
  const [projects, setProjects] = useState<Project[]>([]);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [selectedMode, setSelectedMode] = useState<ModelMode>('reasoning');
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);

  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [isSmbPickerOpen, setIsSmbPickerOpen] = useState(false);
  const [isMemoryHudOpen, setIsMemoryHudOpen] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  const loadProjects = useCallback(async () => {
    try {
      const data = await api.fetchProjects();
      setProjects(data);
    } catch (err) {
      console.error(err);
    }
  }, []);

  const loadThreads = useCallback(async (projId?: string | null) => {
    try {
      const data = await api.fetchThreads(projId);
      setThreads(data);
      if (data.length > 0 && !selectedThreadId) {
        setSelectedThreadId(data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  }, [selectedThreadId]);

  const loadMessages = useCallback(async (thId: string) => {
    try {
      const data = await api.fetchMessages(thId);
      setMessages(data);
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    loadProjects();
    loadThreads(selectedProjectId);
  }, [loadProjects, loadThreads, selectedProjectId]);

  useEffect(() => {
    if (selectedThreadId) {
      loadMessages(selectedThreadId);
    } else {
      setMessages([]);
    }
  }, [selectedThreadId, loadMessages]);

  const handleNewChat = async () => {
    try {
      const newTh = await api.createThread({
        title: t('new_chat'),
        project_id: selectedProjectId,
        model_mode: selectedMode,
      });
      setThreads((prev) => [newTh, ...prev]);
      setSelectedThreadId(newTh.id);
      setIsMobileSidebarOpen(false);
    } catch (err) {
      console.error(err);
    }
  };

  const handleTogglePin = async (th: Thread) => {
    try {
      const updated = await api.updateThread(th.id, { pinned: !th.pinned });
      setThreads((prev) => prev.map((tItem) => (tItem.id === th.id ? updated : tItem)));
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteThread = async (thId: string) => {
    try {
      await api.deleteThread(thId);
      setThreads((prev) => prev.filter((tItem) => tItem.id !== thId));
      if (selectedThreadId === thId) {
        setSelectedThreadId(null);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendMessage = async (content: string, attachments: Attachment[]) => {
    let currentThId = selectedThreadId;
    if (!currentThId) {
      try {
        const newTh = await api.createThread({
          title: content.slice(0, 30) || t('new_chat'),
          project_id: selectedProjectId,
          model_mode: selectedMode,
        });
        setThreads((prev) => [newTh, ...prev]);
        setSelectedThreadId(newTh.id);
        currentThId = newTh.id;
      } catch (err) {
        console.error(err);
        return;
      }
    }

    const tempUserMsg: Message = {
      id: `temp_${Date.now()}`,
      thread_id: currentThId,
      role: 'user',
      content,
      thought: '',
      artifacts: [],
      attachments,
      memory_recalls: [],
      created_at: Math.floor(Date.now() / 1000),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setIsThinking(true);

    try {
      const assistantMsg = await api.sendMessage(currentThId, content, attachments);
      setMessages((prev) => [...prev.filter((m) => m.id !== tempUserMsg.id), tempUserMsg, assistantMsg]);
      if (assistantMsg.artifacts && assistantMsg.artifacts.length > 0) {
        setActiveArtifact(assistantMsg.artifacts[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsThinking(false);
    }
  };

  const currentThread = threads.find((th) => th.id === selectedThreadId) || null;
  const currentProject = projects.find((p) => p.id === (currentThread?.project_id || selectedProjectId)) || null;

  return (
    <div className="@container w-full h-full flex flex-col bg-slate-950 text-slate-100 overflow-hidden font-sans">
      <div className="flex md:hidden items-center justify-between px-3 py-2 bg-slate-900 border-b border-slate-800">
        <button
          type="button"
          onClick={() => setIsMobileSidebarOpen((prev) => !prev)}
          className="p-1.5 rounded-lg bg-slate-800 text-slate-200 text-xs"
        >
          ☰ {t('title')}
        </button>
        {activeArtifact && (
          <button
            type="button"
            onClick={() => setActiveArtifact(null)}
            className="p-1.5 rounded-lg bg-cyan-900/60 text-cyan-300 text-xs"
          >
            ✕ {t('canvas_title')}
          </button>
        )}
      </div>

      <div className="flex-1 flex overflow-hidden relative">
        <div
          className={`${
            isMobileSidebarOpen ? 'flex absolute inset-0 z-30' : 'hidden'
          } md:flex md:static md:z-0`}
        >
          <ProjectSidebar
            projects={projects}
            threads={threads}
            selectedProjectId={selectedProjectId}
            selectedThreadId={selectedThreadId}
            onSelectProject={(pId) => {
              setSelectedProjectId(pId);
              loadThreads(pId);
            }}
            onSelectThread={(tId) => {
              setSelectedThreadId(tId);
              setIsMobileSidebarOpen(false);
            }}
            onNewChat={handleNewChat}
            onNewProject={() => {
              setEditingProject(null);
              setIsProjectModalOpen(true);
            }}
            onEditProject={(p) => {
              setEditingProject(p);
              setIsProjectModalOpen(true);
            }}
            onTogglePin={handleTogglePin}
            onDeleteThread={handleDeleteThread}
            onOpenMemoryHud={() => setIsMemoryHudOpen(true)}
          />
        </div>

        <main className="flex-1 flex flex-col h-full min-w-0">
          <ConversationView
            thread={currentThread}
            project={currentProject}
            messages={messages}
            isThinking={isThinking}
            onOpenArtifact={setActiveArtifact}
          />
          <InputOmnibar
            onSendMessage={handleSendMessage}
            onOpenSmbPicker={() => setIsSmbPickerOpen(true)}
            selectedMode={selectedMode}
            onChangeMode={setSelectedMode}
            disabled={isThinking}
          />
        </main>

        {activeArtifact && (
          <div className="absolute inset-y-0 right-0 z-20 md:static flex">
            <ArtifactCanvas
              artifact={activeArtifact}
              onClose={() => setActiveArtifact(null)}
              defaultSmbFolder={currentProject?.smb_folder || '04 Codice'}
            />
          </div>
        )}
      </div>

      <NewProjectModal
        isOpen={isProjectModalOpen}
        onClose={() => setIsProjectModalOpen(false)}
        initialProject={editingProject}
        onSave={async (data) => {
          await api.createProject(data);
          await loadProjects();
        }}
      />

      <SmbFilePickerModal
        isOpen={isSmbPickerOpen}
        onClose={() => setIsSmbPickerOpen(false)}
        onSelectFile={(att) => {
          handleSendMessage(`[Allegato SMB: ${att.name}]`, [att]);
        }}
      />

      <MemoryInspectorModal
        isOpen={isMemoryHudOpen}
        onClose={() => setIsMemoryHudOpen(false)}
      />
    </div>
  );
};
