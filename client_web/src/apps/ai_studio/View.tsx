import React, { useState, useEffect, useCallback } from 'react';
import { useStudioI18n } from './scope';
import type { Project, Thread, Message, Artifact, Attachment, ModelMode, Workpiece3DData, FileDiff } from './types';
import * as api from './api';
import { getDefaultVoiceMessages } from './seedData';
import { ProjectSidebar } from './components/ProjectSidebar';
import { ConversationView } from './components/ConversationView';
import { InputOmnibar } from './components/InputOmnibar';
import { ArtifactCanvas } from './components/ArtifactCanvas';
import { SmbFilePickerModal } from './components/SmbFilePickerModal';
import { MemoryInspectorModal } from './components/MemoryInspectorModal';
import { NewProjectModal } from './components/NewProjectModal';
import { Workpiece3DModal } from './components/Workpiece3DModal';
import { FileDiffModal } from './components/FileDiffModal';
import { CommandPalette, type PaletteItem } from './components/CommandPalette';

export const View: React.FC = () => {
  const { t } = useStudioI18n();
  const [projects, setProjects] = useState<Project[]>([]);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>('th_live_voice_port80');
  const [selectedMode, setSelectedMode] = useState<ModelMode>('reasoning');
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);

  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [isSmbPickerOpen, setIsSmbPickerOpen] = useState(false);
  const [isMemoryHudOpen, setIsMemoryHudOpen] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);

  const [is3DModalOpen, setIs3DModalOpen] = useState(false);
  const [selectedWorkpiece3D, setSelectedWorkpiece3D] = useState<Workpiece3DData | null>(null);
  const [isDiffModalOpen, setIsDiffModalOpen] = useState(false);
  const [currentDiffs, setCurrentDiffs] = useState<FileDiff[]>([]);
  const [selectedDiffId, setSelectedDiffId] = useState<string | undefined>(undefined);

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
      const voiceThreadExists = data.some((tItem) => tItem.id === 'th_live_voice_port80');
      let combinedThreads = data;
      if (!voiceThreadExists) {
        const liveVoiceThread: Thread = {
          id: 'th_live_voice_port80',
          project_id: null,
          title: 'Conversazione Vocale (Pagina 80 Live)',
          pinned: true,
          model_mode: 'fast',
          created_at: Math.floor(Date.now() / 1000),
          updated_at: Math.floor(Date.now() / 1000),
          message_count: 2,
        };
        combinedThreads = [liveVoiceThread, ...data];
      }
      setThreads(combinedThreads);
      if (combinedThreads.length > 0 && !selectedThreadId) {
        setSelectedThreadId('th_live_voice_port80');
      }
    } catch (err) {
      console.error(err);
    }
  }, [selectedThreadId]);

  const loadMessages = useCallback(async (thId: string) => {
    try {
      if (thId === 'th_live_voice_port80') {
        const data = await api.fetchMessages(thId).catch(() => []);
        if (data.length === 0) {
          setMessages(getDefaultVoiceMessages());
          return;
        }
        setMessages(data);
        return;
      }
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

  const handleOpen3DViewer = (data?: Workpiece3DData) => {
    setSelectedWorkpiece3D(data || {
      title: 'Lavorazione 3D CAD & Laser CNC',
      format: 'openscad',
      dimensions_mm: [60, 90, 30],
      material: 'PLA / Compensato Laser',
      tolerance_mm: 0.15,
      kerf_mm: 0.14,
    });
    setIs3DModalOpen(true);
  };

  const handleOpenDiff = (diffId?: string, diffs?: FileDiff[]) => {
    if (diffs && diffs.length > 0) {
      setCurrentDiffs(diffs);
      setSelectedDiffId(diffId || diffs[0].id);
      setIsDiffModalOpen(true);
    } else if (currentDiffs.length > 0) {
      setSelectedDiffId(diffId || currentDiffs[0].id);
      setIsDiffModalOpen(true);
    }
  };

  const handleToggleReaction = (msgId: string, emoji: string) => {
    setMessages((prev) =>
      prev.map((m) => {
        if (m.id !== msgId) return m;
        const currentReactions = m.reactions || [];
        const existingIdx = currentReactions.findIndex((r) => r.emoji === emoji);
        if (existingIdx >= 0) {
          const existing = currentReactions[existingIdx];
          const hasUser = existing.authors.includes('user');
          const newAuthors = hasUser ? existing.authors.filter((a) => a !== 'user') : [...existing.authors, 'user'];
          const newCount = hasUser ? existing.count - 1 : existing.count + 1;
          if (newCount <= 0) {
            return { ...m, reactions: currentReactions.filter((_, i) => i !== existingIdx) };
          }
          const updated = [...currentReactions];
          updated[existingIdx] = { ...existing, count: newCount, authors: newAuthors };
          return { ...m, reactions: updated };
        } else {
          return {
            ...m,
            reactions: [...currentReactions, { emoji, count: 1, authors: ['user'] }],
          };
        }
      })
    );
  };

  const handleVotePoll = (msgId: string, pollId: string, optionId: string, stepIndex?: number) => {
    setMessages((prev) =>
      prev.map((m) => {
        if (m.id !== msgId || !m.poll || m.poll.id !== pollId) return m;
        const p = m.poll;
        if (stepIndex !== undefined && p.steps && p.steps[stepIndex]) {
          const newSteps = [...p.steps];
          const targetStep = newSteps[stepIndex];
          newSteps[stepIndex] = {
            ...targetStep,
            userVotedId: optionId,
            options: targetStep.options.map((opt) =>
              opt.id === optionId ? { ...opt, votes: opt.votes + 1 } : opt
            ),
          };
          return { ...m, poll: { ...p, steps: newSteps } };
        }
        return {
          ...m,
          poll: {
            ...p,
            userVotedId: optionId,
            options: p.options.map((opt) => (opt.id === optionId ? { ...opt, votes: opt.votes + 1 } : opt)),
          },
        };
      })
    );
  };

  const handleSubmitSurvey = (msgId: string, pollId: string, answers: Record<string, string>) => {
    handleSendMessage(`[Sondaggio Requisiti Completato]: ${JSON.stringify(answers)}`, []);
  };

  const handlePartialEdit = (artifactTitle: string, startLine: number, endLine: number, instructions: string) => {
    handleSendMessage(`[Modifica Parziale: "${artifactTitle}" (Righe ${startLine}-${endLine})]: ${instructions}`, []);
  };

  const handleNewChat = async () => {
    try {
      const newTh = await api.createThread({
        title: t('new_chat'),
        project_id: selectedProjectId,
        model_mode: selectedMode,
      });
      setThreads((prev) => [prev[0], newTh, ...prev.slice(1)]);
      setSelectedThreadId(newTh.id);
      setIsMobileSidebarOpen(false);
    } catch (err) {
      console.error(err);
    }
  };

  const handleTogglePin = async (th: Thread) => {
    if (th.id === 'th_live_voice_port80') return;
    try {
      const updated = await api.updateThread(th.id, { pinned: !th.pinned });
      setThreads((prev) => prev.map((tItem) => (tItem.id === th.id ? updated : tItem)));
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteThread = async (thId: string) => {
    if (thId === 'th_live_voice_port80') return;
    try {
      await api.deleteThread(thId);
      setThreads((prev) => prev.filter((tItem) => tItem.id !== thId));
      if (selectedThreadId === thId) {
        setSelectedThreadId('th_live_voice_port80');
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
        setThreads((prev) => [prev[0], newTh, ...prev.slice(1)]);
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
            onOpen3DViewer={handleOpen3DViewer}
          />
        </div>

        <main className="flex-1 flex flex-col h-full min-w-0">
          <ConversationView
            thread={currentThread}
            project={currentProject}
            messages={messages}
            isThinking={isThinking}
            onOpenArtifact={setActiveArtifact}
            onOpen3DViewer={handleOpen3DViewer}
            onOpenDiff={handleOpenDiff}
            onQuickPrompt={(prompt) => handleSendMessage(prompt, [])}
            onToggleReaction={handleToggleReaction}
            onVotePoll={handleVotePoll}
            onSubmitSurvey={handleSubmitSurvey}
            onFeedback={(msgId, type) => {
              setMessages((prev) => prev.map((m) => (m.id === msgId ? { ...m, feedback: type } : m)));
            }}
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
              onPartialEdit={handlePartialEdit}
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

      <Workpiece3DModal
        isOpen={is3DModalOpen}
        onClose={() => setIs3DModalOpen(false)}
        workpiece={selectedWorkpiece3D}
      />

      <FileDiffModal
        isOpen={isDiffModalOpen}
        onClose={() => setIsDiffModalOpen(false)}
        diffs={currentDiffs}
        initialDiffId={selectedDiffId}
      />
    </div>
  );
};
