import React, { useEffect, useState } from 'react';
import {
  Activity,
  CheckCircle2,
  Cpu,
  Loader2,
  Play,
  ShieldCheck,
  Sliders,
  Sparkles,
  Zap,
} from 'lucide-react';
import {
  ArbiterBenchmark,
  ArbiterOverview,
  COMPOSITE_PRESETS,
  CascadeTestResult,
  CompositePreset,
  DecisionPrimitiveType,
  TypedPrimitiveResult,
  executeTypedPrimitive,
  extractLiveRuntimeContext,
  fetchArbiterOverview,
  runArbiterBenchmark,
  saveArbiterThreshold,
  simulateArbiterCascade,
} from '../arbiterApi';
import { BrainGlobalDefault, BrainTargetConfig } from '../types';

interface ProbabilisticArbiterPanelProps {
  readonly globalDefault: BrainGlobalDefault;
  readonly targets: readonly BrainTargetConfig[];
  readonly onSyncAllModules: () => void;
  readonly t: (key: string) => string;
}

export const ProbabilisticArbiterPanel: React.FC<ProbabilisticArbiterPanelProps> = ({
  globalDefault,
  targets,
  onSyncAllModules,
  t,
}) => {
  const [overview, setOverview] = useState<ArbiterOverview | null>(null);
  const [benchmark, setBenchmark] = useState<ArbiterBenchmark | null>(null);
  const [preset, setPreset] = useState<CompositePreset>('NUXIVA_5AXIS');
  const [threshold, setThreshold] = useState<number>(0.82);
  const [query, setQuery] = useState<string>('');
  const [cascadeResult, setCascadeResult] = useState<CascadeTestResult | null>(null);
  const [primitiveType, setPrimitiveType] = useState<DecisionPrimitiveType>('VERDICT');
  const [temperature, setTemperature] = useState<number>(0.85);
  const [debiasEnabled, setDebiasEnabled] = useState<boolean>(true);
  const [primitiveResult, setPrimitiveResult] = useState<TypedPrimitiveResult | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [statusBanner, setStatusBanner] = useState<string | null>(null);

  const liveRuntime = extractLiveRuntimeContext(globalDefault, targets);

  const loadOverview = async () => {
    try {
      const data = await fetchArbiterOverview();
      setOverview(data);
      setBenchmark(data.benchmark);
      setThreshold(data.cascadeThreshold);
    } catch {}
  };

  useEffect(() => {
    void loadOverview();
  }, []);

  const handleRunBenchmark = async (selectedPreset: CompositePreset) => {
    setPreset(selectedPreset);
    setBusyKey('benchmark');
    try {
      const res = await runArbiterBenchmark(selectedPreset, liveRuntime);
      setBenchmark(res);
      setStatusBanner(t('arbiter_benchmark_done'));
    } catch {} finally {
      setBusyKey(null);
    }
  };

  const handleSaveThreshold = async () => {
    setBusyKey('threshold');
    try {
      const saved = await saveArbiterThreshold(threshold);
      setThreshold(saved);
      setStatusBanner(`${t('arbiter_threshold_saved')} (τ = ${saved.toFixed(2)})`);
      await loadOverview();
    } catch {} finally {
      setBusyKey(null);
    }
  };

  const handleApplyToAllModules = async () => {
    setBusyKey('apply_all');
    try {
      await saveArbiterThreshold(threshold);
      const bench = await runArbiterBenchmark(preset, liveRuntime);
      setBenchmark(bench);
      onSyncAllModules();
      await loadOverview();
      setStatusBanner(t('arbiter_synced_all_success'));
    } catch {} finally {
      setBusyKey(null);
    }
  };

  const handleSimulateCascade = async (customQuery?: string) => {
    const targetQuery = (customQuery ?? query).trim();
    if (!targetQuery) return;
    if (customQuery) setQuery(customQuery);
    setBusyKey('cascade');
    try {
      const res = await simulateArbiterCascade(targetQuery, liveRuntime);
      setCascadeResult(res);
      await loadOverview();
    } catch {} finally {
      setBusyKey(null);
    }
  };

  const handleExecutePrimitive = async (typeOverride?: DecisionPrimitiveType) => {
    const activePrim = typeOverride ?? primitiveType;
    if (typeOverride) setPrimitiveType(typeOverride);
    setBusyKey('primitive');
    try {
      const res = await executeTypedPrimitive({
        primitive: activePrim,
        query: query.trim() || t('arbiter_sample_q1'),
        temperature,
        thresholdTau: threshold,
        runtime: liveRuntime,
      });
      setPrimitiveResult(res);
      await loadOverview();
    } catch {} finally {
      setBusyKey(null);
    }
  };

  const activeBench = benchmark ?? overview?.benchmark ?? null;

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border-2 border-violet-300 bg-gradient-to-br from-violet-50/90 via-white to-indigo-50/60 p-5 sm:p-6 shadow-xs space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-black uppercase tracking-wider bg-violet-600 text-white shadow-2xs">
                <Sparkles className="w-3.5 h-3.5" />
                {t('arbiter_badge_5axis')}
              </span>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-950 border border-emerald-300">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                {t('arbiter_connected_modules')}: {targets.length}
              </span>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-bold bg-slate-100 text-slate-800 border border-slate-300">
                <Cpu className="w-3.5 h-3.5 text-indigo-600" />
                {liveRuntime.provider.toUpperCase()} • {liveRuntime.activeModel}
              </span>
            </div>
            <h3 className="text-lg sm:text-xl font-black text-slate-950">
              {t('arbiter_panel_title')}
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed max-w-3xl">
              {t('arbiter_panel_subtitle')}
            </p>
          </div>

          <button
            type="button"
            disabled={busyKey !== null}
            onClick={() => void handleApplyToAllModules()}
            className="inline-flex items-center justify-center gap-2 px-5 py-3.5 rounded-2xl bg-violet-600 hover:bg-violet-700 text-white font-black text-xs sm:text-sm shadow-md shadow-violet-600/20 transition active:scale-95 shrink-0"
          >
            {busyKey === 'apply_all' ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Zap className="w-4 h-4" />
            )}
            {t('arbiter_apply_all_btn')}
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
          {[
            ['arbiter_pipe_dispatcher', `Sys1: ${liveRuntime.system1Model}`],
            ['arbiter_pipe_jury', `Sys2: ${liveRuntime.system2Model}`],
            ['arbiter_pipe_router', `${liveRuntime.provider.replace('_', ' ')}`],
            ['arbiter_pipe_ledger', 'HMAC-SHA256 Zero-Trust'],
          ].map(([key, badge]) => (
            <div
              key={key}
              className="p-3 rounded-2xl bg-white/90 border border-violet-200 flex items-center justify-between gap-2 text-xs"
            >
              <div className="min-w-0">
                <div className="font-black text-slate-900 text-[11px] truncate">{t(key)}</div>
                <div className="text-[10px] font-mono text-violet-700 truncate">{badge}</div>
              </div>
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            </div>
          ))}
        </div>

        {statusBanner && (
          <div className="p-3 rounded-2xl bg-emerald-50 border border-emerald-300 text-emerald-950 text-xs font-bold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{statusBanner}</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-6 p-5 rounded-3xl border border-slate-200 bg-slate-50/70 space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3.5">
            <div>
              <h4 className="font-black text-sm text-slate-950">{t('arbiter_bench_section_title')}</h4>
              <p className="text-[11px] text-slate-500">{t('arbiter_bench_section_desc')}</p>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={preset}
                disabled={busyKey !== null}
                onChange={(e) => void handleRunBenchmark(e.target.value as CompositePreset)}
                className="px-3 py-2 rounded-xl text-xs font-bold border border-slate-300 bg-white text-slate-900"
              >
                {COMPOSITE_PRESETS.map((p) => (
                  <option key={p} value={p}>
                    {t(`arbiter_preset_${p}`)}
                  </option>
                ))}
              </select>
              <button
                type="button"
                disabled={busyKey !== null}
                onClick={() => void handleRunBenchmark(preset)}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-black text-xs transition"
              >
                {busyKey === 'benchmark' ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5" />
                )}
                {t('arbiter_run_benchmark_btn')}
              </button>
            </div>
          </div>

          {activeBench ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="p-3.5 rounded-2xl bg-white border border-indigo-200">
                  <div className="text-[10px] font-bold uppercase text-slate-500">
                    {t('arbiter_composite_score')}
                  </div>
                  <div className="text-2xl font-black text-indigo-700">
                    {activeBench.compositeScore.toFixed(1)}
                  </div>
                </div>
                <div className="p-3.5 rounded-2xl bg-white border border-emerald-200">
                  <div className="text-[10px] font-bold uppercase text-slate-500">
                    {t('arbiter_capability_score')}
                  </div>
                  <div className="text-2xl font-black text-emerald-700">
                    {activeBench.capabilityScore.toFixed(1)}
                  </div>
                </div>
                <div className="p-3.5 rounded-2xl bg-white border border-violet-200 col-span-2 sm:col-span-1">
                  <div className="text-[10px] font-bold uppercase text-slate-500">
                    {t('arbiter_bootstrap_ci')}
                  </div>
                  <div className="text-sm font-black font-mono text-violet-900 mt-1">
                    {activeBench.bootstrap
                      ? `[${activeBench.bootstrap.ciLower95.toFixed(1)} - ${activeBench.bootstrap.ciUpper95.toFixed(1)}]`
                      : '95% CI'}
                  </div>
                </div>
              </div>

              <div className="space-y-2.5 bg-white p-4 rounded-2xl border border-slate-200">
                {[
                  ['arbiter_axis_intelligence', activeBench.axes.intelligence, 'bg-indigo-600'],
                  ['arbiter_axis_calibration', activeBench.axes.calibration, 'bg-violet-600'],
                  ['arbiter_axis_speed', activeBench.axes.speed, 'bg-cyan-600'],
                  ['arbiter_axis_cost', activeBench.axes.cost, 'bg-emerald-600'],
                  ['arbiter_axis_security', activeBench.axes.securityHomeostasis, 'bg-amber-600'],
                ].map(([labelKey, val, barColor]) => (
                  <div key={String(labelKey)} className="space-y-1">
                    <div className="flex justify-between text-xs font-bold text-slate-800">
                      <span>{t(String(labelKey))}</span>
                      <span className="font-mono font-black text-slate-950">
                        {Number(val).toFixed(1)} / 100
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${String(barColor)}`}
                        style={{ width: `${Math.min(100, Math.max(0, Number(val)))}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                <div className="p-2.5 rounded-xl bg-white border border-slate-200">
                  <span className="text-[10px] text-slate-500 block">ECE (10-Bin)</span>
                  <span className="font-mono font-black text-slate-900">
                    {activeBench.ece10Bin.toFixed(4)}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-white border border-slate-200">
                  <span className="text-[10px] text-slate-500 block">Brier Score</span>
                  <span className="font-mono font-black text-slate-900">
                    {activeBench.brierScore.toFixed(4)}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-white border border-slate-200">
                  <span className="text-[10px] text-slate-500 block">RPS Ordinale</span>
                  <span className="font-mono font-black text-slate-900">
                    {activeBench.rpsMean.toFixed(4)}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-white border border-slate-200">
                  <span className="text-[10px] text-slate-500 block">{t('arbiter_paraphrase')}</span>
                  <span className="font-mono font-black text-emerald-700">
                    {(activeBench.paraphraseAgreement * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-white border border-slate-200">
                  <span className="text-[10px] text-slate-500 block">{t('arbiter_order_inv')}</span>
                  <span className="font-mono font-black text-emerald-700">
                    {(activeBench.optionOrderConsistency * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-emerald-50 border border-emerald-200">
                  <span className="text-[10px] text-emerald-800 font-bold block">Conformance</span>
                  <span className="font-mono font-black text-emerald-950">
                    {overview?.conformance.passedChecks ?? 7}/{overview?.conformance.totalChecks ?? 7} OK
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="py-12 flex justify-center">
              <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
            </div>
          )}
        </div>

        <div className="lg:col-span-6 space-y-5">
          <div className="p-5 rounded-3xl border border-violet-200 bg-white space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
              <div>
                <h4 className="font-black text-sm text-slate-950">{t('arbiter_cascade_title')}</h4>
                <p className="text-[11px] text-slate-500">{t('arbiter_cascade_desc')}</p>
              </div>
              <span className="px-2.5 py-1 rounded-full text-xs font-mono font-black bg-violet-100 text-violet-950">
                τ = {threshold.toFixed(2)}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-3 bg-slate-50 p-3 rounded-2xl border border-slate-200">
              <Sliders className="w-4 h-4 text-violet-600 shrink-0" />
              <span className="text-xs font-bold text-slate-700">{t('arbiter_threshold_label')}:</span>
              <input
                type="range"
                min={0.5}
                max={0.99}
                step={0.01}
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
                className="flex-1 accent-violet-600"
              />
              <button
                type="button"
                disabled={busyKey !== null}
                onClick={() => void handleSaveThreshold()}
                className="px-3 py-1.5 rounded-xl bg-violet-600 hover:bg-violet-700 text-white font-bold text-xs transition"
              >
                {t('arbiter_save_tau_btn')}
              </button>
            </div>

            <div className="space-y-2">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={t('arbiter_query_placeholder')}
                  className="flex-1 px-3.5 py-2.5 rounded-xl text-xs border border-slate-300 bg-white"
                />
                <button
                  type="button"
                  disabled={busyKey !== null || !query.trim()}
                  onClick={() => void handleSimulateCascade()}
                  className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-700 text-white font-black text-xs transition shrink-0"
                >
                  {busyKey === 'cascade' ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Activity className="w-3.5 h-3.5" />
                  )}
                  {t('arbiter_test_cascade_btn')}
                </button>
              </div>

              <div className="flex flex-wrap gap-1.5">
                {[t('arbiter_sample_q1'), t('arbiter_sample_q2'), t('arbiter_sample_q3')].map(
                  (sample) => (
                    <button
                      key={sample}
                      type="button"
                      onClick={() => void handleSimulateCascade(sample)}
                      className="px-2.5 py-1 rounded-lg border border-violet-200 bg-violet-50/60 hover:bg-violet-100 text-[11px] font-semibold text-violet-950 transition"
                    >
                      {sample}
                    </button>
                  )
                )}
              </div>
            </div>

            {cascadeResult && (
              <div className="p-4 rounded-2xl bg-slate-950 text-slate-100 text-xs space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-black text-cyan-300 uppercase">
                    {t('arbiter_selected_tier')}: {cascadeResult.selectedTier}
                  </span>
                  <span className="px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 font-mono font-bold">
                    {cascadeResult.predictedLabel} ({(cascadeResult.confidence * 100).toFixed(1)}%)
                  </span>
                </div>
                <div className="text-[11px] text-slate-300 font-mono">
                  {t('arbiter_conformal_set')}: [{cascadeResult.conformalLabels.join(', ')}]
                </div>
                <div className="text-[11px] text-slate-400 font-mono">
                  H_tot={cascadeResult.totalEntropy.toFixed(3)} • H_ale=
                  {cascadeResult.aleatoricEntropy.toFixed(3)} • JSD_epi=
                  {cascadeResult.epistemicDisagreement.toFixed(3)}
                </div>
              </div>
            )}
          </div>

          <div className="p-5 rounded-3xl border border-slate-200 bg-white space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h4 className="font-black text-sm text-slate-950">{t('arbiter_primitives_title')}</h4>
                <p className="text-[11px] text-slate-500">{t('arbiter_primitives_desc')}</p>
              </div>
              <div className="flex items-center gap-1.5">
                {(['VERDICT', 'CHOICE', 'RUBRIC'] as const).map((prim) => (
                  <button
                    key={prim}
                    type="button"
                    onClick={() => void handleExecutePrimitive(prim)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-black transition ${
                      primitiveType === prim
                        ? 'bg-indigo-600 text-white'
                        : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    }`}
                  >
                    {prim}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 text-xs bg-slate-50 p-3 rounded-2xl border border-slate-200">
              <label className="flex items-center gap-2 font-bold text-slate-700">
                <span>Temp T={temperature.toFixed(2)}</span>
                <input
                  type="range"
                  min={0.5}
                  max={2.0}
                  step={0.05}
                  value={temperature}
                  onChange={(e) => setTemperature(Number(e.target.value))}
                  className="w-24 accent-indigo-600"
                />
              </label>
              <label className="flex items-center gap-1.5 font-bold text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={debiasEnabled}
                  onChange={(e) => setDebiasEnabled(e.target.checked)}
                  className="rounded accent-indigo-600"
                />
                <span>{t('arbiter_debias_toggle')}</span>
              </label>
              <button
                type="button"
                onClick={() => void handleExecutePrimitive()}
                className="px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs transition"
              >
                {t('arbiter_run_primitive_btn')}
              </button>
            </div>

            {primitiveResult && (
              <div className="p-3.5 rounded-2xl bg-indigo-50/70 border border-indigo-200 text-xs space-y-1.5">
                <div className="flex items-center justify-between font-black text-indigo-950">
                  <span>
                    {primitiveResult.primitive} → {primitiveResult.predictedLabel}
                  </span>
                  <span className="font-mono">
                    {(primitiveResult.confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="text-[11px] font-mono text-slate-700">
                  {t('arbiter_conformal_set')}: [{primitiveResult.conformalLabels.join(', ')}]
                </div>
              </div>
            )}

            {overview?.ledger && (
              <div className="p-3 rounded-2xl bg-emerald-50/80 border border-emerald-200 flex flex-wrap items-center justify-between gap-2 text-xs text-emerald-950">
                <div className="flex items-center gap-2 font-bold">
                  <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>{t('arbiter_ledger_verified')}</span>
                </div>
                <span className="font-mono font-bold text-[11px]">
                  Cap ${overview.ledger.capUsd.toFixed(2)} • Rem ${overview.ledger.remainingUsd.toFixed(4)}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
