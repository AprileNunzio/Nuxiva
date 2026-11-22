import React from 'react';
import type { Project, Workpiece3DData, FileDiff, Attachment } from '../types';
import * as api from '../api';
import { NewProjectModal } from './NewProjectModal';
import { SmbFilePickerModal } from './SmbFilePickerModal';
import { Workpiece3DModal } from './Workpiece3DModal';
import { FileDiffModal } from './FileDiffModal';

interface StudioAuxiliaryModalsProps {
  isProjectModalOpen: boolean;
  setIsProjectModalOpen: (open: boolean) => void;
  editingProject: Project | null;
  loadProjects: () => Promise<void>;
  isSmbPickerOpen: boolean;
  setIsSmbPickerOpen: (open: boolean) => void;
  onSendAttachment: (att: Attachment) => void;
  is3DModalOpen: boolean;
  setIs3DModalOpen: (open: boolean) => void;
  selectedWorkpiece3D: Workpiece3DData | null;
  isDiffModalOpen: boolean;
  setIsDiffModalOpen: (open: boolean) => void;
  currentDiffs: FileDiff[];
  selectedDiffId?: string;
}

export const StudioAuxiliaryModals: React.FC<StudioAuxiliaryModalsProps> = ({
  isProjectModalOpen,
  setIsProjectModalOpen,
  editingProject,
  loadProjects,
  isSmbPickerOpen,
  setIsSmbPickerOpen,
  onSendAttachment,
  is3DModalOpen,
  setIs3DModalOpen,
  selectedWorkpiece3D,
  isDiffModalOpen,
  setIsDiffModalOpen,
  currentDiffs,
  selectedDiffId,
}) => {
  return (
    <>
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
        onSelectFile={onSendAttachment}
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
    </>
  );
};
