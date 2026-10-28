import React, { useCallback, useEffect, useState } from 'react';
import {
  AbstractionTierName,
  ActiveInferenceStepResult,
  ColumnResolution,
  EmbodiedCortexOverview,
} from './types';
import {
  fetchEmbodiedCortexOverview,
  solveCorticalQuadratic,
  stepHumanoidActiveInference,
} from './embodiedCortexApi';
import { CorticalColumnsSection } from './CorticalColumnsSection';
import { HumanoidEmbodimentSection } from './HumanoidEmbodimentSection';
import { AlertTriangle, BrainCircuit, RefreshCw } from 'lucide-react';

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
                {overview.metrics.cortical_maturity_pct}%
              </span>
            </div>
            <div className="px-4 py-2 rounded-2xl bg-white border border-teal-200 shadow-2xs">
              <span className="text-[10px] font-bold uppercase text-slate-400 block">
                {t('metric_embodied_grounding')}
              </span>
              <span className="text-sm font-black text-teal-950">
                {overview.metrics.embodied_grounding_pct}%
              </span>
            </div>
            <div className="px-4 py-2 rounded-2xl bg-indigo-600 text-white shadow-xs">
              <span className="text-[10px] font-bold uppercase text-indigo-200 block">
                {t('metric_human_parity_index')}
              </span>
              <span className="text-sm font-black">
                {overview.metrics.estimated_human_logic_pct}%
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
