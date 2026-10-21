import React, { useEffect, useState } from 'react';
import { Activity, CheckCircle2, Loader2, Play, ShieldCheck, Sliders } from 'lucide-react';
import { Panel } from '../../shared/components/ModuleFrame';
import { ActionHandle, usePolled } from '../../shared/hooks/useAction';
import {
  COMPOSITE_PRESETS,
  CascadeSimulationResult,
  CompositePreset,
  DecisionLabBenchmark,
  fetchDecisionLab,
  runDecisionBenchmark,
  simulateCascadeDecision,
  updateCascadeThreshold,
} from '../data/decisionLabApi';
import { chipButton, fieldClass } from '../scope';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';

interface Props {
  readonly action: ActionHandle;
}

export const DecisionLabTab: React.FC<Props> = ({ action }) => {
  const { t } = useScopedI18n('node_apps/brain/decision_lab');
  const lab = usePolled(fetchDecisionLab, 'node_brain_decision_lab_failed', true, 12000);
  const [preset, setPreset] = useState<CompositePreset>('NUXIVA_5AXIS');
  const [benchmark, setBenchmark] = useState<DecisionLabBenchmark | null>(null);
  const [threshold, setThreshold] = useState<number>(0.82);
  const [query, setQuery] = useState<string>('');
  const [cascadeOut, setCascadeOut] = useState<CascadeSimulationResult | null>(null);

  useEffect(() => {
    if (!lab.data) return;
    if (!benchmark) setBenchmark(lab.data.benchmark);
    setThreshold(lab.data.cascadeThreshold);
  }, [lab.data, benchmark]);

  const executeBenchmark = async (selectedPreset: CompositePreset) => {
    setPreset(selectedPreset);
    const res = await action.run(
      'decision-lab:benchmark',
      () => runDecisionBenchmark(selectedPreset),
      'node_brain_decision_lab_failed'
    );
    if (res) setBenchmark(res);
  };

  const saveThreshold = async () => {
    const saved = await action.run(
      'decision-lab:threshold',
      () => updateCascadeThreshold(threshold),
      'node_brain_decision_lab_failed'
    );
    if (typeof saved === 'number') {
      setThreshold(saved);
      lab.refresh();
    }
  };

  const runSimulation = async () => {
    if (!query.trim()) return;
    const res = await action.run(
      'decision-lab:cascade',
      () => simulateCascadeDecision(query.trim()),
      'node_brain_decision_lab_failed'
    );
    if (res) {
      setCascadeOut(res);
      lab.refresh();
    }
  };

  const busy = action.busy !== null;
  const activeBench = benchmark ?? lab.data?.benchmark ?? null;

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Panel title={t('decision_lab_title')}>
        <p className="mb-4 text-xs text-slate-400">{t('decision_lab_hint')}</p>
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <label className="text-xs font-semibold text-slate-300">{t('preset_label')}</label>
          <select
            value={preset}
            disabled={busy}
            onChange={(e) => void executeBenchmark(e.target.value as CompositePreset)}
            className={`${fieldClass} max-w-xs`}
          >
            {COMPOSITE_PRESETS.map((p) => (
              <option key={p} value={p}>
                {t(`preset_${p}`)}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={busy}
            onClick={() => void executeBenchmark(preset)}
            className={`${chipButton} border-cyan-400/50 bg-cyan-400/10 text-cyan-100`}
          >
            {action.busy === 'decision-lab:benchmark' ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            ) : (
              <Play className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            {t('run_benchmark')}
          </button>
        </div>

        {activeBench ? (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3">
              <div>
                <p className="text-[11px] text-slate-400">{t('composite_score')}</p>
                <p className="text-2xl font-bold text-cyan-300">{activeBench.compositeScore.toFixed(1)}</p>
              </div>
              <div>
                <p className="text-[11px] text-slate-400">{t('capability_score')}</p>
                <p className="text-2xl font-bold text-emerald-300">{activeBench.capabilityScore.toFixed(1)}</p>
              </div>
            </div>
            <div className="space-y-2 text-xs">
              {[
                ['axis_intelligence', activeBench.axes.intelligence],
                ['axis_calibration', activeBench.axes.calibration],
                ['axis_speed', activeBench.axes.speed],
                ['axis_cost', activeBench.axes.cost],
                ['axis_security', activeBench.axes.securityHomeostasis],
              ].map(([labelKey, scoreVal]) => (
                <div key={String(labelKey)} className="space-y-1">
                  <div className="flex justify-between text-slate-300">
                    <span>{t(String(labelKey))}</span>
                    <span className="font-mono font-semibold text-cyan-200">{Number(scoreVal).toFixed(1)}</span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                    <div
                      className="h-full rounded-full bg-cyan-400 transition-all"
                      style={{ width: `${Math.min(100, Math.max(0, Number(scoreVal)))}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <Loader2 className="h-4 w-4 animate-spin text-cyan-300" />
        )}
      </Panel>

      <Panel title={t('calibration_panel_title')}>
        {activeBench ? (
          <div className="space-y-2 text-xs text-slate-300">
            <p>{t('metric_ece', { val: activeBench.ece10Bin.toFixed(4) })}</p>
            <p>{t('metric_brier', { val: activeBench.brierScore.toFixed(4) })}</p>
            <p>{t('metric_rps', { val: activeBench.rpsMean.toFixed(4) })}</p>
            <p>{t('metric_paraphrase', { val: (activeBench.paraphraseAgreement * 100).toFixed(1) })}</p>
            <p>{t('metric_order', { val: (activeBench.optionOrderConsistency * 100).toFixed(1) })}</p>
            {activeBench.bootstrap && (
              <p className="text-cyan-200">
                {t('metric_bootstrap', {
                  low: activeBench.bootstrap.ciLower95.toFixed(1),
                  high: activeBench.bootstrap.ciUpper95.toFixed(1),
                })}
              </p>
            )}
            {lab.data?.conformance && (
              <div className="mt-3 flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-2.5 text-emerald-200">
                <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span className="break-all text-[11px]">
                  {t('conformance_status', {
                    passed: lab.data.conformance.passedChecks,
                    total: lab.data.conformance.totalChecks,
                    hash: lab.data.conformance.datasetHash.slice(0, 19),
                  })}
                </span>
              </div>
            )}
          </div>
        ) : null}
      </Panel>

      <Panel title={t('cascade_panel_title')}>
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-xs text-slate-300">
              {t('cascade_threshold_label', { val: threshold.toFixed(2) })}
            </label>
            <input
              type="range"
              min={0.5}
              max={0.99}
              step={0.01}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="accent-cyan-400"
            />
            <button
              type="button"
              disabled={busy}
              onClick={() => void saveThreshold()}
              className={`${chipButton} border-slate-700 text-slate-200`}
            >
              <Sliders className="h-3.5 w-3.5" aria-hidden="true" />
              {t('cascade_save_threshold')}
            </button>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('cascade_query_placeholder')}
              className={fieldClass}
            />
            <button
              type="button"
              disabled={busy || !query.trim()}
              onClick={() => void runSimulation()}
              className={`${chipButton} shrink-0 border-cyan-400/50 bg-cyan-400/10 text-cyan-100`}
            >
              <Activity className="h-3.5 w-3.5" aria-hidden="true" />
              {t('cascade_test_button')}
            </button>
          </div>
          {cascadeOut && (
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-xs text-slate-200 space-y-1">
              <p className="font-semibold text-cyan-200">
                {t('cascade_tier_used', { tier: cascadeOut.selectedTier })}
              </p>
              <p>
                {t('cascade_predicted', {
                  label: cascadeOut.predictedLabel,
                  conf: (cascadeOut.confidence * 100).toFixed(1),
                })}
              </p>
              <p className="text-slate-400">
                {t('cascade_conformal', { items: cascadeOut.conformalLabels.join(', ') })}
              </p>
            </div>
          )}
        </div>
      </Panel>

      <Panel title={t('ledger_panel_title')}>
        {lab.data?.ledger && (
          <div className="space-y-2 text-xs text-slate-300">
            <p>
              {t('ledger_cap', {
                cap: lab.data.ledger.capUsd.toFixed(2),
                committed: lab.data.ledger.committedUsd.toFixed(4),
                remaining: lab.data.ledger.remainingUsd.toFixed(4),
              })}
            </p>
            <div className="flex items-center gap-2 text-emerald-300">
              <ShieldCheck className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span>
                {lab.data.ledger.chainIntegrityVerified
                  ? t('ledger_integrity_ok')
                  : t('ledger_integrity_fail')}
              </span>
            </div>
          </div>
        )}
      </Panel>
    </div>
  );
};
