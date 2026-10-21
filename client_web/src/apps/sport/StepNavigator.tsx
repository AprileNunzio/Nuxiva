import React from 'react';
import { SportStep } from './types';
import { Layers, Calendar, Trophy, BarChart3, Tv, Bell } from 'lucide-react';

interface StepNavigatorProps {
  readonly currentStep: SportStep;
  readonly onSelectStep: (step: SportStep) => void;
  readonly sportColor?: string;
}

export const StepNavigator: React.FC<StepNavigatorProps> = ({
  currentStep,
  onSelectStep,
  sportColor = 'cyan',
}) => {
  const steps: { id: SportStep; label: string; icon: React.ReactNode }[] = [
    { id: 'competition', label: '1. Competizioni', icon: <Layers className="h-3.5 w-3.5" /> },
    { id: 'schedule', label: '2. Calendario & Live', icon: <Calendar className="h-3.5 w-3.5" /> },
    { id: 'standings', label: '3. Classifiche', icon: <Trophy className="h-3.5 w-3.5" /> },
    { id: 'details', label: '4. Dettagli & Statistiche', icon: <BarChart3 className="h-3.5 w-3.5" /> },
    { id: 'tv_stream', label: '5. Canale TV / IPTV', icon: <Tv className="h-3.5 w-3.5" /> },
    { id: 'favorites', label: '6. Preferiti & Avvisi', icon: <Bell className="h-3.5 w-3.5" /> },
  ];

  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/80 p-1.5 backdrop-blur-sm">
      {steps.map((st) => {
        const isActive = currentStep === st.id;
        return (
          <button
            key={st.id}
            type="button"
            onClick={() => onSelectStep(st.id)}
            className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              isActive
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            {st.icon}
            <span>{st.label}</span>
          </button>
        );
      })}
    </div>
  );
};
