import React from 'react';
import type { UpdaterStatus, UpdaterTelemetry } from '../types';
import { ConsolePanel } from './ConsolePanel';
import { ImpactPanel } from './ImpactPanel';
import { IntegrityPanel } from './IntegrityPanel';
import { PipelinePanel } from './PipelinePanel';
import { ReleaseNotesPanel } from './ReleaseNotesPanel';
import { ServicesPanel } from './ServicesPanel';
import { VersionHero } from './VersionHero';

interface OverviewPanelProps {
  readonly status: UpdaterStatus;
  readonly telemetry: UpdaterTelemetry | null;
  readonly applying: boolean;
  readonly unreachable: boolean;
  readonly onStatus: (status: UpdaterStatus) => void;
  readonly onApplying: (fromRev: string | null) => void;
}

export const OverviewPanel: React.FC<OverviewPanelProps> = ({ status, telemetry, applying, unreachable, onStatus, onApplying }) => (
  <div className="flex flex-col gap-6">
    <VersionHero status={status} applying={applying} unreachable={unreachable} onStatus={onStatus} onApplying={onApplying} />
    <ReleaseNotesPanel report={telemetry?.release_notes} compact />
    {telemetry && (
      <div className="upd-overview grid gap-6">
        <div className="flex min-w-0 flex-col gap-6">
          <PipelinePanel run={telemetry.run} stageIds={telemetry.stages} boot={telemetry.boot ?? null} />
          <ConsolePanel lines={telemetry.console} />
        </div>
        <div className="flex min-w-0 flex-col gap-6">
          <IntegrityPanel telemetry={telemetry} />
          <ImpactPanel impact={telemetry.run && !telemetry.run.pipeline?.outcome ? telemetry.run.impact : telemetry.pending.impact ?? telemetry.run?.impact ?? null} />
          <ServicesPanel services={telemetry.services} />
        </div>
      </div>
    )}
  </div>
);
