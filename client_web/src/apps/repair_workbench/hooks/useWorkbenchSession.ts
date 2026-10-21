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
  const framePending = useRef(false);

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
    setInitialized(false);
    const init = async () => {
      try {
        const [camList, projList] = await Promise.all([
          fetchCamerasList().catch(() => []),
          fetchProjectsList().catch(() => []),
        ]);
        if (!mounted) return;
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
          if (!mounted) return;
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

  const startOrEnsureSession = useCallback(async () => {
    setBusy(true);
    try {
      let projectId = selectedProjectId;
      if (!projectId) {
        const created = await createRepairProject(defaultProjectTitle, defaultProjectTitle);
        projectId = created.project_id;
        setProjects((prev) => [created, ...prev]);
        setSelectedProjectId(projectId);
      }
      const started = await startWorkbenchSession({
        project_id: projectId,
        camera_id: selectedCameraId,
        camera_name: cameraName || defaultBenchName,
        language: lang,
      });
      setSession(started);
      return started;
    } catch (cause: unknown) {
      reportError('repair_workbench_start_failed', cause);
      return null;
    } finally {
      setBusy(false);
    }
  }, [selectedProjectId, selectedCameraId, cameraName, defaultBenchName, defaultProjectTitle, lang]);

  const submitFrame = useCallback(
    async (frameBase64: string, grid: number[]) => {
      if (!session || framePending.current) return;
      framePending.current = true;
      try {
        const res = await analyzeWorkbenchFrame(session.session_id, frameBase64, grid);
        setSession(res.session);
      } catch (cause: unknown) {
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
      setBusy(true);
      try {
        const updated = await teachWorkbenchComponent(session.session_id, trackId, label, value);
        setSession(updated);
      } catch (cause: unknown) {
        reportError('repair_workbench_teach_failed', cause);
      } finally {
        setBusy(false);
      }
    },
    [session]
  );

  const sendChat = useCallback(
    async (message: string, agentId?: string) => {
      if (!session) return;
      setBusy(true);
      try {
        await sendWorkbenchChat(session.session_id, message, agentId);
        const refreshed = await getWorkbenchSession(session.session_id);
        setSession(refreshed);
      } catch (cause: unknown) {
        reportError('repair_workbench_chat_failed', cause);
      } finally {
        setBusy(false);
      }
    },
    [session]
  );

  const escalateSpecialist = useCallback(
    async (requesterId: string, specialty: string, justification: string) => {
      if (!session) return;
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
        setSession(refreshed);
        setProjects(projList);
      } catch (cause: unknown) {
        reportError('repair_workbench_escalate_failed', cause);
      } finally {
        setBusy(false);
      }
    },
    [session, projects]
  );

  return {
    cameras,
    projects,
    selectedCameraId,
    setSelectedCameraId: (id: string) => { setSelectedCameraId(id); setSession(null); },
    cameraName,
    setCameraName,
    selectedProjectId,
    setSelectedProjectId: (id: string) => { setSelectedProjectId(id); setSession(null); },
    session,
    busy,
    initialized,
    startOrEnsureSession,
    submitFrame,
    teachComponent,
    sendChat,
    escalateSpecialist,
  };
}
