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
      <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
        {t('policy_selection_title')}
      </h3>
      {updating && <span className="text-xs text-cyan-300 animate-pulse">{t('applying_policy')}...</span>}
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
            className={`flex flex-col text-left rounded-xl border p-3.5 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
              isSelected
                ? 'border-cyan-400/60 bg-cyan-950/30 text-white shadow-[0_0_20px_rgba(34,211,238,0.15)] ring-1 ring-cyan-400/40'
                : 'border-slate-800 bg-slate-900/60 text-slate-300 hover:border-slate-700 hover:bg-slate-900/90'
            } ${updating ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            <div className="flex items-center justify-between gap-2 mb-2">
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-lg border ${
                  isSelected
                    ? 'border-cyan-400/50 bg-cyan-400/20 text-cyan-300'
                    : 'border-slate-700 bg-slate-800/80 text-slate-400'
                }`}
              >
                <Icon className="h-4 w-4" />
              </span>
              {isSelected && (
                <span className="rounded-full bg-cyan-400/20 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-cyan-300 border border-cyan-400/30">
                  {t('active_badge')}
                </span>
              )}
            </div>
            <strong className="text-sm font-semibold text-white">{t(`policy_${id}`)}</strong>
            <p className="mt-1 text-xs text-slate-400 leading-relaxed">{t(`policy_${id}_desc`)}</p>
          </button>
        );
      })}
    </div>
  </div>
);
