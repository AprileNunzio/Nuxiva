import React from 'react';
import { ResetStage, Translate } from '../types';

const ORDER: readonly ResetStage[] = ['review', 'identity', 'confirm', 'running', 'done'];

export const StepBar: React.FC<{ readonly stage: ResetStage; readonly t: Translate }> = ({ stage, t }) => {
  const current = ORDER.indexOf(stage);
  return (
    <ol className="mb-4 flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-wider" aria-label={t('steps_label')}>
      {ORDER.map((item, index) => (
        <li
          key={item}
          aria-current={index === current ? 'step' : undefined}
          className={`rounded-full border px-3 py-1 ${
            index === current
              ? 'border-rose-400/60 bg-rose-500/15 text-rose-200'
              : index < current
                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                : 'border-slate-700 text-slate-500'
          }`}
        >
          {index + 1}. {t(`step_${item}`)}
        </li>
      ))}
    </ol>
  );
};
