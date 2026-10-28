import React, { useState } from 'react';
import { EpistemicConfrontationRecord } from './types';
import { CheckCircle2, HelpCircle, Lock, ShieldCheck } from 'lucide-react';

interface EpistemicConfrontationSectionProps {
  readonly pending: readonly EpistemicConfrontationRecord[];
  readonly resolved: readonly EpistemicConfrontationRecord[];
  readonly onResolve: (id: string, choiceId: string, justification: string) => Promise<void>;
  readonly busy: boolean;
  readonly t: (key: string) => string;
}

export const EpistemicConfrontationSection: React.FC<EpistemicConfrontationSectionProps> = ({
  pending,
  resolved,
  onResolve,
  busy,
  t,
}) => {
  const [selectedChoices, setSelectedChoices] = useState<Record<string, string>>({});
  const [justifications, setJustifications] = useState<Record<string, string>>({});

  const handleSelectChoice = (confId: string, choiceId: string) => {
    setSelectedChoices((prev) => ({ ...prev, [confId]: choiceId }));
  };

  const handleJustificationChange = (confId: string, val: string) => {
    setJustifications((prev) => ({ ...prev, [confId]: val }));
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-amber-200 bg-gradient-to-r from-amber-50/70 via-white to-orange-50/50 p-5 sm:p-6 shadow-sm">
        <div className="flex items-center gap-2.5">
          <HelpCircle className="w-5 h-5 text-amber-700" />
          <h3 className="text-base sm:text-lg font-black text-slate-950">
            {t('confrontation_title')}
          </h3>
          <span className="ml-auto inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
            <Lock className="w-3.5 h-3.5" />
            {t('confrontation_certainty_100')}
          </span>
        </div>
        <p className="mt-1 text-xs text-slate-600">
          {t('confrontation_subtitle')}
        </p>

        <div className="mt-5 space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
            {t('confrontation_pending_label')} ({pending.length})
          </h4>

          {pending.length === 0 ? (
            <div className="p-4 rounded-2xl bg-white/80 border border-slate-200 text-xs font-medium text-slate-600 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              {t('confrontation_empty_pending')}
            </div>
          ) : (
            pending.map((conf) => {
              const currentChoice = selectedChoices[conf.id] || '';
              const currentJust = justifications[conf.id] || '';
              const canSubmit = Boolean(currentChoice && currentJust.trim().length >= 3);

              return (
                <div
                  key={conf.id}
                  className="rounded-2xl border border-amber-300 bg-white p-4 space-y-4 shadow-sm"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-amber-100 pb-3">
                    <div>
                      <span className="text-xs font-mono font-bold text-amber-900 bg-amber-50 px-2.5 py-1 rounded-lg border border-amber-200">
                        {conf.context_key}
                      </span>
                      <p className="text-xs text-slate-500 mt-1">ID: {conf.id}</p>
                    </div>
                    <div className="text-xs font-semibold text-slate-700">
                      Entropia di Shannon: {conf.uncertainty_entropy.toFixed(3)}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {conf.hypotheses.map((h) => {
                      const isSelected = currentChoice === h.id;
                      return (
                        <button
                          key={h.id}
                          type="button"
                          onClick={() => handleSelectChoice(conf.id, h.id)}
                          className={`text-left p-3.5 rounded-xl border transition-all ${
                            isSelected
                              ? 'border-indigo-600 bg-indigo-50/80 shadow-md ring-2 ring-indigo-500/20'
                              : 'border-slate-200 bg-slate-50/60 hover:bg-slate-100/80'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-black text-slate-900">
                              {h.label}
                            </span>
                            <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-200 text-slate-800">
                              P = {(h.prior_probability * 100).toFixed(0)}%
                            </span>
                          </div>
                          <p className="mt-1.5 text-xs text-slate-600">
                            <strong>Esito:</strong> {h.predicted_outcome}
                          </p>
                          <p className="mt-1 text-[11px] text-slate-500">
                            <strong>Piano:</strong> {h.action_plan}
                          </p>
                        </button>
                      );
                    })}
                  </div>

                  <div className="space-y-2">
                    <textarea
                      value={currentJust}
                      onChange={(e) => handleJustificationChange(conf.id, e.target.value)}
                      placeholder={t('confrontation_justification_placeholder')}
                      rows={2}
                      className="w-full text-xs p-3 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-amber-500 bg-slate-50/50"
                    />
                    <div className="flex justify-end">
                      <button
                        type="button"
                        disabled={!canSubmit || busy}
                        onClick={() => void onResolve(conf.id, currentChoice, currentJust)}
                        className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 disabled:opacity-40 text-white font-bold text-xs shadow-md transition-all flex items-center gap-1.5"
                      >
                        <ShieldCheck className="w-4 h-4" />
                        {t('confrontation_resolve_btn')}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {resolved.length > 0 && (
          <div className="mt-6 pt-5 border-t border-amber-200 space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              {t('confrontation_resolved_label')} ({resolved.length})
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {resolved.map((rec) => (
                <div
                  key={rec.id}
                  className="rounded-2xl border border-emerald-200 bg-white/90 p-3.5 space-y-1.5 shadow-sm"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900">
                      {rec.context_key}
                    </span>
                    <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                      100% Certezza
                    </span>
                  </div>
                  <p className="text-xs text-slate-700">
                    <strong>Scelta:</strong> {rec.chosen_hypothesis_id}
                  </p>
                  <p className="text-[11px] text-slate-500 italic">
                    «{rec.user_justification}»
                  </p>
                  <div className="text-[10px] font-mono text-slate-400 truncate">
                    {rec.encrypted_digest}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
