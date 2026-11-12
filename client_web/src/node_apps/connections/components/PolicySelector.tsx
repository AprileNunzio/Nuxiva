import React from 'react';
import { Cable, Layers, RefreshCw, Wifi } from 'lucide-react';
import { ConnectionRoutingPolicy } from '../types';

interface PolicySelectorProps {
  readonly currentPolicy: ConnectionRoutingPolicy;
  readonly updating: boolean;
  readonly onSelectPolicy: (policy: ConnectionRoutingPolicy) => void;
  readonly t: (key: string) => string;
}

const POLICIES: readonly {
  readonly id: ConnectionRoutingPolicy;
  readonly icon: React.ComponentType<{ className?: string }>;
}[] = [
  { id: 'fallback', icon: RefreshCw },
  { id: 'ethernet_only', icon: Cable },
  { id: 'wifi_only', icon: Wifi },
  { id: 'dual_aggregation', icon: Layers },
];

export const PolicySelector: React.FC<PolicySelectorProps> = ({ currentPolicy, updating, onSelectPolicy, t }) => (
  <div className="flex flex-col gap-3">
    <div className="flex items-center justify-between">
      <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
        {t('policy_selection_title')}
      </h3>
      {updating && <span className="text-xs text-blue-600 font-medium animate-pulse">{t('applying_policy')}...</span>}
    </div>

    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {POLICIES.map(({ id, icon: Icon }) => {
        const isSelected = currentPolicy === id;
        return (
          <button
            key={id}
            type="button"
            disabled={updating}
            onClick={() => onSelectPolicy(id)}
            className={`flex flex-col text-left rounded-xl border p-3.5 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
              isSelected
                ? 'border-blue-500/80 bg-blue-50/70 text-slate-900 ring-2 ring-blue-500/20 shadow-xs'
                : 'border-slate-200/90 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50/60 shadow-2xs'
            } ${updating ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            <div className="flex items-center justify-between gap-2 mb-2">
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-lg border ${
                  isSelected
                    ? 'border-blue-300 bg-blue-100 text-blue-600'
                    : 'border-slate-200 bg-slate-100 text-slate-500'
                }`}
              >
                <Icon className="h-4 w-4" />
              </span>
              {isSelected && (
                <span className="rounded-full bg-blue-100 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-blue-700 border border-blue-200 font-semibold">
                  {t('active_badge')}
                </span>
              )}
            </div>
            <strong className={`text-sm font-semibold ${isSelected ? 'text-blue-900' : 'text-slate-900'}`}>
              {t(`policy_${id}`)}
            </strong>
            <p className="mt-1 text-xs text-slate-500 leading-relaxed">{t(`policy_${id}_desc`)}</p>
          </button>
        );
      })}
    </div>
  </div>
);
