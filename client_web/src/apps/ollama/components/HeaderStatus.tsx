import React from 'react';
import { Activity, CheckCircle2, Server, XCircle } from 'lucide-react';
import type { DaemonStatus } from '../types';

interface HeaderStatusProps {
  status: DaemonStatus | null;
  t: (key: string) => string;
}

export const HeaderStatus: React.FC<HeaderStatusProps> = ({ status, t }) => {
  const isOnline = status?.online ?? false;

  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl border border-border/80 bg-card/70 backdrop-blur-md shadow-sm">
      <div className="flex items-center gap-3.5">
        <div
          className={`p-3 rounded-xl transition-colors ${
            isOnline ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' : 'bg-destructive/10 text-destructive border border-destructive/20'
          }`}
        >
          <Server className="w-6 h-6" />
        </div>
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-lg font-bold tracking-tight text-foreground">{t('engine_title')}</h2>
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                isOnline
                  ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                  : 'bg-destructive/15 text-destructive border border-destructive/30'
              }`}
            >
              {isOnline ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
              {isOnline ? t('status_online') : t('status_offline')}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {t('host_label')}: <span className="font-mono text-foreground font-medium">{status?.host || '127.0.0.1:11434'}</span> · {t('version_label')}:{' '}
            <span className="font-mono text-foreground font-medium">{status?.version || 'N/A'}</span>
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 w-full sm:w-auto">
        <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-background/60 text-xs font-medium border border-border/60 shadow-xs">
          <Activity className="w-4 h-4 text-primary" />
          <span className="text-muted-foreground">{t('active_models_label')}:</span>
          <span className="font-bold text-primary font-mono">{status?.active_models.length ?? 0}</span>
        </div>
      </div>
    </div>
  );
};
