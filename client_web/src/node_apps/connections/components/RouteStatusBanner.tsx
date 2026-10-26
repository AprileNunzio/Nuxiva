import React from 'react';
import { Activity, AlertTriangle, CheckCircle2, Globe, ShieldCheck } from 'lucide-react';
import { ActiveRouteResult, ConnectionRoutingPolicy } from '../types';

interface RouteStatusBannerProps {
  readonly route: ActiveRouteResult;
  readonly policy: ConnectionRoutingPolicy;
  readonly t: (key: string) => string;
}

export const RouteStatusBanner: React.FC<RouteStatusBannerProps> = ({ route, policy, t }) => {
  const isOptimal = !route.failover_triggered && route.internet_reachable;

  return (
    <div
      className={`rounded-2xl border p-4 sm:p-5 transition ${
        !route.internet_reachable
          ? 'border-rose-500/40 bg-gradient-to-br from-rose-950/30 to-slate-950/90 text-rose-200'
          : route.failover_triggered
          ? 'border-amber-500/40 bg-gradient-to-br from-amber-950/30 to-slate-950/90 text-amber-200'
          : 'border-cyan-500/30 bg-gradient-to-br from-cyan-950/20 to-slate-950/90 text-cyan-200'
      }`}
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${
              !route.internet_reachable
                ? 'border-rose-500/40 bg-rose-500/10 text-rose-400'
                : route.failover_triggered
                ? 'border-amber-500/40 bg-amber-500/10 text-amber-400'
                : 'border-cyan-400/40 bg-cyan-400/10 text-cyan-300'
            }`}
          >
            {!route.internet_reachable ? (
              <AlertTriangle className="h-5 w-5" aria-hidden="true" />
            ) : route.failover_triggered ? (
              <Activity className="h-5 w-5 animate-pulse" aria-hidden="true" />
            ) : (
              <ShieldCheck className="h-5 w-5" aria-hidden="true" />
            )}
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-['Rajdhani'] text-lg font-bold tracking-wide text-white">
                {t(`status_${route.status}`)}
              </span>
              <span
                className={`rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${
                  route.internet_reachable
                    ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                    : 'border-rose-500/40 bg-rose-500/10 text-rose-300'
                }`}
              >
                <Globe className="mr-1 inline-block h-3 w-3" aria-hidden="true" />
                {route.internet_reachable ? t('internet_online') : t('internet_offline')}
              </span>
              {route.failover_triggered && (
                <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-amber-300">
                  {t('failover_active_badge')}
                </span>
              )}
            </div>
            <p className="mt-0.5 text-xs text-slate-400">
              {t('active_policy_label')}: <strong className="text-slate-200">{t(`policy_${policy}`)}</strong>
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-1.5 font-mono">
            <span className="text-slate-400">{t('primary_route_label')}: </span>
            <span className="font-bold text-cyan-300">{route.primary_interface}</span>
          </div>
          {route.secondary_interface && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-1.5 font-mono">
              <span className="text-slate-400">{t('secondary_route_label')}: </span>
              <span className="font-bold text-cyan-300">{route.secondary_interface}</span>
            </div>
          )}
          {isOptimal && (
            <span className="flex items-center gap-1 text-[11px] text-emerald-400">
              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
              {t('routing_optimal')}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
