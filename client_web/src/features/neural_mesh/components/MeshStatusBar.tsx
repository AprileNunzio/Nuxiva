import React from 'react';
import { Activity } from 'lucide-react';
import { StreamState } from '../domain/types';
import { useMeshI18n } from '../i18nScope';

interface MeshStatusBarProps {
  readonly streamState: StreamState;
  readonly online: number;
  readonly total: number;
  readonly touchOnly: boolean;
}

const STATE_STYLES: Readonly<Record<StreamState, string>> = {
  connecting: 'bg-sky-400',
  live: 'bg-emerald-400 shadow-[0_0_10px_#34d399]',
  reconnecting: 'bg-amber-400 animate-pulse',
  offline: 'bg-rose-500',
};

export const MeshStatusBar: React.FC<MeshStatusBarProps> = ({ streamState, online, total, touchOnly }) => {
  const { t } = useMeshI18n();
  return (
    <div className="pointer-events-none absolute left-3 right-3 top-3 z-20 flex flex-wrap items-center gap-2 sm:left-5 sm:top-5">
      <div className="nm-glass pointer-events-auto flex items-center gap-2 rounded-full border border-cyan-400/25 px-3 py-1.5" role="status">
        <span className={`h-2 w-2 rounded-full ${STATE_STYLES[streamState]}`} aria-hidden="true" />
        <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-cyan-100">
          {t(`stream_state_${streamState}`)}
        </span>
      </div>
      <div className="nm-glass flex items-center gap-2 rounded-full border border-slate-700/60 px-3 py-1.5">
        <Activity className="h-3.5 w-3.5 text-cyan-300" aria-hidden="true" />
        <span className="font-mono text-[11px] text-slate-200">{t('status_neurons', { online, total })}</span>
      </div>
      <p className="hidden w-full text-[11px] text-slate-500 sm:block sm:w-auto">
        {t(touchOnly ? 'hint_touch' : 'hint_pointer')}
      </p>
    </div>
  );
};
