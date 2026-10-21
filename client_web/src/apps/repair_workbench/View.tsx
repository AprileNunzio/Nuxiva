import React, { useEffect, useRef, useState } from 'react';
import { FolderKanban, Maximize2, Minimize2, Play, Wrench } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { useWorkbenchSession } from './hooks/useWorkbenchSession';
import { ARVideoStage } from './components/ARVideoStage';
import { BoardDossierPanel } from './components/BoardDossierPanel';
import { LiveRepairCoPilot } from './components/LiveRepairCoPilot';
import type { BoardDossier, CircuitSpec } from './types';

interface WorkbenchViewProps {
  readonly initialPayload?: {
    readonly projectId?: string;
    readonly takeover?: boolean;
  };
}

const EMPTY_DOSSIER: BoardDossier = {
  title: '',
  board_kind: '',
  summary: '',
  characteristics: [],
  anomalies: [],
  component_count: 0,
};

const EMPTY_CIRCUIT: CircuitSpec = {
  name: '',
  description: '',
  components: [],
  nets: [],
};

export const View: React.FC<WorkbenchViewProps> = ({ initialPayload }) => {
  const { t, lang } = useScopedI18n('apps/repair_workbench');
  const [immersive, setImmersive] = useState<boolean>(Boolean(initialPayload?.takeover));
  const launchAttempted = useRef(false);

  const {
    cameras,
    projects,
    selectedCameraId,
    setSelectedCameraId,
    cameraName,
    setCameraName,
    selectedProjectId,
    setSelectedProjectId,
    session,
    busy,
    initialized,
    startOrEnsureSession,
    submitFrame,
    teachComponent,
    sendChat,
    escalateSpecialist,
  } = useWorkbenchSession(
    lang,
    t('camera_default_bench'),
    t('project_new_amp'),
    initialPayload?.projectId
  );

  useEffect(() => {
    if (initialPayload?.takeover && initialized && !session && !busy && !launchAttempted.current) {
      launchAttempted.current = true;
      void startOrEnsureSession();
    }
  }, [initialPayload?.takeover, initialized, session, busy, startOrEnsureSession]);

  return (
    <div
      className={
        immersive
          ? 'fixed inset-0 z-[999999] flex h-screen w-screen flex-col gap-3 bg-slate-950 p-3 text-slate-100'
          : 'flex h-full w-full flex-col gap-3 bg-slate-950 p-3 text-slate-100'
      }
    >
      <header className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-slate-800 bg-slate-900/90 px-4 py-2.5 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 font-bold text-white">
            <Wrench className="h-4 w-4 text-cyan-400" aria-hidden="true" />
            <span>{t('title')}</span>
          </div>

          <div className="flex items-center gap-1.5">
            <FolderKanban className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
            <select
              aria-label={t('project_select')}
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 text-xs text-slate-200"
            >
              <option value="">{t('project_new_amp')}</option>
              {projects.map((proj) => (
                <option key={proj.project_id} value={proj.project_id}>
                  {proj.name}
                </option>
              ))}
            </select>
          </div>

          <input
            type="text"
            value={cameraName}
            maxLength={80}
            aria-label={t('camera_default_bench')}
            onChange={(e) => setCameraName(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 text-xs text-cyan-200"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => void startOrEnsureSession()}
            className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3 py-1.5 font-semibold text-white hover:bg-emerald-500 disabled:opacity-40"
          >
            <Play className="h-3.5 w-3.5" aria-hidden="true" />
            {t('start_session')}
          </button>

          <button
            type="button"
            onClick={() => setImmersive((prev) => !prev)}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 px-3 py-1.5 font-medium text-slate-200 hover:bg-slate-700"
          >
            {immersive ? (
              <Minimize2 className="h-3.5 w-3.5" aria-hidden="true" />
            ) : (
              <Maximize2 className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            {t('fullscreen_takeover')}
          </button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 lg:grid-cols-12">
        <div className="min-h-[18rem] lg:col-span-8">
          <ARVideoStage
            t={t}
            cameras={cameras}
            selectedCameraId={selectedCameraId}
            cameraName={cameraName || t('camera_default_bench')}
            sceneState={session?.scene_state || 'warmup'}
            popups={session?.popups || []}
            sessionActive={Boolean(session)}
            busy={busy}
            onSelectCamera={(id, name) => {
              setSelectedCameraId(id);
              setCameraName(name);
            }}
            onFrameCaptured={(b64, grid) => void submitFrame(b64, grid)}
            onTeachComponent={teachComponent}
          />
        </div>

        <div className="min-h-[16rem] lg:col-span-4">
          <BoardDossierPanel
            t={t}
            dossier={session?.dossier || EMPTY_DOSSIER}
            circuit={session?.circuit || EMPTY_CIRCUIT}
            expectedVoltages={session?.expected_voltages || {}}
          />
        </div>
      </div>

      <div className="h-56 shrink-0">
        <LiveRepairCoPilot
          t={t}
          advice={session?.advice || []}
          notes={session?.notes || []}
          sessionActive={Boolean(session)}
          busy={busy}
          assignedAgents={projects.find((project) => project.project_id === session?.project_id)?.assigned_agents || []}
          onSendChat={sendChat}
          onEscalateSpecialist={escalateSpecialist}
        />
      </div>
    </div>
  );
};

export default View;
