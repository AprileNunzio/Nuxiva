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
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl border border-border bg-card/60 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <div className={`p-2.5 rounded-lg ${isOnline ? 'bg-emerald-500/10 text-emerald-500' : 'bg-destructive/10 text-destructive'}`}>
          <Server className="w-6 h-6" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold tracking-tight">{t('engine_title')}</h2>
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                isOnline ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' : 'bg-destructive/15 text-destructive'
              }`}
            >
              {isOnline ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
              {isOnline ? t('status_online') : t('status_offline')}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {t('host_label')}: <span className="font-mono text-foreground">{status?.host || '127.0.0.1:11434'}</span> · {t('version_label')}:{' '}
            <span className="font-mono text-foreground">{status?.version || 'N/A'}</span>
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 w-full sm:w-auto">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-secondary/50 text-xs font-medium border border-border/50">
          <Activity className="w-4 h-4 text-primary" />
          <span>{t('active_models_label')}:</span>
          <span className="font-semibold text-primary">{status?.active_models.length ?? 0}</span>
        </div>
      </div>
    </div>
  );
};
