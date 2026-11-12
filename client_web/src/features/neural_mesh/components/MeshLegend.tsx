import React from 'react';
import { KIND_COLORS } from '../domain/palette';
import { NEURON_KINDS } from '../domain/types';
import { useMeshI18n } from '../i18nScope';

export const MeshLegend: React.FC = () => {
  const { t } = useMeshI18n();
  return (
    <div className="nm-glass pointer-events-none absolute bottom-4 left-4 z-20 hidden rounded-2xl border border-slate-700/50 px-4 py-3 md:block">
      <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">{t('legend_title')}</p>
      <ul className="flex flex-col gap-1.5">
        {NEURON_KINDS.map((kind) => (
          <li key={kind} className="flex items-center gap-2 text-xs text-slate-300">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: KIND_COLORS[kind], boxShadow: `0 0 8px ${KIND_COLORS[kind]}` }}
              aria-hidden="true"
            />
            {t(`kind_${kind}`)}
          </li>
        ))}
      </ul>
    </div>
  );
};
