import React, { useState } from 'react';
import {
  AbstractionTierName,
  ColumnResolution,
  CorticalColumnSpec,
  InvariantShortcut,
} from './types';
import { Cpu, Layers, Play, Zap } from 'lucide-react';

interface CorticalColumnsSectionProps {
  readonly columns: readonly CorticalColumnSpec[];
  readonly shortcuts: readonly InvariantShortcut[];
  readonly lastResolution: ColumnResolution | null;
  readonly busy: boolean;
  readonly onSolve: (payload: {
    columnId: string;
    a: number;
    b: number;
    c: number;
    tier: AbstractionTierName | null;
  }) => Promise<void>;
  readonly t: (key: string) => string;
}

export const CorticalColumnsSection: React.FC<CorticalColumnsSectionProps> = ({
  columns,
  shortcuts,
  lastResolution,
  busy,
  onSolve,
  t,
}) => {
  const [selectedColumn, setSelectedColumn] = useState('col_algebra_sym');
  const [coeffA, setCoeffA] = useState(1);
  const [coeffB, setCoeffB] = useState(-5);
  const [coeffC, setCoeffC] = useState(4);
  const [selectedTier, setSelectedTier] = useState<AbstractionTierName | 'auto'>('auto');

  const handleRun = () => {
    void onSolve({
      columnId: selectedColumn,
      a: coeffA,
      b: coeffB,
      c: coeffC,
      tier: selectedTier === 'auto' ? null : selectedTier,
    });
  };

  const applyPreset = (a: number, b: number, c: number) => {
    setCoeffA(a);
    setCoeffB(b);
    setCoeffC(c);
  };

  return (
    <div className="rounded-3xl border border-indigo-200 bg-white p-5 sm:p-6 shadow-xs space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-indigo-600 text-white">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base sm:text-lg font-black text-slate-950">
              {t('cortical_columns_title')}
            </h3>
            <p className="text-xs text-slate-600 font-medium">
              {t('cortical_columns_subtitle')}
            </p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-indigo-50 text-indigo-900 border border-indigo-200">
          <Cpu className="w-3.5 h-3.5 text-indigo-600" />
          {t('rust_zero_copy_badge')}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {columns.map((col) => (
          <button
            key={col.id}
            type="button"
            onClick={() => setSelectedColumn(col.id)}
            className={`text-left p-4 rounded-2xl border transition ${
              selectedColumn === col.id
                ? 'border-indigo-600 bg-indigo-50/70 shadow-2xs'
                : 'border-slate-200 hover:border-indigo-300 bg-slate-50/50'
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-black text-slate-900 truncate">{col.id}</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase bg-indigo-100 text-indigo-900">
                {t(`tier_${col.preferred_tier}`)}
              </span>
            </div>
            <div className="mt-3 flex items-center justify-between text-[11px] font-bold text-slate-600">
              <span>{t('column_maturity_label')}</span>
              <span className="text-indigo-950 font-black">
                {Math.round(col.maturity_score * 100)}%
              </span>
            </div>
            <div className="mt-1.5 w-full h-1.5 rounded-full bg-slate-200 overflow-hidden">
              <div
                className="h-full bg-indigo-600 rounded-full"
                style={{ width: `${Math.min(100, Math.round(col.maturity_score * 100))}%` }}
              />
            </div>
            <div className="mt-2 flex items-center justify-between text-[10px] font-semibold text-slate-500">
              <span>
                {t('column_runs_label')}: {col.total_executions}
              </span>
              <span>
                {t('column_shortcuts_label')}: {col.shortcuts_consolidated}
              </span>
            </div>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-7 space-y-4 rounded-2xl bg-slate-50 p-4 sm:p-5 border border-slate-200">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-black uppercase tracking-wider text-slate-700">
              {t('algorithm_selector_heading')}
            </span>
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                onClick={() => applyPreset(1, -5, 4)}
                className="px-2.5 py-1 rounded-lg text-[11px] font-bold bg-white border border-slate-300 hover:bg-indigo-50 text-slate-800"
              >
                {t('preset_unit_root')}
              </button>
              <button
                type="button"
                onClick={() => applyPreset(1, 0, -9)}
                className="px-2.5 py-1 rounded-lg text-[11px] font-bold bg-white border border-slate-300 hover:bg-indigo-50 text-slate-800"
              >
                {t('preset_symmetric_dipole')}
              </button>
              <button
                type="button"
                onClick={() => applyPreset(2, -7, 3)}
                className="px-2.5 py-1 rounded-lg text-[11px] font-bold bg-white border border-slate-300 hover:bg-indigo-50 text-slate-800"
              >
                {t('preset_general_quadratic')}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <label className="block space-y-1">
              <span className="text-[11px] font-bold text-slate-600">{t('coeff_a_label')}</span>
              <input
                type="number"
                step="0.5"
                value={coeffA}
                onChange={(e) => setCoeffA(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-black text-slate-900"
              />
            </label>
            <label className="block space-y-1">
              <span className="text-[11px] font-bold text-slate-600">{t('coeff_b_label')}</span>
              <input
                type="number"
                step="0.5"
                value={coeffB}
                onChange={(e) => setCoeffB(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-black text-slate-900"
              />
            </label>
            <label className="block space-y-1">
              <span className="text-[11px] font-bold text-slate-600">{t('coeff_c_label')}</span>
              <input
                type="number"
                step="0.5"
                value={coeffC}
                onChange={(e) => setCoeffC(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-black text-slate-900"
              />
            </label>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {(['auto', 'procedural', 'canonical', 'invariant'] as const).map((tierKey) => (
              <button
                key={tierKey}
                type="button"
                onClick={() => setSelectedTier(tierKey)}
                className={`px-3 py-2 rounded-xl text-xs font-black border transition ${
                  selectedTier === tierKey
                    ? 'bg-indigo-600 text-white border-indigo-700'
                    : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                }`}
              >
                {t(`tier_${tierKey}`)}
              </button>
            ))}
          </div>

          <button
            type="button"
            disabled={busy}
            onClick={handleRun}
            className="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-black text-xs sm:text-sm shadow-sm transition"
          >
            <Play className="w-4 h-4" />
            {t('execute_cortical_solve_btn')}
          </button>
        </div>

        <div className="lg:col-span-5 space-y-4">
          {lastResolution ? (
            <div className="rounded-2xl border-2 border-emerald-200 bg-emerald-50/60 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black uppercase text-emerald-950">
                  {t(`tier_${lastResolution.selected_tier}`)}
                </span>
                <span className="text-xs font-black text-emerald-800">
                  {lastResolution.latency_ms} ms
                </span>
              </div>
              <div className="text-sm font-black text-slate-950">
                {t('roots_output_label')}: [{lastResolution.roots.join(', ')}]
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs font-bold text-slate-700">
                <div className="p-2 rounded-xl bg-white border border-emerald-200">
                  {t('steps_executed_label')}: {lastResolution.steps_executed}
                </div>
                <div className="p-2 rounded-xl bg-white border border-emerald-200 text-emerald-900">
                  {t('steps_saved_label')}: {lastResolution.steps_saved}
                </div>
              </div>
              {lastResolution.invariant_applied && (
                <div className="flex items-center gap-1.5 text-xs font-black text-indigo-900 bg-indigo-100/80 px-3 py-1.5 rounded-xl">
                  <Zap className="w-3.5 h-3.5 text-indigo-700 shrink-0" />
                  <span>
                    {t('invariant_applied_label')}: {lastResolution.invariant_applied}
                  </span>
                </div>
              )}
              <div className="space-y-1">
                {lastResolution.trace_keys.map((tk) => (
                  <div key={tk} className="text-[11px] font-semibold text-slate-600">
                    • {t(tk)}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs font-semibold text-slate-500">
              {t('no_resolution_yet')}
            </div>
          )}

          <div className="rounded-2xl border border-slate-200 bg-white p-4 space-y-2">
            <div className="text-xs font-black uppercase text-slate-700">
              {t('consolidated_shortcuts_heading')} ({shortcuts.length})
            </div>
            <div className="space-y-1.5 max-h-36 overflow-y-auto">
              {shortcuts.map((sc) => (
                <div
                  key={sc.id}
                  className="flex items-center justify-between text-xs px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200"
                >
                  <span className="font-bold text-slate-800 truncate">{sc.pattern_signature}</span>
                  <span className="font-black text-indigo-700">
                    {Math.round(sc.synaptic_strength * 100)}% ({sc.activations}x)
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
