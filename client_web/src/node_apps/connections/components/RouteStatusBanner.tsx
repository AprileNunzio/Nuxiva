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
      className={`rounded-2xl border p-4 sm:p-5 transition shadow-xs ${
        !route.internet_reachable
          ? 'border-rose-200/90 bg-gradient-to-r from-rose-50/90 to-white text-rose-900'
          : route.failover_triggered
          ? 'border-amber-200/90 bg-gradient-to-r from-amber-50/90 to-white text-amber-900'
          : 'border-blue-200/90 bg-gradient-to-r from-blue-50/90 via-indigo-50/40 to-white text-slate-800'
      }`}
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${
              !route.internet_reachable
                ? 'border-rose-200 bg-rose-100/80 text-rose-600'
                : route.failover_triggered
                ? 'border-amber-200 bg-amber-100/80 text-amber-600'
                : 'border-blue-200 bg-blue-100/80 text-blue-600 shadow-2xs'
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
              <span className="text-base sm:text-lg font-bold tracking-tight text-slate-900">
                {t(`status_${route.status}`)}
              </span>
              <span
                className={`rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider font-semibold ${
                  route.internet_reachable
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                    : 'border-rose-200 bg-rose-50 text-rose-700'
                }`}
              >
                <Globe className="mr-1 inline-block h-3 w-3" aria-hidden="true" />
                {route.internet_reachable ? t('internet_online') : t('internet_offline')}
              </span>
              {route.failover_triggered && (
                <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-amber-700 font-semibold">
                  {t('failover_active_badge')}
                </span>
              )}
            </div>
            <p className="mt-0.5 text-xs text-slate-500">
              {t('active_policy_label')}: <strong className="text-slate-800">{t(`policy_${policy}`)}</strong>
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="rounded-xl border border-slate-200/90 bg-white/95 px-3 py-1.5 font-mono shadow-2xs">
            <span className="text-slate-500">{t('primary_route_label')}: </span>
            <span className="font-bold text-blue-600">{route.primary_interface}</span>
          </div>
          {route.secondary_interface && (
            <div className="rounded-xl border border-slate-200/90 bg-white/95 px-3 py-1.5 font-mono shadow-2xs">
              <span className="text-slate-500">{t('secondary_route_label')}: </span>
              <span className="font-bold text-blue-600">{route.secondary_interface}</span>
            </div>
          )}
          {isOptimal && (
            <span className="flex items-center gap-1 text-[11px] text-emerald-600 font-semibold">
              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
              {t('routing_optimal')}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
