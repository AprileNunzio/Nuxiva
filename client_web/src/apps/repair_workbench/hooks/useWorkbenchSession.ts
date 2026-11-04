import { useCallback, useEffect, useRef, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import {
  analyzeWorkbenchFrame,
  createRepairProject,
  escalateWorkbenchSpecialist,
  fetchCamerasList,
  fetchProjectsList,
  getWorkbenchSession,
  sendWorkbenchChat,
  startWorkbenchSession,
  teachWorkbenchComponent,
  resumeRepairProject,
  closeRepairProject,
  fetchRepairProjectFolders,
} from '../api';
import type { CameraSourceItem, ProjectSummaryItem, WorkbenchSession } from '../types';

export function useWorkbenchSession(
  lang: string,
  defaultBenchName: string,
  defaultProjectTitle: string,
  initialProjectId?: string,
  initialSessionId?: string
) {
  const [cameras, setCameras] = useState<CameraSourceItem[]>([]);
  const [projects, setProjects] = useState<ProjectSummaryItem[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string>('local_usb');
  const [cameraName, setCameraName] = useState<string>(defaultBenchName);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(initialProjectId || '');
  const [session, setSession] = useState<WorkbenchSession | null>(null);
  const [busy, setBusy] = useState<boolean>(false);
  const [initialized, setInitialized] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState<'idle' | 'analyzing' | 'error'>('idle');
  const framePending = useRef(false);
  const generation = useRef(0);
  const startPending = useRef<Promise<WorkbenchSession | null> | null>(null);

  useEffect(() => {
    if (!session?.session_id) return;
    const sessionId = session.session_id;
    const currentGeneration = generation.current;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const refreshed = await getWorkbenchSession(sessionId);
        if (!stopped && currentGeneration === generation.current) {
          setSession((previous) => previous?.session_id === sessionId && refreshed.updated_at > previous.updated_at ? refreshed : previous);
        }
      } catch (cause: unknown) {
        if (!stopped) reportError('repair_workbench_refresh_failed', cause);
      }
      if (!stopped) timer = setTimeout(() => void refresh(), 5000);
    };
    timer = setTimeout(() => void refresh(), 5000);
    return () => { stopped = true; clearTimeout(timer); };
  }, [session?.session_id]);

  const resumeProject = useCallback(async (projectId: string) => {
    const currentGeneration = ++generation.current;
    setBusy(true);
    setAnalysisStatus('idle');
    setSession(null);
    setSelectedProjectId(projectId);
    try {
      const restored = await resumeRepairProject(projectId);
      if (currentGeneration !== generation.current) return;
      setSession(restored);
      setSelectedCameraId(restored.camera_id);
      setCameraName(restored.camera_name);
    } catch (cause: unknown) { reportError('repair_workbench_resume_failed', cause); }
    finally { if (currentGeneration === generation.current) setBusy(false); }
  }, []);

  const closeProject = useCallback(async (projectId: string) => {
    const currentGeneration = generation.current;
    setBusy(true);
    try {
      await closeRepairProject(projectId);
      if (currentGeneration === generation.current && selectedProjectId === projectId) {
        generation.current++;
        setSession(null);
        setSelectedProjectId('');
        setAnalysisStatus('idle');
        setBusy(false);
      }
      setProjects((previous) => previous.filter((project) => project.project_id !== projectId));
    } catch (cause: unknown) { reportError('repair_workbench_close_failed', cause); throw cause; }
    finally { if (currentGeneration === generation.current) setBusy(false); }
  }, [selectedProjectId]);

  useEffect(() => {
    const devices = navigator.mediaDevices;
    if (!devices?.enumerateDevices) return;
    let active = true;
    const refresh = async () => {
      try {
        const list = await devices.enumerateDevices();
        if (!active) return;
        const usb = list.filter((d) => d.kind === 'videoinput' && d.deviceId).map((d) => ({
          id: `usb:${d.deviceId}`, name: d.label || defaultBenchName, kind: 'usb',
        }));
        setCameras((previous) => [...previous.filter((d) => !d.id.startsWith('usb:')), ...usb]);
      } catch (cause: unknown) {
        reportError('repair_workbench_devices_failed', cause);
      }
    };
    void refresh();
    devices.addEventListener('devicechange', refresh);
    return () => { active = false; devices.removeEventListener('devicechange', refresh); };
  }, [defaultBenchName]);

  useEffect(() => {
    let mounted = true;
    const currentGeneration = generation.current;
    setInitialized(false);
    const init = async () => {
      try {
        const [camList, projList] = await Promise.all([
          fetchCamerasList().catch(() => []),
          fetchProjectsList().catch(() => []),
        ]);
        if (!mounted || currentGeneration !== generation.current) return;
        setCameras((previous) => [...camList, ...previous.filter((d) => d.id.startsWith('usb:'))]);
        setProjects(projList);
        const preferredCam = camList.find((c) =>
          c.name.toLowerCase().includes('banco') || c.name.toLowerCase().includes('repair')
        );
        if (preferredCam) {
          setSelectedCameraId(preferredCam.id);
          setCameraName(preferredCam.name);
        }
        const targetProjId = initialProjectId || projList[0]?.project_id || '';
        if (targetProjId) {
          setSelectedProjectId(targetProjId);
        }
        if (initialSessionId) {
          const restored = await getWorkbenchSession(initialSessionId);
          if (!mounted || currentGeneration !== generation.current) return;
          setSession(restored);
          setSelectedProjectId(restored.project_id);
          setSelectedCameraId(restored.camera_id);
          setCameraName(restored.camera_name);
        }
      } catch (cause: unknown) {
        reportError('repair_workbench_init_failed', cause);
      } finally {
        if (mounted) setInitialized(true);
      }
    };
    void init();
    return () => {
      mounted = false;
    };
  }, [initialProjectId, initialSessionId]);

  const startOrEnsureSession = useCallback((forceNew = false): Promise<WorkbenchSession | null> => {
    if (session && !forceNew) return Promise.resolve(session);
    if (startPending.current) return startPending.current;
    const currentGeneration = generation.current;
    const operation = (async () => {
    setBusy(true);
    try {
      let projectId = selectedProjectId;
      if (!projectId) {
        const created = await createRepairProject(defaultProjectTitle, defaultProjectTitle);
        if (currentGeneration !== generation.current) return null;
        projectId = created.project_id;
        setProjects((prev) => [created, ...prev]);
        setSelectedProjectId(projectId);
      }
      const folders = !forceNew ? await fetchRepairProjectFolders() : [];
      if (currentGeneration !== generation.current) return null;
      const folder = folders.find((item) => item.project_id === projectId);
      if (folder && ['COMPLETED', 'ARCHIVED', 'CLOSED'].includes(folder.status.toUpperCase())) return null;
      const started = folder?.latest_session_id ? await resumeRepairProject(projectId) : await startWorkbenchSession({
        project_id: projectId,
        camera_id: selectedCameraId,
        camera_name: cameraName || defaultBenchName,
        language: lang,
      });
      if (currentGeneration !== generation.current) return null;
      setSession(started);
      setSelectedCameraId(started.camera_id);
      setCameraName(started.camera_name);
      return started;
    } catch (cause: unknown) {
      reportError('repair_workbench_start_failed', cause);
      return null;
    } finally {
      if (currentGeneration === generation.current) setBusy(false);
    }
    })();
    startPending.current = operation;
    void operation.finally(() => { if (startPending.current === operation) startPending.current = null; });
    return operation;
  }, [session, selectedProjectId, selectedCameraId, cameraName, defaultBenchName, defaultProjectTitle, lang]);

  const submitFrame = useCallback(
    async (frameBase64: string, grid: number[]) => {
      if (!session || framePending.current) return;
      framePending.current = true;
      const currentGeneration = generation.current;
      setAnalysisStatus('analyzing');
      try {
        const res = await analyzeWorkbenchFrame(session.session_id, frameBase64, grid);
        if (currentGeneration === generation.current) {
          setSession(res.session);
          setAnalysisStatus('idle');
        }
      } catch (cause: unknown) {
        if (currentGeneration === generation.current) setAnalysisStatus('error');
        reportError('repair_workbench_frame_failed', cause);
      } finally {
        framePending.current = false;
      }
    },
    [session]
  );

  const teachComponent = useCallback(
    async (trackId: number, label: string, value: string) => {
      if (!session) return;
      const currentGeneration = generation.current;
      setBusy(true);
      try {
        const updated = await teachWorkbenchComponent(session.session_id, trackId, label, value);
        if (currentGeneration === generation.current) setSession(updated);
      } catch (cause: unknown) {
        reportError('repair_workbench_teach_failed', cause);
      } finally {
        if (currentGeneration === generation.current) setBusy(false);
      }
    },
    [session]
  );

  const sendChat = useCallback(
    async (message: string, agentId?: string) => {
      if (!session) return;
      const currentGeneration = generation.current;
      setBusy(true);
      try {
        await sendWorkbenchChat(session.session_id, message, agentId);
        const refreshed = await getWorkbenchSession(session.session_id);
        if (currentGeneration === generation.current) setSession(refreshed);
      } catch (cause: unknown) {
        reportError('repair_workbench_chat_failed', cause);
      } finally {
        if (currentGeneration === generation.current) setBusy(false);
      }
    },
    [session]
  );

  const escalateSpecialist = useCallback(
    async (requesterId: string, specialty: string, justification: string) => {
      if (!session) return;
      const currentGeneration = generation.current;
      setBusy(true);
      try {
        await escalateWorkbenchSpecialist(
          session.session_id,
          requesterId,
          specialty,
          justification
        );
        const [refreshed, projList] = await Promise.all([
          getWorkbenchSession(session.session_id),
          fetchProjectsList().catch(() => projects),
        ]);
        if (currentGeneration === generation.current) {
          setSession(refreshed);
          setProjects(projList);
        }
      } catch (cause: unknown) {
        reportError('repair_workbench_escalate_failed', cause);
      } finally {
        if (currentGeneration === generation.current) setBusy(false);
      }
    },
    [session, projects]
  );

  return {
    cameras,
    projects,
    selectedCameraId,
    setSelectedCameraId: (id: string) => { generation.current++; setBusy(false); setSelectedCameraId(id); setSession(null); setAnalysisStatus('idle'); },
    cameraName,
    setCameraName,
    selectedProjectId,
    setSelectedProjectId: (id: string) => { generation.current++; setBusy(false); setSelectedProjectId(id); setSession(null); setAnalysisStatus('idle'); },
    session,
    busy,
    initialized,
    analysisStatus,
    startOrEnsureSession,
    submitFrame,
    teachComponent,
    sendChat,
    escalateSpecialist,
    resumeProject,
    closeProject,
  };
}
