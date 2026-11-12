import React from 'react';
import { saveRouting } from '../../core/brainApi';
import { useSectionText } from '../../core/i18n';
import { useBrain } from '../../core/useBrainStore';
import { ROUTING, Routing } from '../../core/types';
import { Card, FLUID } from '../../ui/primitives';

export const RoutingCard: React.FC<{ readonly routing: Routing }> = ({ routing }) => {
  const { t } = useSectionText('contexts');
  const { commit, action } = useBrain();
  return (
    <Card title={t('routing_title')} description={t('routing_hint')}>
      <div role="radiogroup" aria-label={t('routing_title')} className={`grid gap-2 ${FLUID.xs}`}>
        {ROUTING.map((value) => {
          const selected = value === routing;
          return (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={action.busy !== null}
              onClick={() => !selected && void commit('routing', 'brain_routing_failed', () => saveRouting(value))}
              className={`flex flex-col gap-1 rounded-lg border p-3 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 disabled:opacity-60 ${
                selected ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500' : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
              }`}
            >
              <span className="text-sm font-medium text-slate-900">{t(`routing_${value}`)}</span>
              <span className="text-xs text-slate-500">{t(`routing_${value}_hint`)}</span>
            </button>
          );
        })}
      </div>
    </Card>
  );
};
