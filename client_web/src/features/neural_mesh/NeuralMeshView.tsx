import React, { useCallback, useMemo, useRef, useState } from 'react';
import { MeshLegend } from './components/MeshLegend';
import { EmptyMeshNotice } from './components/EmptyMeshNotice';
import { MeshStatusBar } from './components/MeshStatusBar';
import { NeuronNode } from './components/NeuronNode';
import { NucleusCore } from './components/NucleusCore';
import { SynapseLayer } from './components/SynapseLayer';
import { ParentBindingDialog } from './components/binding/ParentBindingDialog';
import { CoreSummary } from './components/telemetry/CoreSummary';
import { NeuronDetails } from './components/telemetry/NeuronDetails';
import { TelemetryPanel } from './components/telemetry/TelemetryPanel';
import { computeMeshLayout } from './domain/layout';
import { aggregateMesh, cpuRatio, descendantIds, isStale } from './domain/metrics';
import { MeshNeuron, MeshSelection } from './domain/types';
import { NeuralField } from './field/NeuralField';
import { useClock } from './hooks/useClock';
import { useElementSize } from './hooks/useElementSize';
import { DOCKED_PANEL_QUERY, REDUCED_MOTION_QUERY, TOUCH_ONLY_QUERY, useMediaQuery } from './hooks/useMediaQuery';
import { useMeshTopology } from './hooks/useMeshTopology';
import { useMeshI18n } from './i18nScope';
import './neural_mesh.css';

export interface NeuronOpenTarget {
  readonly id: string;
  readonly name: string;
  readonly tier: string;
  readonly ip: string;
}

interface NeuralMeshViewProps {
  readonly onOpenCore: () => void;
  readonly onOpenNeuron: (target: NeuronOpenTarget) => void;
}

const EMPTY: readonly MeshNeuron[] = [];
const PANEL_RESERVE = 384;
const PANEL_HEADING_ID = 'nm-panel-heading';

export const NeuralMeshView: React.FC<NeuralMeshViewProps> = ({ onOpenCore, onOpenNeuron }) => {
  const { t } = useMeshI18n();
  const stageRef = useRef<HTMLDivElement>(null);
  const { width, height } = useElementSize(stageRef);
  const reducedMotion = useMediaQuery(REDUCED_MOTION_QUERY);
  const touchOnly = useMediaQuery(TOUCH_ONLY_QUERY);
  const docked = useMediaQuery(DOCKED_PANEL_QUERY);
  const now = useClock(5000);
  const { snapshot, streamState, applyLocalParent } = useMeshTopology();
  const [selection, setSelection] = useState<MeshSelection | null>(null);
  const [bindingId, setBindingId] = useState<string | null>(null);

  const neurons = snapshot?.neurons ?? EMPTY;
  const byId = useMemo(() => new Map(neurons.map((n) => [n.id, n])), [neurons]);
  const layout = useMemo(
    () => computeMeshLayout({ width, height, insetRight: docked ? PANEL_RESERVE : 0, neurons }),
    [width, height, docked, neurons],
  );
  const aggregate = useMemo(() => aggregateMesh(neurons, now), [neurons, now]);

  const validSelection = selection?.type === 'neuron' && !byId.has(selection.id) ? null : selection;
  const panelSelection: MeshSelection | null = validSelection ?? (docked ? { type: 'core' } : null);
  const activeNeuronId = panelSelection?.type === 'neuron' ? panelSelection.id : null;
  const selectedNeuron = activeNeuronId ? byId.get(activeNeuronId) ?? null : null;
  const bindingNeuron = bindingId ? byId.get(bindingId) ?? null : null;

  const previewNeuron = useCallback((id: string) => setSelection({ type: 'neuron', id }), []);
  const previewCore = useCallback(() => setSelection({ type: 'core' }), []);
  const openNeuron = useCallback(
    (id: string) => {
      const neuron = byId.get(id);
      if (neuron) {
        onOpenNeuron({ id: neuron.id, name: neuron.name, tier: neuron.tier ?? t(`kind_${neuron.kind}`), ip: neuron.ip ?? '' });
      }
    },
    [byId, onOpenNeuron, t],
  );

  const bindingCandidates = useMemo(() => {
    if (!bindingNeuron) {
      return EMPTY;
    }
    const excluded = descendantIds(bindingNeuron.id, neurons);
    return neurons.filter((n) => n.kind === 'compute' && n.id !== bindingNeuron.id && !excluded.has(n.id));
  }, [bindingNeuron, neurons]);

  const counter = t('core_counter', { online: aggregate.online, total: aggregate.total });

  return (
    <section
      ref={stageRef}
      aria-label={t('stage_label')}
      className="nm-stage relative min-h-[28rem] w-full flex-1 select-none overflow-hidden"
      onClick={(event) => event.target === event.currentTarget && setSelection(null)}
    >
      <NeuralField width={width} height={height} layout={layout} reducedMotion={reducedMotion} />
      <div className="nm-vignette pointer-events-none absolute inset-0" aria-hidden="true" />
      <SynapseLayer layout={layout} width={width} height={height} activeId={activeNeuronId} />

      {width > 0 && (
        <NucleusCore
          center={layout.center}
          radius={layout.coreRadius}
          active={panelSelection?.type === 'core'}
          title={t('core_title')}
          subtitle={t('core_subtitle')}
          counter={counter}
          ariaLabel={t('core_aria', { counter })}
          onPreview={previewCore}
          onOpen={onOpenCore}
        />
      )}

      {layout.placed.map((placed) => (
        <NeuronNode
          key={placed.neuron.id}
          placed={placed}
          radius={layout.neuronRadius}
          compact={layout.compact}
          active={placed.neuron.id === activeNeuronId}
          stale={isStale(placed.neuron, now)}
          load={cpuRatio(placed.neuron)}
          kindLabel={t(`kind_${placed.neuron.kind}`)}
          ariaLabel={t('neuron_aria', { name: placed.neuron.name, kind: t(`kind_${placed.neuron.kind}`) })}
          onPreview={previewNeuron}
          onOpen={openNeuron}
        />
      ))}

      <MeshStatusBar streamState={streamState} online={aggregate.online} total={aggregate.total} touchOnly={touchOnly} />
      {!docked && !panelSelection && <MeshLegend />}
      {neurons.length === 0 && <EmptyMeshNotice loading={snapshot === null} />}

      {panelSelection && (
        <TelemetryPanel docked={docked} closeLabel={t('action_close')} labelledBy={PANEL_HEADING_ID} onClose={() => setSelection(null)}>
          {selectedNeuron ? (
            <NeuronDetails
              headingId={PANEL_HEADING_ID}
              neuron={selectedNeuron}
              parentName={(selectedNeuron.parentId && byId.get(selectedNeuron.parentId)?.name) || t('core_summary_title')}
              childCount={neurons.filter((n) => n.parentId === selectedNeuron.id).length}
              stale={isStale(selectedNeuron, now)}
              canBind={selectedNeuron.kind !== 'compute' || selectedNeuron.parentId !== null}
              onOpen={() => openNeuron(selectedNeuron.id)}
              onBind={() => setBindingId(selectedNeuron.id)}
            />
          ) : (
            <CoreSummary headingId={PANEL_HEADING_ID} aggregate={aggregate} onOpenCore={onOpenCore} />
          )}
        </TelemetryPanel>
      )}

      {bindingNeuron && (
        <ParentBindingDialog
          neuron={bindingNeuron}
          candidates={bindingCandidates}
          onClose={() => setBindingId(null)}
          onBound={applyLocalParent}
        />
      )}
    </section>
  );
};
