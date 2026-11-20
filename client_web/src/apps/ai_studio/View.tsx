import React, { useState, useEffect, useCallback } from 'react';
import { useStudioI18n } from './scope';
import type { Project, Thread, Message, Artifact, Attachment, ModelMode, Workpiece3DData, FileDiff, AgentAction } from './types';
import * as api from './api';
import { ProjectSidebar } from './components/ProjectSidebar';
import { ConversationView } from './components/ConversationView';
import { InputOmnibar } from './components/InputOmnibar';
import { ArtifactCanvas } from './components/ArtifactCanvas';
import { SmbFilePickerModal } from './components/SmbFilePickerModal';
import { MemoryInspectorModal } from './components/MemoryInspectorModal';
import { NewProjectModal } from './components/NewProjectModal';
import { Workpiece3DModal } from './components/Workpiece3DModal';
import { FileDiffModal } from './components/FileDiffModal';


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
          const defaultVoiceMessages: Message[] = [
            {
              id: 'voice_msg_1',
              thread_id: 'th_live_voice_port80',
              role: 'user',
              content: 'Ciao Nuxiva, verifica lo stato dei sensori e la lavorazione del pezzo 3D per la stampa.',
              thought: '',
              artifacts: [],
              attachments: [],
              memory_recalls: [{
                id: 'mem_v1',
                source: 'voice_speech',
                content: 'Voce utente acquisita in duplex sulla porta 80',
                speaker: 'Utente',
                timestamp: Math.floor(Date.now() / 1000) - 30,
                tags: ['voce', 'sensori', '3d'],
              }],
              created_at: Math.floor(Date.now() / 1000) - 30,
            },
            {
              id: 'voice_msg_2',
              thread_id: 'th_live_voice_port80',
              role: 'assistant',
              content: 'Sensori a regime. Ho preparato il pezzo 3D parametrico con tolleranza meccanica di 0.15mm e compensazione kerf. Puoi aprire la visualizzazione della lavorazione 3D direttamente nella finestra WebGL.',
              thought: 'Trascrizione risposta audio duplex con modulo parametrico collegato e calcolo tolleranze.',
              thinking_duration: '6m 36s',
              actions: [
                { id: 'act_1', kind: 'wait', label: 'Wait 6 seconds finished' },
                { id: 'act_2', kind: 'command', label: 'Check gh run list', detail: 'gh run list -L 6' },
                { id: 'act_3', kind: 'command', label: 'Check run 44790863567', detail: 'Check CI run logs' },
                { id: 'act_4', kind: 'task', label: 'Checked task Check run 44790863567' },
                { id: 'act_5', kind: 'command', label: 'Check run 44790863567 finished' },
                { id: 'act_6', kind: 'analyze', ext: 'ts', target: 'types.ts', lines: '#L30-73' },
                { id: 'act_7', kind: 'edit', ext: 'ts', target: 'types.ts', added: 14, removed: 1, diff_id: 'd_types' },
                { id: 'act_8', kind: 'edit', ext: 'tsx', target: 'Workpiece3DModal.tsx', added: 312, removed: 0, diff_id: 'd_workpiece' },
                { id: 'act_9', kind: 'analyze', ext: 'tsx', target: 'ProjectSidebar.tsx', lines: '#L105-170' },
                { id: 'act_10', kind: 'analyze', ext: 'tsx', target: 'ProjectSidebar.tsx', lines: '#L1-50' },
                { id: 'act_11', kind: 'edit', ext: 'tsx', target: 'ProjectSidebar.tsx', added: 77, removed: 5, diff_id: 'd_sidebar' },
                { id: 'act_12', kind: 'edit', ext: 'tsx', target: 'ConversationView.tsx', added: 187, removed: 9, diff_id: 'd_conv' },
                { id: 'act_13', kind: 'analyze', ext: 'tsx', target: 'View.tsx', lines: '#L10-60' },
                { id: 'act_14', kind: 'think', label: 'Thinking', duration: '13s' },
              ],
              diffs: [
                {
                  id: 'd_types',
                  filename: 'types.ts',
                  ext: 'ts',
                  added: 14,
                  removed: 1,
                  before_content: 'export interface Message {\n  id: string;\n  content: string;\n  thought: string;\n}',
                  after_content: 'export interface Message {\n  id: string;\n  content: string;\n  thought: string;\n  thinking_duration?: string;\n  actions?: AgentAction[];\n  diffs?: FileDiff[];\n  audio_url?: string;\n  feedback?: "positive" | "negative" | null;\n}',
                },
                {
                  id: 'd_workpiece',
                  filename: 'Workpiece3DModal.tsx',
                  ext: 'tsx',
                  added: 312,
                  removed: 0,
                  before_content: '// File nuovo creato',
                  after_content: 'import React, { useEffect, useRef, useState } from "react";\nimport * as THREE from "three";\nexport const Workpiece3DModal = () => { /* WebGL 3D CAD viewer */ };',
                },
                {
                  id: 'd_sidebar',
                  filename: 'ProjectSidebar.tsx',
                  ext: 'tsx',
                  added: 77,
                  removed: 5,
                  before_content: '// Project sidebar senza pin duplex',
                  after_content: '// Project sidebar con pinned live voice duplex card (Pagina 80 Live)',
                },
              ],
              artifacts: [{
                id: 'art_voice_3d',
                identifier: 'cad_workpiece_preview',
                title: 'Pezzo Meccanico 3D (CAD Parametrico)',
                kind: '3d',
                language: 'openscad',
                content: '$fn=40;\ndifference() {\n  cube([60,90,30], center=true);\n  cylinder(h=35, r=12, center=true);\n}',
              }],
              attachments: [],
              memory_recalls: [],
              created_at: Math.floor(Date.now() / 1000) - 25,
            },

          ];
          setMessages(defaultVoiceMessages);
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

  const handleQuickPrompt = (prompt: string) => {
    handleSendMessage(prompt, []);
  };

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
            onQuickPrompt={handleQuickPrompt}
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

