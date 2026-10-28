import React, { useState } from 'react';
import { AxiomaticFormalism } from './types';
import { Atom, Compass, Sparkles, Zap } from 'lucide-react';

interface OntologicalCreativitySectionProps {
  readonly formalisms: readonly AxiomaticFormalism[];
  readonly onSynthesize: (id: string, paradigm: string, observations: number[][]) => Promise<void>;
  readonly busy: boolean;
  readonly t: (key: string) => string;
}

export const OntologicalCreativitySection: React.FC<OntologicalCreativitySectionProps> = ({
  formalisms,
  onSynthesize,
  busy,
  t,
}) => {
  const [selectedParadigm, setSelectedParadigm] = useState<string>('calculus');

  const sampleObservations: Record<string, number[][]> = {
    calculus: [[0, 0], [1, 1], [2, 4], [3, 9], [4, 16]],
    riemann_metric: [[0, 0], [1, 1.41], [2, 2.82], [3, 4.24], [4, 5.65]],
    lie_algebra: [[0, 1], [1.57, 0], [3.14, -1], [4.71, 0], [6.28, 1]],
    symplectic_geometry: [[1, 0], [0, 1], [-1, 0], [0, -1]],
    discrete_topology: [[0, 0], [1, 0], [1, 1], [0, 1]],
  };

  const handleTriggerSynthesis = () => {
    const id = `formalism_${selectedParadigm}_${Date.now().toString(36).slice(-4)}`;
    const obs = sampleObservations[selectedParadigm] || sampleObservations.calculus;
    void onSynthesize(id, selectedParadigm, obs);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-purple-200 bg-gradient-to-r from-purple-50/70 via-white to-pink-50/50 p-5 sm:p-6 shadow-sm">
        <div className="flex items-center gap-2.5">
          <Sparkles className="w-5 h-5 text-purple-700" />
          <h3 className="text-base sm:text-lg font-black text-slate-950">
            {t('ontology_title')}
          </h3>
          <span className="ml-auto inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-purple-100 text-purple-800 border border-purple-300">
            <Atom className="w-3.5 h-3.5" />
            Meta-Genesi
          </span>
        </div>
        <p className="mt-1 text-xs text-slate-600">
          {t('ontology_subtitle')}
        </p>

        <div className="mt-5 p-4 rounded-2xl bg-white border border-purple-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-700 block">
              {t('ontology_paradigm_label')}
            </label>
            <div className="flex flex-wrap gap-2">
              {[
                { id: 'calculus', label: t('ontology_formalism_calculus') },
                { id: 'riemann_metric', label: t('ontology_formalism_riemann') },
                { id: 'lie_algebra', label: t('ontology_formalism_lie') },
                { id: 'symplectic_geometry', label: t('ontology_formalism_symplectic') },
                { id: 'discrete_topology', label: t('ontology_formalism_discrete') },
              ].map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setSelectedParadigm(p.id)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all border ${
                    selectedParadigm === p.id
                      ? 'border-purple-600 bg-purple-600 text-white shadow-sm'
                      : 'border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <button
            type="button"
            disabled={busy}
            onClick={handleTriggerSynthesis}
            className="self-start sm:self-center px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs shadow-md transition-all flex items-center gap-2 whitespace-nowrap"
          >
            <Compass className="w-4 h-4" />
            {t('ontology_synthesize_btn')}
          </button>
        </div>

        {formalisms.length > 0 && (
          <div className="mt-5 space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Formalismi Inventati ({formalisms.length})
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {formalisms.map((f) => (
                <div
                  key={f.id}
                  className="rounded-2xl border border-purple-200 bg-white p-4 space-y-2 shadow-sm"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-black text-slate-950">
                      {f.name}
                    </span>
                    <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 border border-purple-200 flex items-center gap-1">
                      <Zap className="w-3 h-3 text-purple-600" />
                      {t('ontology_shortcut_compiled')}
                    </span>
                  </div>

                  <div className="text-xs text-slate-700 space-y-1">
                    <p className="font-mono text-[11px] bg-slate-50 p-2 rounded-lg border border-slate-200">
                      <strong>{t('ontology_differential_op')}:</strong> {f.differential_operator}
                    </p>
                    <p className="text-[11px] text-slate-600">
                      <strong>{t('ontology_invariance_group')}:</strong> {f.invariance_group}
                    </p>
                    <p className="text-[11px] text-emerald-700 font-semibold">
                      {t('ontology_residual_reduction')}: {(f.empirical_residual_reduction * 100).toFixed(1)}%
                    </p>
                  </div>

                  {f.axioms.map((ax) => (
                    <div
                      key={ax.id}
                      className="p-2.5 rounded-xl bg-purple-50/50 border border-purple-100 text-[11px] text-purple-900"
                    >
                      <p className="font-medium">«{ax.statement}»</p>
                      <p className="text-[10px] text-purple-600 mt-1">
                        Legge di Conservazione: {ax.conservation_law}
                      </p>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
