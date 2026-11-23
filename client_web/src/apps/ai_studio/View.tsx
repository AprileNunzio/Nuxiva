import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useStudioI18n } from './scope';
import type { Project, Thread, Message, Artifact, Attachment, ModelMode, Workpiece3DData, FileDiff } from './types';
import * as api from './api';
import { VOICE_VIEW_ID } from './voice/constants';
import { VoiceConversationView } from './voice/VoiceConversationView';
import type { VoiceTurn } from './voice/types';
import { ProjectSidebar } from './components/ProjectSidebar';
import { ConversationView } from './components/ConversationView';
import { InputOmnibar } from './components/InputOmnibar';
import { ArtifactCanvas } from './components/ArtifactCanvas';
import { MemoryInspectorModal } from './components/MemoryInspectorModal';
import { StudioAuxiliaryModals } from './components/StudioAuxiliaryModals';
import { ResizeHandle, useResizableWidth } from './components/ResizeHandle';
import { AuroraBackground, ACCENTS } from './components/AuroraBackground';
import { votePoll } from './messageMutations';
import { useMessageMarks } from './useMessageMarks';
import { PresetsModal } from './components/PresetsModal';
import { ModelComparisonModal } from './components/ModelComparisonModal';
import { KnowledgeModal } from './components/KnowledgeModal';
import { downloadMarkdown } from './components/Markdown';
import { StudioNotice } from './components/StudioNotice';
import { CommandPalette, type PaletteItem } from './components/CommandPalette';

export const View: React.FC = () => {
  const { t } = useStudioI18n();
  const [projects, setProjects] = useState<Project[]>([]);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(VOICE_VIEW_ID);
  const [notice, setNotice] = useState<string | null>(null);
  const freshThread = useRef<string | null>(null);
  const [selectedMode, setSelectedMode] = useState<ModelMode>('reasoning');
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);

  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [isSmbPickerOpen, setIsSmbPickerOpen] = useState(false);
  const [isMemoryHudOpen, setIsMemoryHudOpen] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);
  const [isKnowledgeOpen, setIsKnowledgeOpen] = useState(false);
  const [isCompareOpen, setIsCompareOpen] = useState(false);
  const [isPresetsOpen, setIsPresetsOpen] = useState(false);
  const [presets, setPresets] = useState<api.Preset[]>([]);
  const [activePresetId, setActivePresetId] = useState<string | null>(() => localStorage.getItem('ai_studio.preset'));
  const [accent, setAccent] = useState<string>(() => localStorage.getItem('ai_studio.accent') || 'cyan');
  const sidebarW = useResizableWidth('sidebar', 288, 220, 480);
  const canvasW = useResizableWidth('canvas', 580, 360, 900);

  const [is3DModalOpen, setIs3DModalOpen] = useState(false);
  const [selectedWorkpiece3D, setSelectedWorkpiece3D] = useState<Workpiece3DData | null>(null);
  const [isDiffModalOpen, setIsDiffModalOpen] = useState(false);
  const [currentDiffs, setCurrentDiffs] = useState<FileDiff[]>([]);
  const [selectedDiffId, setSelectedDiffId] = useState<string | undefined>(undefined);

  const reportError = useCallback((err: unknown, key: string) => {
    console.error(err);
    const detail = err instanceof Error ? err.message : String(err);
    setNotice(detail.startsWith('brain_unavailable') ? t('err_brain') : `${t(key)}: ${detail}`);
  }, [t]);

  const loadProjects = useCallback(async () => {
    try {
      setProjects(await api.fetchProjects());
    } catch (err) {
      reportError(err, 'err_load');
    }
  }, [reportError]);

  const loadThreads = useCallback(async (projId?: string | null) => {
    try {
      setThreads(await api.fetchThreads(projId));
    } catch (err) {
      reportError(err, 'err_load');
    }
  }, [reportError]);

  const loadMessages = useCallback(async (thId: string) => {
    try {
      setMessages(await api.fetchMessages(thId));
    } catch (err) {
      reportError(err, 'err_load');
    }
  }, [reportError]);

  useEffect(() => {
    loadProjects();
    loadThreads(selectedProjectId);
  }, [loadProjects, loadThreads, selectedProjectId]);

  useEffect(() => {
    if (selectedThreadId && selectedThreadId === freshThread.current) {
      freshThread.current = null;
    } else if (selectedThreadId && selectedThreadId !== VOICE_VIEW_ID) {
      loadMessages(selectedThreadId);
    } else {
      setMessages([]);
    }
  }, [selectedThreadId, loadMessages]);

  const handleOpen3DViewer = (data?: Workpiece3DData) => {
    setSelectedWorkpiece3D(data || {
      title: t('work3d_default'),
      format: 'openscad',
      dimensions_mm: [60, 90, 30],
      material: t('w3d_material_default'),
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

  const marks = useMessageMarks(selectedThreadId === VOICE_VIEW_ID ? null : selectedThreadId, setMessages, (err) => reportError(err, 'err_send'));

  const handleVotePoll = (msgId: string, pollId: string, optionId: string, stepIndex?: number) =>
    setMessages((prev) => votePoll(prev, msgId, pollId, optionId, stepIndex));

  const handleSubmitSurvey = (msgId: string, pollId: string, answers: Record<string, string>) => {
    handleSendMessage(t('prompt_survey', { answers: JSON.stringify(answers) }), []);
  };

  const handlePartialEdit = (artifactTitle: string, startLine: number, endLine: number, instructions: string) => {
    handleSendMessage(t('prompt_partial', { title: artifactTitle, start: startLine, end: endLine, instructions }), []);
  };

  const handleNewChat = async () => {
    try {
      const newTh = await api.createThread({
        title: t('new_chat'),
        project_id: selectedProjectId,
        model_mode: selectedMode,
      });
      setThreads((prev) => [newTh, ...prev]);
      setSelectedThreadId(newTh.id);
      setMessages([]);
      setIsMobileSidebarOpen(false);
    } catch (err) {
      reportError(err, 'err_send');
    }
  };

  const handleTogglePin = async (th: Thread) => {
    try {
      const updated = await api.updateThread(th.id, { pinned: !th.pinned });
      setThreads((prev) => prev.map((tItem) => (tItem.id === th.id ? updated : tItem)));
    } catch (err) { reportError(err, 'err_send'); }
  };

  const handleForkThread = async () => {
    if (!selectedThreadId || selectedThreadId === VOICE_VIEW_ID) return;
    try {
      const forked = await api.forkThread(selectedThreadId);
      setThreads((prev) => [forked, ...prev]);
      setSelectedThreadId(forked.id);
    } catch (err) { reportError(err, 'err_send'); }
  };

  const handleDeleteThread = async (thId: string) => {
    try {
      await api.deleteThread(thId);
      setThreads((prev) => prev.filter((tItem) => tItem.id !== thId));
      if (selectedThreadId === thId) setSelectedThreadId(VOICE_VIEW_ID);
    } catch (err) { reportError(err, 'err_send'); }
  };

  const handleSendMessage = async (content: string, attachments: Attachment[]) => {
    let currentThId = selectedThreadId === VOICE_VIEW_ID ? null : selectedThreadId;
    setNotice(null);
    if (!currentThId) {
      try {
        const newTh = await api.createThread({
          title: content.slice(0, 30) || t('new_chat'),
          project_id: selectedProjectId,
          model_mode: selectedMode,
        });
        setThreads((prev) => [newTh, ...prev]);
        freshThread.current = newTh.id;
        setSelectedThreadId(newTh.id);
        setMessages([]);
        currentThId = newTh.id;
      } catch (err) {
        reportError(err, 'err_send');
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

    const streamingId = `stream_${Date.now()}`;
    const initialAssistant: Message = {
      id: streamingId,
      thread_id: currentThId,
      role: 'assistant',
      content: '',
      thought: '',
      artifacts: [],
      attachments: [],
      memory_recalls: [],
      created_at: Math.floor(Date.now() / 1000),
    };

    setMessages((prev) => [...prev, initialAssistant]);

    try {
      const assistantMsg = await api.streamMessage(
        currentThId,
        content,
        attachments,
        activePresetId,
        selectedMode,
        (token) => {
          setMessages((prev) =>
            prev.map((m) => (m.id === streamingId ? { ...m, content: m.content + token } : m))
          );
        },
        (delta) => {
          setMessages((prev) =>
            prev.map((m) => (m.id === streamingId ? { ...m, thought: (m.thought || '') + delta } : m))
          );
        }
      );
      setMessages((prev) => prev.map((m) => (m.id === streamingId ? assistantMsg : m)));
      if (assistantMsg.artifacts && assistantMsg.artifacts.length > 0) {
        setActiveArtifact(assistantMsg.artifacts[0]);
      }
      void loadThreads(selectedProjectId);
      void loadMessages(currentThId);
    } catch (err) {
      reportError(err, 'err_send');
      setMessages((prev) => prev.filter((m) => m.id !== streamingId));
    } finally {
      setIsThinking(false);
    }
  };

  const isVoiceView = selectedThreadId === VOICE_VIEW_ID;
  const currentThread = threads.find((th) => th.id === selectedThreadId) || null;

  const selectThread = (thId: string) => {
    setSelectedThreadId(thId);
    setNotice(null);
    const th = threads.find((item) => item.id === thId);
    if (th) setSelectedMode(th.model_mode);
    setIsMobileSidebarOpen(false);
  };

  const continueVoiceInChat = (turn: VoiceTurn) => {
    setSelectedThreadId(null);
    setMessages([]);
    void handleSendMessage(turn.said, []);
  };
  const currentProject = projects.find((p) => p.id === (currentThread?.project_id || selectedProjectId)) || null;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsPaletteOpen((o) => !o);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const selectPreset = (id: string | null) => {
    setActivePresetId(id);
    if (id) localStorage.setItem('ai_studio.preset', id);
    else localStorage.removeItem('ai_studio.preset');
  };

  const loadPresets = useCallback(async () => {
    try {
      setPresets(await api.fetchPresets(selectedProjectId));
    } catch (err) {
      console.error(err);
    }
  }, [selectedProjectId]);

  useEffect(() => {
    void loadPresets();
  }, [loadPresets]);

  const handleRegenerate = () => {
    const lastUser = [...messages].reverse().find((m) => m.role === 'user');
    if (lastUser && !isThinking) void handleSendMessage(lastUser.content, lastUser.attachments || []);
  };

  const handleExport = () => {
    if (currentThread) downloadMarkdown(currentThread.title, messages);
  };

  const cycleAccent = () => {
    const keys = Object.keys(ACCENTS);
    const next = keys[(keys.indexOf(accent) + 1) % keys.length];
    localStorage.setItem('ai_studio.accent', next);
    setAccent(next);
  };

  const paletteItems: PaletteItem[] = [
    { id: 'a_new', group: 'actions', label: t('new_chat'), run: handleNewChat },
    { id: 'a_proj', group: 'actions', label: t('new_project'), run: () => { setEditingProject(null); setIsProjectModalOpen(true); } },
    { id: 'a_mem', group: 'actions', label: t('cmd_memory'), run: () => setIsMemoryHudOpen(true) },
    { id: 'a_3d', group: 'actions', label: t('cmd_3d'), run: () => handleOpen3DViewer() },
        { id: 'a_fork', group: 'actions', label: t('cmd_fork'), run: handleForkThread },
    { id: 'a_compare', group: 'actions', label: t('cmd_compare'), run: () => setIsCompareOpen(true) },
    { id: 'a_presets', group: 'actions', label: t('cmd_presets'), run: () => setIsPresetsOpen(true) },
    ...presets.map((p): PaletteItem => ({
      id: `p_${p.id}`,
      group: 'actions',
      label: `${t('cmd_preset_active')}${p.name}`,
      run: () => selectPreset(p.id),
    })),
    { id: 'a_kb', group: 'actions', label: t('cmd_knowledge'), run: () => setIsKnowledgeOpen(true) },
    { id: 'a_regen', group: 'actions', label: t('cmd_regenerate'), run: handleRegenerate },
    { id: 'a_export', group: 'actions', label: t('cmd_export'), run: handleExport },
    { id: 'a_accent', group: 'actions', label: t('cmd_accent'), run: cycleAccent },
    ...messages
      .filter((m) => m.content.trim())
      .map((m): PaletteItem => ({
        id: `m_${m.id}`,
        group: 'chats',
        label: `${t('cmd_msg_prefix')}${m.content.replace(/\s+/g, ' ').slice(0, 80)}`,
        run: () => document.getElementById(`studio-msg-${m.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }),
      })),
    ...threads.map((th): PaletteItem => ({
      id: `t_${th.id}`,
      group: 'chats',
      label: th.title,
      run: () => selectThread(th.id),
    })),
  ];

  return (
    <div className="@container relative w-full h-full flex flex-col bg-slate-950 text-slate-100 overflow-hidden font-sans">
      <AuroraBackground accent={accent} />
      <CommandPalette isOpen={isPaletteOpen} onClose={() => setIsPaletteOpen(false)} items={paletteItems} />
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
          } md:flex md:static md:z-0 md:w-[var(--sw)] md:shrink-0`}
          style={{ ['--sw' as string]: `${sidebarW.width}px` }}
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
            onSelectThread={selectThread}
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

        <ResizeHandle width={sidebarW.width} onChange={sidebarW.setWidth} side="right" label={t('title')} />

        <main className="flex-1 flex flex-col h-full min-w-0">
          <StudioNotice message={notice} onDismiss={() => setNotice(null)} />
          {isVoiceView ? (
            <VoiceConversationView onContinueInChat={continueVoiceInChat} />
          ) : (
            <>
              <ConversationView
                thread={currentThread}
                project={currentProject}
                messages={messages}
                isThinking={isThinking}
                onOpenArtifact={setActiveArtifact}
                onOpen3DViewer={handleOpen3DViewer}
                onOpenDiff={handleOpenDiff}
                onQuickPrompt={(prompt) => handleSendMessage(prompt, [])}
                onRegenerate={handleRegenerate}
                onToggleReaction={marks.react} onVotePoll={handleVotePoll} onSubmitSurvey={handleSubmitSurvey}
                onFeedback={marks.rate}
              />
              <InputOmnibar
                onSendMessage={handleSendMessage}
                onOpenSmbPicker={() => setIsSmbPickerOpen(true)}
                selectedMode={selectedMode}
                onChangeMode={setSelectedMode}
                disabled={isThinking}
              />
            </>
          )}
        </main>

        {activeArtifact && (
          <ResizeHandle width={canvasW.width} onChange={canvasW.setWidth} side="left" label={t('canvas_title')} />
        )}
        {activeArtifact && (
          <div
            className="absolute inset-y-0 right-0 z-20 w-full md:static md:w-[var(--cw)] md:shrink-0 flex"
            style={{ ['--cw' as string]: `${canvasW.width}px` }}
          >
            <ArtifactCanvas
              artifact={activeArtifact}
              onClose={() => setActiveArtifact(null)}
              defaultSmbFolder={currentProject?.smb_folder || '04 Codice'}
              onPartialEdit={handlePartialEdit}
            />
          </div>
        )}
      </div>

      <ModelComparisonModal
        isOpen={isCompareOpen}
        onClose={() => setIsCompareOpen(false)}
        projectId={currentProject?.id || null}
      />

      <PresetsModal
        isOpen={isPresetsOpen} onClose={() => setIsPresetsOpen(false)} projectId={currentProject?.id || null}
        activePresetId={activePresetId} onSelect={selectPreset} onChanged={loadPresets}
      />

      <KnowledgeModal
        isOpen={isKnowledgeOpen}
        onClose={() => setIsKnowledgeOpen(false)}
        projectId={currentProject?.id || null}
        projectName={currentProject?.name}
      />

      <MemoryInspectorModal
        isOpen={isMemoryHudOpen}
        onClose={() => setIsMemoryHudOpen(false)}
      />

      <StudioAuxiliaryModals
        isProjectModalOpen={isProjectModalOpen} setIsProjectModalOpen={setIsProjectModalOpen} editingProject={editingProject} loadProjects={loadProjects}
        isSmbPickerOpen={isSmbPickerOpen} setIsSmbPickerOpen={setIsSmbPickerOpen} onSendAttachment={(att) => handleSendMessage(t('prompt_smb', { name: att.name }), [att])}
        is3DModalOpen={is3DModalOpen} setIs3DModalOpen={setIs3DModalOpen} selectedWorkpiece3D={selectedWorkpiece3D}
        isDiffModalOpen={isDiffModalOpen} setIsDiffModalOpen={setIsDiffModalOpen} currentDiffs={currentDiffs} selectedDiffId={selectedDiffId}
      />
    </div>
  );
};
