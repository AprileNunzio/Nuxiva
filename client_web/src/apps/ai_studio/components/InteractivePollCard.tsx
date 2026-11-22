import React, { useState } from 'react';
import type { Poll } from '../types';

interface InteractivePollCardProps {
  poll: Poll;
  onVote: (pollId: string, optionId: string, stepIndex?: number) => void;
  onSubmitSurvey?: (pollId: string, answers: Record<string, string>) => void;
}

export const InteractivePollCard: React.FC<InteractivePollCardProps> = ({
  poll,
  onVote,
  onSubmitSurvey,
}) => {
  const [selectedOptionId, setSelectedOptionId] = useState<string | undefined>(poll.userVotedId);
  const [currentStepIdx, setCurrentStepIdx] = useState<number>(poll.currentStepIndex || 0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isCompleted, setIsCompleted] = useState(false);

  if (!poll) return null;

  const isComplex = Boolean(poll.isComplex && Array.isArray(poll.steps) && poll.steps.length > 0);

  if (isComplex && poll.steps && poll.steps.length > 0) {
    const currentStep = poll.steps[currentStepIdx] || poll.steps[0];
    if (!currentStep) return null;
    const totalSteps = poll.steps.length;
    const progressPercent = Math.round(((currentStepIdx + 1) / totalSteps) * 100);

    const handleSelectStepOption = (optId: string) => {
      setAnswers((prev) => ({ ...prev, [currentStep.id]: optId }));
      onVote(poll.id, optId, currentStepIdx);
    };

    const handleNext = () => {
      if (currentStepIdx < totalSteps - 1) {
        setCurrentStepIdx((p) => p + 1);
      } else {
        setIsCompleted(true);
        onSubmitSurvey?.(poll.id, answers);
      }
    };

    const handlePrev = () => {
      if (currentStepIdx > 0) {
        setCurrentStepIdx((p) => p - 1);
      }
    };

    return (
      <div className="w-full max-w-2xl rounded-2xl border border-cyan-800/80 bg-slate-900/90 p-4 shadow-xl flex flex-col gap-3 my-2">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div className="flex items-center gap-2">
            <span className="text-cyan-400 font-semibold text-sm">📋</span>
            <span className="text-xs font-semibold text-cyan-200">
              Sondaggio Progetto & Requisiti Dettagliati
            </span>
          </div>
          <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/80 px-2 py-0.5 rounded-full border border-cyan-800">
            Passo {currentStepIdx + 1} di {totalSteps}
          </span>
        </div>

        <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div
            className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {!isCompleted ? (
          <div className="flex flex-col gap-3">
            <div>
              <span className="text-[10px] uppercase font-semibold text-cyan-400/80 tracking-wider">
                {currentStep.category}
              </span>
              <h3 className="text-sm font-medium text-slate-100 mt-0.5">{currentStep.title}</h3>
            </div>

            <div className="flex flex-col gap-2">
              {currentStep.options.map((opt) => {
                const isSelected = answers[currentStep.id] === opt.id || currentStep.userVotedId === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => handleSelectStepOption(opt.id)}
                    className={`text-left p-3 rounded-xl border text-xs transition-all flex items-start gap-3 ${
                      isSelected
                        ? 'bg-cyan-950/70 border-cyan-500 text-cyan-100 shadow-sm'
                        : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:bg-slate-800/50 hover:border-slate-700'
                    }`}
                  >
                    <span
                      className={`h-4 w-4 rounded-full mt-0.5 border flex items-center justify-center shrink-0 ${
                        isSelected
                          ? 'border-cyan-400 bg-cyan-500 text-white'
                          : 'border-slate-600 bg-transparent'
                      }`}
                    >
                      {isSelected && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-slate-200">{opt.text}</div>
                      {opt.description && (
                        <div className="text-[11px] text-slate-400 mt-0.5 leading-snug">
                          {opt.description}
                        </div>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={handlePrev}
                disabled={currentStepIdx === 0}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
              >
                ← Indietro
              </button>

              <button
                type="button"
                onClick={handleNext}
                disabled={!answers[currentStep.id] && !currentStep.userVotedId}
                className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-white text-xs font-semibold shadow-md transition-all"
              >
                {currentStepIdx === totalSteps - 1 ? 'Conferma e Invia ✓' : 'Avanti →'}
              </button>
            </div>
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-cyan-950/40 border border-cyan-800/60 flex flex-col items-center text-center gap-2">
            <span className="text-2xl">✓</span>
            <div className="text-xs font-semibold text-cyan-200">
              Sondaggio Completato & Ricevuto da Nuxiva!
            </div>
            <p className="text-[11px] text-slate-400 max-w-sm">
              I parametri selezionati per architettura, tolleranze, e workflow sono stati sincronizzati
              nel cervello dell'agente per l'elaborazione autonoma.
            </p>
          </div>
        )}
      </div>
    );
  }

  const options = Array.isArray(poll.options) ? poll.options.filter(Boolean) : [];
  const totalVotes = options.reduce((acc, opt) => acc + (opt?.votes || 0), 0);

  const handleVoteQuick = (optId: string) => {
    setSelectedOptionId(optId);
    onVote(poll.id, optId);
  };

  return (
    <div className="w-full max-w-2xl rounded-2xl border border-slate-700/80 bg-slate-900/90 p-4 shadow-xl flex flex-col gap-3 my-2">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          <span className="text-cyan-400">📊</span>
          <span className="text-xs font-semibold text-slate-200">Domanda & Scelta Rapida</span>
        </div>
        <span className="text-[11px] text-slate-500 font-mono">
          {totalVotes} {totalVotes === 1 ? 'risposta' : 'risposte'}
        </span>
      </div>

      <p className="text-xs font-medium text-slate-100">{poll.question}</p>

      <div className="flex flex-col gap-2">
        {options.map((opt) => {
          const isSelected = selectedOptionId === opt.id;
          const percent = totalVotes > 0 ? Math.round((opt.votes / totalVotes) * 100) : 0;

          return (
            <button
              key={opt.id}
              type="button"
              onClick={() => handleVoteQuick(opt.id)}
              className={`relative overflow-hidden text-left p-2.5 rounded-xl border text-xs transition-all flex items-center justify-between ${
                isSelected
                  ? 'bg-cyan-950/80 border-cyan-500 text-cyan-100 font-medium'
                  : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:bg-slate-800/60 hover:border-slate-700'
              }`}
            >
              <div
                className="absolute inset-y-0 left-0 bg-cyan-500/10 pointer-events-none transition-all duration-300"
                style={{ width: `${percent}%` }}
              />

              <div className="relative z-10 flex items-center gap-2 min-w-0">
                <span
                  className={`h-3.5 w-3.5 rounded-full border flex items-center justify-center shrink-0 ${
                    isSelected ? 'border-cyan-400 bg-cyan-500' : 'border-slate-600'
                  }`}
                >
                  {isSelected && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
                </span>
                <span className="truncate">{opt.text}</span>
              </div>

              <div className="relative z-10 flex items-center gap-2 text-[11px] font-mono text-slate-400 shrink-0">
                <span>{percent}%</span>
              </div>
            </button>
          );
        })}
      </div>

      {selectedOptionId && (
        <div className="text-[11px] text-emerald-400 font-mono flex items-center gap-1 mt-0.5">
          <span>✓</span>
          <span>Risposta registrata da Nuxiva</span>
        </div>
      )}
    </div>
  );
};
