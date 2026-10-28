import React, { useCallback, useEffect, useState } from 'react';
import {
  AbstractionTierName,
  ActiveInferenceStepResult,
  ColumnResolution,
  EmbodiedCortexOverview,
} from './types';
import {
  fetchEmbodiedCortexOverview,
  resolveEpistemicConfrontation,
  solveCorticalQuadratic,
  stepHumanoidActiveInference,
  synthesizeOntologicalFormalism,
} from './embodiedCortexApi';
import { CorticalColumnsSection } from './CorticalColumnsSection';
import { EpistemicConfrontationSection } from './EpistemicConfrontationSection';
import { OntologicalCreativitySection } from './OntologicalCreativitySection';
import { HumanoidEmbodimentSection } from './HumanoidEmbodimentSection';
import { AlertTriangle, BrainCircuit, Cpu, RefreshCw, ShieldCheck } from 'lucide-react';

interface EmbodiedCortexPanelProps {
  readonly t: (key: string) => string;
}

export const EmbodiedCortexPanel: React.FC<EmbodiedCortexPanelProps> = ({ t }) => {
  const [overview, setOverview] = useState<EmbodiedCortexOverview | null>(null);
  const [lastResolution, setLastResolution] = useState<ColumnResolution | null>(null);
  const [lastStep, setLastStep] = useState<ActiveInferenceStepResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadOverview = useCallback(async () => {
    setBusy(true);
    setErrorMessage(null);
    try {
      const data = await fetchEmbodiedCortexOverview();
      setOverview(data);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('persist_failed'));
    } finally {
      setBusy(false);
    }
  }, [t]);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  const handleSolve = async (payload: {
    columnId: string;
    a: number;
    b: number;
    c: number;
    tier: AbstractionTierName | null;
  }) => {
    setBusy(true);
    setErrorMessage(null);
    try {
      const res = await solveCorticalQuadratic(payload);
      setLastResolution(res);
      const updated = await fetchEmbodiedCortexOverview();
      setOverview(updated);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('persist_failed'));
    } finally {
      setBusy(false);
    }
  };

  const handleStepInference = async (payload: {
    jointId: string;
    targetAngleRad: number;
    feedforwardTorqueNm: number;
    dtSec: number;
    measuredLoadKg: number;
  }) => {
    setBusy(true);
    setErrorMessage(null);
    try {
      const step = await stepHumanoidActiveInference(payload);
      setLastStep(step);
      const updated = await fetchEmbodiedCortexOverview();
      setOverview(updated);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('persist_failed'));
    } finally {
      setBusy(false);
    }
  };

  const handleResolveConfrontation = async (
    id: string,
    choiceId: string,
    justification: string
  ) => {
    setBusy(true);
    setErrorMessage(null);
    try {
      await resolveEpistemicConfrontation({ id, choiceId, justification });
      const updated = await fetchEmbodiedCortexOverview();
      setOverview(updated);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('persist_failed'));
    } finally {
      setBusy(false);
    }
  };

  const handleSynthesizeFormalism = async (
    id: string,
    paradigm: string,
    observations: number[][]
  ) => {
    setBusy(true);
    setErrorMessage(null);
    try {
      await synthesizeOntologicalFormalism({ id, paradigm, observations });
      const updated = await fetchEmbodiedCortexOverview();
      setOverview(updated);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('persist_failed'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-indigo-200 bg-gradient-to-r from-indigo-50/80 via-white to-teal-50/70 p-5 sm:p-6 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <BrainCircuit className="w-5 h-5 text-indigo-700" />
            <h3 className="text-lg font-black text-slate-950">
              {t('embodied_cortex_banner_title')}
            </h3>
          </div>
          <p className="text-xs font-medium text-slate-600">
            {t('embodied_cortex_banner_desc')}
          </p>
        </div>

        {overview && (
          <div className="flex flex-wrap items-center gap-3">
            <div className="px-4 py-2 rounded-2xl bg-white border border-indigo-200 shadow-2xs">
              <span className="text-[10px] font-bold uppercase text-slate-400 block">
                {t('metric_cortical_maturity')}
              </span>
              <span className="text-sm font-black text-indigo-950">
                {overview.human_parity_metrics.current_level_percentage}%
              </span>
            </div>
            <div className="px-4 py-2 rounded-2xl bg-white border border-teal-200 shadow-2xs">
              <span className="text-[10px] font-bold uppercase text-slate-400 block">
                {t('humanoid_34dof_badge')}
              </span>
              <span className="text-sm font-black text-teal-950">
                {overview.physical_embodiment.degrees_of_freedom} DOF
              </span>
            </div>
            <div className="px-4 py-2 rounded-2xl bg-indigo-600 text-white shadow-xs">
              <span className="text-[10px] font-bold uppercase text-indigo-200 block">
                {t('metric_human_parity_index')}
              </span>
              <span className="text-sm font-black">
                {overview.human_parity_metrics.current_level_percentage}%
              </span>
            </div>
            <button
              type="button"
              onClick={() => void loadOverview()}
              className="p-2.5 rounded-2xl border border-slate-300 bg-white hover:bg-slate-100 text-slate-700"
              title={t('os_refresh')}
            >
              <RefreshCw className={`w-4 h-4 ${busy ? 'animate-spin' : ''}`} />
            </button>
          </div>
        )}
      </div>

      {overview && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-4 rounded-2xl bg-slate-900 text-white border border-slate-800 space-y-1">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-400">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              {t('human_parity_stat_title')}
            </div>
            <p className="text-xs text-slate-300">
              {t('human_parity_stat_desc')}
            </p>
          </div>
          <div className="p-4 rounded-2xl bg-white border border-slate-200 space-y-1">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
              <Cpu className="w-4 h-4 text-teal-600" />
              {t('fieldbus_ethercat_canopen')}
            </div>
            <p className="text-xs text-slate-600">
              {overview.physical_embodiment.fieldbus_protocol} ({overview.physical_embodiment.supported_bus_modes.join(', ')})
            </p>
          </div>
          <div className="p-4 rounded-2xl bg-white border border-slate-200 space-y-1">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
              <BrainCircuit className="w-4 h-4 text-purple-600" />
              {t('confrontation_certainty_100')}
            </div>
            <p className="text-xs text-slate-600">
              {t('confrontation_resolved_label')}: {overview.confrontation.resolved_count} | {t('confrontation_pending_label')}: {overview.confrontation.pending_count}
            </p>
          </div>
        </div>
      )}

      {errorMessage && (
        <div className="p-4 rounded-2xl border border-rose-300 bg-rose-50 text-rose-950 text-xs font-bold flex items-center gap-2.5">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {overview && (
        <>
          <CorticalColumnsSection
            columns={overview.columns}
            shortcuts={overview.shortcuts}
            lastResolution={lastResolution}
            busy={busy}
            onSolve={handleSolve}
            t={t}
          />
          <EpistemicConfrontationSection
            pending={overview.confrontation.pending}
            resolved={overview.confrontation.resolved}
            onResolve={handleResolveConfrontation}
            busy={busy}
            t={t}
          />
          <OntologicalCreativitySection
            formalisms={overview.ontological_creativity.formalisms}
            onSynthesize={handleSynthesizeFormalism}
            busy={busy}
            t={t}
          />
          <HumanoidEmbodimentSection
            joints={overview.joints}
            imu={overview.imu}
            totalCycles={overview.totalCycles}
            lastStep={lastStep}
            busy={busy}
            onStepInference={handleStepInference}
            t={t}
          />
        </>
      )}
    </div>
  );
};
