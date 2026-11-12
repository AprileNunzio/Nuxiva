import React from 'react';
import { Check, Loader2 } from 'lucide-react';
import type { Job } from '../types';

interface BuildProgressProps {
  readonly job: Job;
  readonly count: number;
  readonly label: (stage: string) => string;
  readonly itemsLabel: string;
  readonly fallbackLabel: string;
}

export const BuildProgress: React.FC<BuildProgressProps> = ({ job, count, label, itemsLabel, fallbackLabel }) => {
  const stages = ['outline', ...job.stages];
  const active = stages.indexOf(job.stage);
  return (
    <div className="pointer-events-none flex max-w-full flex-wrap items-center justify-center gap-1.5 rounded-2xl border border-slate-200 bg-white/90 px-3 py-2 shadow-md backdrop-blur">
      {stages.map((stage, index) => {
        const done = job.state !== 'building' || index < active;
        const live = job.state === 'building' && index === active;
        return (
          <span key={stage} className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold transition ${live ? 'bg-sky-100 text-sky-800' : done ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-400'}`}>
            {live ? <Loader2 className="h-3 w-3 animate-spin" /> : done ? <Check className="h-3 w-3" /> : <span className="h-1.5 w-1.5 rounded-full bg-slate-300" />}
            {label(stage)}
          </span>
        );
      })}
      <span className="ml-1 text-[11px] font-medium text-slate-500">{count} {itemsLabel}</span>
      {job.mode === 'template' && <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700">{fallbackLabel}</span>}
    </div>
  );
};
